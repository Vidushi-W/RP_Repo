export const SOUND_LABELS = Object.freeze({
  FIRE_ALARM: 'fire_alarm',
  SIREN: 'siren_emergency_vehicle',
  VEHICLE_HORN: 'vehicle_horn',
  DOORBELL: 'doorbell',
  HUMAN_CALLING: 'human_calling_shouting',
  UNKNOWN: 'unknown_sound',
});

const supportedLabels = new Set(Object.values(SOUND_LABELS).filter(label => label !== SOUND_LABELS.UNKNOWN));
const modelStates = new Set(['ready', 'unavailable', 'error']);

/**
 * Normalize a single-file inference response. A candidate is only trusted when
 * it is one of the explicit classes above; e.g. generic "vehicle" is unknown.
 */
export function normalizePrediction(raw, { timestamp, threshold = 0.65 } = {}) {
  const candidate = typeof raw?.label === 'string' ? raw.label.trim().toLowerCase() : '';
  const score = typeof raw?.score === 'number' && Number.isFinite(raw.score) && raw.score >= 0 && raw.score <= 1
    ? raw.score
    : null;
  const rawModelStatus = raw?.modelStatus?.status;
  const status = modelStates.has(rawModelStatus) ? rawModelStatus : 'error';
  const modelName = typeof raw?.modelStatus?.modelName === 'string' ? raw.modelStatus.modelName : null;

  if (status === 'unavailable') return unavailableResult(timestamp, 'inference_unavailable');
  if (status === 'error') {
    return {
      ...unavailableResult(timestamp, 'inference_error'),
      modelStatus: { status: 'error', modelName },
    };
  }

  let label = SOUND_LABELS.UNKNOWN;
  let reason = 'unsupported_sound';
  let candidateLabel = null;

  if (candidate === SOUND_LABELS.UNKNOWN) {
    reason = 'unknown_sound';
  } else if (supportedLabels.has(candidate)) {
    candidateLabel = candidate;
    if (score === null) {
      reason = 'invalid_score';
    } else if (score < threshold) {
      reason = 'low_confidence';
    } else {
      label = candidate;
      reason = 'classified';
    }
  } else if (candidate) {
    // Keep an unsupported model label visible for debugging without promoting it.
    candidateLabel = candidate.slice(0, 80);
  }

  return {
    label,
    score,
    timestamp,
    modelStatus: { status, modelName },
    reason,
    candidateLabel,
  };
}

export function createSoundAnalyzer({ adapter = null, threshold = 0.65, now = () => new Date() } = {}) {
  return {
    async analyzeAudioFile(file) {
      const timestamp = now().toISOString();
      if (!file || typeof file.uri !== 'string' || !file.uri) {
        return unavailableResult(timestamp, 'invalid_audio_file');
      }
      if (!adapter || typeof adapter.analyzeAudioFile !== 'function') {
        return unavailableResult(timestamp, 'inference_unavailable');
      }

      try {
        const raw = await adapter.analyzeAudioFile({ uri: file.uri, mimeType: file.mimeType || null });
        return normalizePrediction(raw, { timestamp, threshold });
      } catch {
        return {
          ...unavailableResult(timestamp, 'inference_error'),
          modelStatus: { status: 'error', modelName: adapter.modelName || null },
        };
      }
    },
  };
}

function unavailableResult(timestamp, reason) {
  return {
    label: SOUND_LABELS.UNKNOWN,
    score: null,
    timestamp,
    modelStatus: { status: 'unavailable', modelName: null },
    reason,
    candidateLabel: null,
  };
}

/** Default adapter: deliberately performs no I/O and stores no audio. */
export const unavailableInferenceAdapter = Object.freeze({
  modelName: null,
  status: 'unavailable',
  async analyzeAudioFile() {
    return { label: SOUND_LABELS.UNKNOWN, score: null, modelStatus: { status: 'unavailable', modelName: null } };
  },
});

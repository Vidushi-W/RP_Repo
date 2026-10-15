import { SOUND_LABELS } from './analysis.mjs';

export const URGENCY = Object.freeze({ LOW: 'low', NORMAL: 'normal', HIGH: 'high', CRITICAL: 'critical', UNKNOWN: 'unknown' });
export const ATTENTION = Object.freeze({ IDLE: 'idle', BUSY: 'busy' });
export const DECISION = Object.freeze({ INTERRUPT: 'interrupt', QUEUE: 'queue', RECORD: 'record' });

const knownSounds = new Set(Object.values(SOUND_LABELS));
const validUrgencies = new Set(Object.values(URGENCY));
const validAttentionStates = new Set(Object.values(ATTENTION));

const DEFAULT_THRESHOLDS = Object.freeze({
  minimumDecisionConfidence: 0.65,
  minimumDirectionEvidenceConfidence: 0.7,
});

/**
 * Deterministic policy layer, separate from sound classification.
 * Confidence thresholds and urgency mappings are provisional pending evaluation.
 */
export function createReasoningEngine({ thresholds = {}, now = () => new Date() } = {}) {
  const policy = { ...DEFAULT_THRESHOLDS, ...thresholds };
  validateThresholds(policy);

  return {
    thresholds: Object.freeze({ ...policy, provisional: true }),
    evaluate(input = {}) {
      return reasonEvent(input, { thresholds: policy, now });
    },
  };
}

export function reasonEvent(input = {}, { thresholds = DEFAULT_THRESHOLDS, now = () => new Date() } = {}) {
  validateThresholds(thresholds);
  const timestamp = now().toISOString();
  const rawCategory = typeof input.soundCategory === 'string' ? input.soundCategory.trim().toLowerCase() : '';
  const categoryKnown = knownSounds.has(rawCategory);
  const soundCategory = categoryKnown ? rawCategory : SOUND_LABELS.UNKNOWN;
  const isUnknownSound = !categoryKnown || soundCategory === SOUND_LABELS.UNKNOWN;
  const confidence = validScore(input.confidence) ? input.confidence : null;
  const urgency = validUrgencies.has(input.estimatedUrgency) ? input.estimatedUrgency : URGENCY.UNKNOWN;
  const attention = validAttentionStates.has(input.attentionChannelState) ? input.attentionChannelState : null;
  const directionEvidence = validateDirectionEvidence(input.availableDirectionEvidence, thresholds.minimumDirectionEvidenceConfidence);
  const log = [];

  log.push(entry('decision_inputs', `category=${soundCategory}; confidence=${confidence ?? 'unknown'}; urgency=${urgency}; attention=${attention || 'unknown'}.`));

  if (!categoryKnown) {
    log.push(entry('unsupported_category', 'Input category is unsupported; event is treated as unknown.'));
  } else if (soundCategory === SOUND_LABELS.UNKNOWN) {
    log.push(entry('unknown_sound', 'Classifier supplied unknown_sound; no sound-specific alert policy is applied.'));
  }

  if (confidence === null) log.push(entry('confidence_missing', 'Confidence is missing or outside 0..1.'));
  if (attention === null) log.push(entry('attention_state_unknown', 'Attention-channel state is missing or invalid; non-critical alerts will not interrupt.'));
  if (directionEvidence.accepted) {
    log.push(entry('direction_evidence_accepted', `Direction ${directionEvidence.value.direction} is included from ${directionEvidence.value.source}; direction does not raise urgency.`));
  } else if (directionEvidence.provided) {
    log.push(entry('direction_evidence_rejected', directionEvidence.reason));
  }

  const sufficientlyConfident = confidence !== null && confidence >= thresholds.minimumDecisionConfidence;
  const safetyCriticalFire = soundCategory === SOUND_LABELS.FIRE_ALARM && sufficientlyConfident;
  const uncertain = isUnknownSound || !sufficientlyConfident;
  const reportedCategory = uncertain ? SOUND_LABELS.UNKNOWN : soundCategory;
  const candidateCategory = uncertain
    ? (isUnknownSound ? (categoryKnown ? null : rawCategory || null) : soundCategory)
    : null;

  let eventState = isUnknownSound ? 'unknown' : uncertain ? 'uncertain' : 'confirmed';
  let priority = URGENCY.UNKNOWN;
  let decision = DECISION.RECORD;
  let reasonCode;
  let reasonText;

  if (isUnknownSound) {
    reasonCode = 'unknown_event_recorded';
    reasonText = 'Evidence does not support a known sound category; event is recorded without a haptic alert.';
  } else if (!sufficientlyConfident) {
    reasonCode = 'uncertain_confidence';
    reasonText = `Confidence is below the provisional ${thresholds.minimumDecisionConfidence} decision threshold; event is uncertain and recorded without a haptic alert.`;
  } else if (safetyCriticalFire) {
    eventState = 'confirmed';
    priority = URGENCY.CRITICAL;
    decision = DECISION.INTERRUPT;
    reasonCode = 'confirmed_fire_alarm_safety_override';
    reasonText = 'Confirmed fire-alarm candidate takes critical priority and interrupts regardless of attention state or urgency estimate.';
  } else {
    priority = nonFirePriority(urgency);
    if (urgency === URGENCY.CRITICAL) {
      log.push(entry('non_fire_urgency_capped', 'Critical urgency is capped at high for non-fire classes; this policy does not infer a safety-critical emergency from sound category alone.'));
    }

    if (soundCategory === SOUND_LABELS.SIREN) {
      log.push(entry('siren_context_required', urgency === URGENCY.HIGH || urgency === URGENCY.CRITICAL
        ? 'Siren is treated as potentially urgent because the supplied urgency estimate is high; this does not establish immediate danger.'
        : 'A siren alone is not treated as immediate danger; the supplied urgency estimate determines priority.'));
    }
    if (soundCategory === SOUND_LABELS.VEHICLE_HORN) {
      log.push(entry('horn_context_limited', directionEvidence.accepted
        ? `Horn priority uses the supplied urgency estimate (${urgency}); direction evidence is reported as ${directionEvidence.value.direction} but does not establish danger.`
        : `Horn priority uses only the supplied urgency estimate (${urgency}); no additional context is inferred.`));
    }

    if (priority === URGENCY.HIGH) {
      decision = attention === ATTENTION.IDLE ? DECISION.INTERRUPT : DECISION.QUEUE;
      reasonCode = attention === ATTENTION.IDLE ? 'high_priority_interrupt_while_idle' : attention === ATTENTION.BUSY ? 'high_priority_queued_while_busy' : 'high_priority_queued_attention_unknown';
      reasonText = attention === ATTENTION.IDLE
        ? 'High-priority non-critical event interrupts while the attention channel is idle.'
        : `Non-critical high-priority event is queued${attention === ATTENTION.BUSY ? ' while the attention channel is busy' : ' because attention state is unknown'}.`;
    } else if (priority === URGENCY.NORMAL) {
      decision = attention === ATTENTION.IDLE ? DECISION.INTERRUPT : DECISION.QUEUE;
      reasonCode = attention === ATTENTION.IDLE ? 'normal_priority_interrupt_while_idle' : attention === ATTENTION.BUSY ? 'normal_priority_queued_while_busy' : 'normal_priority_queued_attention_unknown';
      reasonText = attention === ATTENTION.IDLE
        ? 'Normal-priority event receives a gentle alert while the attention channel is idle.'
        : `Eligible non-critical event is queued${attention === ATTENTION.BUSY ? ' until the attention channel is idle' : ' because attention state is unknown'}.`;
    } else if (priority === URGENCY.LOW) {
      decision = DECISION.RECORD;
      reasonCode = 'low_priority_recorded';
      reasonText = 'Low-priority event is recorded without interrupting or queueing a haptic alert.';
    } else {
      decision = DECISION.RECORD;
      reasonCode = 'urgency_unknown_recorded';
      reasonText = 'Urgency evidence is insufficient; event is recorded without an interrupt or haptic cue.';
    }
  }

  log.push(entry(reasonCode, reasonText));
  const hapticMessage = makeHapticMessage({ decision, priority, soundCategory, directionEvidence: directionEvidence.accepted ? directionEvidence.value : null });

  return {
    event: {
      category: reportedCategory,
      candidateCategory,
      confidence,
      state: eventState,
      timestamp,
      directionEvidence: directionEvidence.accepted ? directionEvidence.value : null,
    },
    priority,
    decision,
    reason: { code: reasonCode, explanation: reasonText },
    hapticMessage,
    decisionLog: log,
    thresholdProfile: { ...thresholds, provisional: true },
  };
}

function nonFirePriority(urgency) {
  if (urgency === URGENCY.UNKNOWN) return URGENCY.UNKNOWN;
  if (urgency === URGENCY.CRITICAL) return URGENCY.HIGH;
  // A siren label alone does not imply danger; only supplied urgency is used.
  return urgency;
}

function makeHapticMessage({ decision, priority, soundCategory, directionEvidence }) {
  if (decision === DECISION.QUEUE) {
    return { pattern: 'none', message: 'Queued until attention is available; no haptic is sent now.', directionCue: null };
  }
  if (decision === DECISION.RECORD) {
    return { pattern: 'none', message: 'Record only; no haptic alert is recommended.', directionCue: null };
  }

  if (priority === URGENCY.CRITICAL) {
    return { pattern: 'critical_repeating', message: 'Immediate fire-alarm alert. Use the repeating critical haptic pattern.', directionCue: null };
  }
  const pattern = priority === URGENCY.HIGH ? 'urgent_pulse' : 'gentle_single_pulse';
  const direction = directionEvidence ? ` Provided direction cue: ${directionEvidence.direction}.` : '';
  return {
    pattern,
    message: `${soundCategory.replaceAll('_', ' ')} alert.${direction}`,
    directionCue: directionEvidence?.direction || null,
  };
}

function validateDirectionEvidence(evidence, threshold) {
  if (!evidence || typeof evidence !== 'object') return { provided: false, accepted: false, value: null };
  const direction = typeof evidence.direction === 'string' ? evidence.direction.trim().toLowerCase() : '';
  const source = typeof evidence.source === 'string' ? evidence.source.trim() : '';
  const confidence = validScore(evidence.confidence) ? evidence.confidence : null;
  if (!['left', 'right', 'front', 'rear'].includes(direction) || !source || confidence === null) {
    return { provided: true, accepted: false, value: null, reason: 'Direction evidence lacks a valid direction, named source, or 0..1 confidence score.' };
  }
  if (/single\s*[- ]?\s*microphone|\bmono\b/i.test(source)) {
    return { provided: true, accepted: false, value: null, reason: 'Direction from a single/mono microphone is not accepted.' };
  }
  if (confidence < threshold) {
    return { provided: true, accepted: false, value: null, reason: `Direction confidence is below the provisional ${threshold} threshold.` };
  }
  return { provided: true, accepted: true, value: { direction, source, confidence } };
}

function validScore(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
}

function validateThresholds(thresholds) {
  for (const key of ['minimumDecisionConfidence', 'minimumDirectionEvidenceConfidence']) {
    if (!validScore(thresholds[key])) throw new RangeError(`${key} must be a number between 0 and 1.`);
  }
}

function entry(code, message) {
  return { code, message };
}

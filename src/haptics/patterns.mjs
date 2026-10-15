import { SOUND_LABELS } from '../sound-analysis/analysis.mjs';

export const GLOVE_POSITIONS = Object.freeze(['front', 'back', 'left', 'right']);

export const HAPTIC_URGENCY = Object.freeze({
  LOW: 'low',
  NORMAL: 'normal',
  HIGH: 'high',
  CRITICAL: 'critical',
  UNKNOWN: 'unknown',
});

export const PATTERN_DEFINITIONS = Object.freeze({
  [SOUND_LABELS.FIRE_ALARM]: Object.freeze({
    title: 'Fire alarm', rhythmName: 'Triple knock',
    explanation: 'Two short pulses followed by one long pulse. Fire alarms are always composed at critical intensity.',
    pulseDurationsMs: Object.freeze([100, 100, 420]), gapDurationsMs: Object.freeze([110, 110, 460]), repeatCount: 2, critical: true,
  }),
  [SOUND_LABELS.SIREN]: Object.freeze({
    title: 'Emergency vehicle siren', rhythmName: 'Alternating sweep',
    explanation: 'A short, long, short rhythm distinguishes a siren. Intensity still comes from the urgency estimate.',
    pulseDurationsMs: Object.freeze([120, 310, 120]), gapDurationsMs: Object.freeze([100, 100, 300]), repeatCount: 1, critical: false,
  }),
  [SOUND_LABELS.VEHICLE_HORN]: Object.freeze({
    title: 'Vehicle horn', rhythmName: 'Long then short',
    explanation: 'One long pulse followed by a short pulse. A position cue is used only when direction is provided.',
    pulseDurationsMs: Object.freeze([300, 130]), gapDurationsMs: Object.freeze([130, 380]), repeatCount: 1, critical: false,
  }),
  [SOUND_LABELS.DOORBELL]: Object.freeze({
    title: 'Doorbell', rhythmName: 'Ding-dong',
    explanation: 'Two evenly separated pulses provide a familiar, non-critical reminder.',
    pulseDurationsMs: Object.freeze([120, 220]), gapDurationsMs: Object.freeze([150, 380]), repeatCount: 1, critical: false,
  }),
  [SOUND_LABELS.HUMAN_CALLING]: Object.freeze({
    title: 'Human calling or shouting', rhythmName: 'Two calls',
    explanation: 'Two longer pulses distinguish a human call from alarms and short chimes.',
    pulseDurationsMs: Object.freeze([240, 240]), gapDurationsMs: Object.freeze([160, 420]), repeatCount: 1, critical: false,
  }),
  [SOUND_LABELS.UNKNOWN]: Object.freeze({
    title: 'Unknown or uncertain sound', rhythmName: 'Three soft taps',
    explanation: 'Three separated light taps mean the sound is unknown or uncertain; review the screen for context.',
    pulseDurationsMs: Object.freeze([80, 80, 80]), gapDurationsMs: Object.freeze([180, 180, 360]), repeatCount: 1, critical: false,
  }),
});

const INTENSITIES = Object.freeze({
  [HAPTIC_URGENCY.LOW]: Object.freeze({ level: 1, name: 'Low', amplitude: 0.25 }),
  [HAPTIC_URGENCY.NORMAL]: Object.freeze({ level: 2, name: 'Normal', amplitude: 0.45 }),
  [HAPTIC_URGENCY.HIGH]: Object.freeze({ level: 3, name: 'High', amplitude: 0.7 }),
  [HAPTIC_URGENCY.CRITICAL]: Object.freeze({ level: 4, name: 'Critical', amplitude: 1 }),
  [HAPTIC_URGENCY.UNKNOWN]: Object.freeze({ level: 1, name: 'Low (uncertain)', amplitude: 0.25 }),
});

/** Compose category rhythm, urgency intensity, and glove actuator position. */
export function composeHapticPattern({ soundCategory, urgency = HAPTIC_URGENCY.UNKNOWN, direction = 'unknown' } = {}) {
  const category = Object.hasOwn(PATTERN_DEFINITIONS, soundCategory) ? soundCategory : SOUND_LABELS.UNKNOWN;
  const definition = PATTERN_DEFINITIONS[category];
  const normalizedUrgency = Object.hasOwn(INTENSITIES, urgency) ? urgency : HAPTIC_URGENCY.UNKNOWN;
  // The alert policy always treats a fire-alarm category as critical.
  const effectiveUrgency = definition.critical ? HAPTIC_URGENCY.CRITICAL : normalizedUrgency;
  const intensity = INTENSITIES[effectiveUrgency];
  const directionMode = GLOVE_POSITIONS.includes(direction) ? 'directional' : 'undirected';
  const actuatorPositions = directionMode === 'directional' ? [direction] : [...GLOVE_POSITIONS];
  const totalDurationMs = definition.repeatCount * definition.pulseDurationsMs.reduce((sum, duration, index) => sum + duration + definition.gapDurationsMs[index], 0);

  return {
    category,
    urgency: effectiveUrgency,
    intensity,
    rhythmName: definition.rhythmName,
    pulseDurationsMs: [...definition.pulseDurationsMs],
    gapDurationsMs: [...definition.gapDurationsMs],
    repeatCount: definition.repeatCount,
    directionMode,
    direction: directionMode === 'directional' ? direction : null,
    actuatorPositions,
    totalDurationMs,
    critical: definition.critical,
    explanation: definition.explanation,
  };
}

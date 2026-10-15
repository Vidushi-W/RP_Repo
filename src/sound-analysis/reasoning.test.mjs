import test from 'node:test';
import assert from 'node:assert/strict';
import { SOUND_LABELS } from './analysis.mjs';
import { ATTENTION, DECISION, URGENCY, createReasoningEngine, reasonEvent } from './reasoning.mjs';

const fixedNow = () => new Date('2026-10-15T08:30:00.000Z');
const evaluate = input => reasonEvent(input, { now: fixedNow });

test('confirmed fire alarm interrupts immediately while attention is busy', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.FIRE_ALARM,
    confidence: 0.91,
    estimatedUrgency: URGENCY.LOW,
    attentionChannelState: ATTENTION.BUSY,
    availableDirectionEvidence: null,
  });

  assert.equal(result.event.state, 'confirmed');
  assert.equal(result.priority, URGENCY.CRITICAL);
  assert.equal(result.decision, DECISION.INTERRUPT);
  assert.equal(result.hapticMessage.pattern, 'critical_repeating');
  assert.equal(result.reason.code, 'confirmed_fire_alarm_safety_override');
  assert.equal(result.event.timestamp, '2026-10-15T08:30:00.000Z');
});

test('non-critical high urgency event interrupts while idle', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.DOORBELL,
    confidence: 0.88,
    estimatedUrgency: URGENCY.HIGH,
    attentionChannelState: ATTENTION.IDLE,
  });
  assert.equal(result.priority, URGENCY.HIGH);
  assert.equal(result.decision, DECISION.INTERRUPT);
  assert.equal(result.hapticMessage.pattern, 'urgent_pulse');
});

test('eligible non-critical events queue while busy', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.HUMAN_CALLING,
    confidence: 0.84,
    estimatedUrgency: URGENCY.NORMAL,
    attentionChannelState: ATTENTION.BUSY,
  });
  assert.equal(result.priority, URGENCY.NORMAL);
  assert.equal(result.decision, DECISION.QUEUE);
  assert.equal(result.hapticMessage.pattern, 'none');
  assert.match(result.reason.explanation, /queued/i);
});

test('low confidence is explicitly uncertain and recorded', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.VEHICLE_HORN,
    confidence: 0.42,
    estimatedUrgency: URGENCY.HIGH,
    attentionChannelState: ATTENTION.IDLE,
  });
  assert.equal(result.event.state, 'uncertain');
  assert.equal(result.event.category, SOUND_LABELS.UNKNOWN);
  assert.equal(result.event.candidateCategory, SOUND_LABELS.VEHICLE_HORN);
  assert.equal(result.priority, URGENCY.UNKNOWN);
  assert.equal(result.decision, DECISION.RECORD);
  assert.equal(result.reason.code, 'uncertain_confidence');
  assert.equal(result.hapticMessage.pattern, 'none');
});

test('unknown categories are recorded without inventing context', () => {
  const result = evaluate({
    soundCategory: 'vehicle',
    confidence: 0.99,
    estimatedUrgency: URGENCY.HIGH,
    attentionChannelState: ATTENTION.BUSY,
    availableDirectionEvidence: null,
  });
  assert.equal(result.event.category, SOUND_LABELS.UNKNOWN);
  assert.equal(result.event.candidateCategory, 'vehicle');
  assert.equal(result.event.state, 'unknown');
  assert.equal(result.decision, DECISION.RECORD);
  assert.equal(result.event.directionEvidence, null);
});

test('siren does not become immediate danger without a high urgency estimate', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.SIREN,
    confidence: 0.93,
    estimatedUrgency: URGENCY.LOW,
    attentionChannelState: ATTENTION.IDLE,
  });
  assert.equal(result.priority, URGENCY.LOW);
  assert.equal(result.decision, DECISION.RECORD);
  assert.equal(result.reason.code, 'low_priority_recorded');
  assert.ok(result.decisionLog.some(item => item.code === 'siren_context_required'));
});

test('horn uses only supplied urgency and accepts only explicit independent direction evidence', () => {
  const accepted = evaluate({
    soundCategory: SOUND_LABELS.VEHICLE_HORN,
    confidence: 0.9,
    estimatedUrgency: URGENCY.NORMAL,
    attentionChannelState: ATTENTION.IDLE,
    availableDirectionEvidence: { direction: 'right', source: 'stereo array', confidence: 0.88 },
  });
  assert.equal(accepted.priority, URGENCY.NORMAL);
  assert.equal(accepted.decision, DECISION.INTERRUPT);
  assert.equal(accepted.hapticMessage.directionCue, 'right');

  const rejected = evaluate({
    soundCategory: SOUND_LABELS.VEHICLE_HORN,
    confidence: 0.9,
    estimatedUrgency: URGENCY.NORMAL,
    attentionChannelState: ATTENTION.IDLE,
    availableDirectionEvidence: { direction: 'left', source: 'single microphone', confidence: 0.99 },
  });
  assert.equal(rejected.event.directionEvidence, null);
  assert.equal(rejected.hapticMessage.directionCue, null);
  assert.ok(rejected.decisionLog.some(item => item.code === 'direction_evidence_rejected'));
});

test('provisional thresholds can be configured and are surfaced in every result', () => {
  const engine = createReasoningEngine({
    thresholds: { minimumDecisionConfidence: 0.8, minimumDirectionEvidenceConfidence: 0.9 },
    now: fixedNow,
  });
  const result = engine.evaluate({
    soundCategory: SOUND_LABELS.DOORBELL,
    confidence: 0.79,
    estimatedUrgency: URGENCY.NORMAL,
    attentionChannelState: ATTENTION.IDLE,
  });
  assert.equal(result.event.state, 'uncertain');
  assert.equal(result.thresholdProfile.minimumDecisionConfidence, 0.8);
  assert.equal(result.thresholdProfile.provisional, true);
});

test('queues a non-critical alert when attention state is missing instead of interrupting', () => {
  const result = evaluate({
    soundCategory: SOUND_LABELS.DOORBELL,
    confidence: 0.9,
    estimatedUrgency: URGENCY.HIGH,
    attentionChannelState: 'unknown',
  });
  assert.equal(result.decision, DECISION.QUEUE);
  assert.ok(result.decisionLog.some(item => item.code === 'attention_state_unknown'));
});

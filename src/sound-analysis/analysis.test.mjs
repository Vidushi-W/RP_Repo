import test from 'node:test';
import assert from 'node:assert/strict';
import { createSoundAnalyzer, SOUND_LABELS } from './analysis.mjs';

const fixedTime = () => new Date('2026-10-15T08:00:00.000Z');
const mockAdapter = output => ({ modelName: 'mock-model', analyzeAudioFile: async () => output });

test('returns structured ready results for each supported sound category', async () => {
  const labels = [
    SOUND_LABELS.FIRE_ALARM,
    SOUND_LABELS.SIREN,
    SOUND_LABELS.VEHICLE_HORN,
    SOUND_LABELS.DOORBELL,
    SOUND_LABELS.HUMAN_CALLING,
  ];

  for (const label of labels) {
    const analyze = createSoundAnalyzer({
      adapter: mockAdapter({ label, score: 0.92, modelStatus: { status: 'ready', modelName: 'mock-model' } }),
      now: fixedTime,
    });
    const result = await analyze.analyzeAudioFile({ uri: 'file:///private/test.wav', mimeType: 'audio/wav' });
    assert.deepEqual(result, {
      label,
      score: 0.92,
      timestamp: '2026-10-15T08:00:00.000Z',
      modelStatus: { status: 'ready', modelName: 'mock-model' },
      reason: 'classified',
      candidateLabel: label,
    });
  }
});

test('maps predictions below the confidence threshold to unknown explicitly', async () => {
  const analyze = createSoundAnalyzer({
    adapter: mockAdapter({ label: SOUND_LABELS.DOORBELL, score: 0.42, modelStatus: { status: 'ready' } }),
    threshold: 0.65,
    now: fixedTime,
  });
  const result = await analyze.analyzeAudioFile({ uri: 'file:///private/test.wav' });
  assert.equal(result.label, SOUND_LABELS.UNKNOWN);
  assert.equal(result.candidateLabel, SOUND_LABELS.DOORBELL);
  assert.equal(result.reason, 'low_confidence');
  assert.equal(result.score, 0.42);
});

test('does not promote generic vehicle predictions to an emergency siren', async () => {
  const analyze = createSoundAnalyzer({
    adapter: mockAdapter({ label: 'vehicle', score: 0.99, modelStatus: { status: 'ready' } }),
    now: fixedTime,
  });
  const result = await analyze.analyzeAudioFile({ uri: 'file:///private/test.wav' });
  assert.equal(result.label, SOUND_LABELS.UNKNOWN);
  assert.equal(result.reason, 'unsupported_sound');
  assert.equal(result.candidateLabel, 'vehicle');
});

test('reports unknown classes, unavailable models, invalid files, and inference failures', async () => {
  const timestamp = '2026-10-15T08:00:00.000Z';
  const unknown = createSoundAnalyzer({
    adapter: mockAdapter({ label: SOUND_LABELS.UNKNOWN, score: 0.8, modelStatus: { status: 'ready' } }),
    now: fixedTime,
  });
  assert.equal((await unknown.analyzeAudioFile({ uri: 'file:///private/test.wav' })).reason, 'unknown_sound');

  const noModel = createSoundAnalyzer({ now: fixedTime });
  assert.deepEqual(await noModel.analyzeAudioFile({ uri: 'file:///private/test.wav' }), {
    label: SOUND_LABELS.UNKNOWN,
    score: null,
    timestamp,
    modelStatus: { status: 'unavailable', modelName: null },
    reason: 'inference_unavailable',
    candidateLabel: null,
  });
  assert.equal((await noModel.analyzeAudioFile(null)).reason, 'invalid_audio_file');

  const broken = createSoundAnalyzer({
    adapter: { modelName: 'mock-model', analyzeAudioFile: async () => { throw new Error('inference failed'); } },
    now: fixedTime,
  });
  const failed = await broken.analyzeAudioFile({ uri: 'file:///private/test.wav' });
  assert.equal(failed.modelStatus.status, 'error');
  assert.equal(failed.reason, 'inference_error');
  assert.equal(failed.label, SOUND_LABELS.UNKNOWN);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { createSettingsStore, DEFAULT_PREFERENCES, normalizePreferences, validateCategory, validateSample } from './settingsStore.mjs';

function memoryStorage() {
  const data = new Map();
  return { getItem: async key => data.get(key) ?? null, setItem: async (key, value) => data.set(key, value) };
}

test('audio retention defaults off and invalid preference values fall back safely', () => {
  assert.equal(DEFAULT_PREFERENCES.retainAudioSamples, false);
  assert.deepEqual(normalizePreferences({ hapticIntensity: 'unsafe', phoneVibrationEnabled: 'yes', retainAudioSamples: 1 }), DEFAULT_PREFERENCES);
});

test('validates added category names and duplicates', () => {
  assert.equal(validateCategory('  Train  horn ', ['Fire alarm']), 'Train horn');
  assert.throws(() => validateCategory('x'), /2 to 40/);
  assert.throws(() => validateCategory('Doorbell', ['doorbell']), /already exists/);
  assert.throws(() => validateCategory('Siren💥'), /Use letters/);
});

test('requires informed audio retention before accepting a labelled sample', async () => {
  const store = createSettingsStore(memoryStorage());
  await assert.rejects(store.addSample({ filename: 'clip.wav', category: 'Doorbell', uri: 'file:///sample.wav' }), /Enable audio retention/);
  await store.updatePreferences({ retainAudioSamples: true });
  const updated = await store.addSample({ filename: 'clip.wav', category: 'Doorbell', uri: 'file:///sample.wav' });
  assert.equal(updated.samples.length, 1);
  assert.equal(updated.samples[0].category, 'Doorbell');
  assert.equal(updated.samples[0].status, 'stored_locally_not_used_for_training');
  assert.throws(() => validateSample({ filename: 'clip.txt', category: 'Doorbell', uri: 'file:///clip.txt' }), /audio clip/);
  assert.throws(() => validateSample({ filename: 'clip.wav', category: '', uri: 'file:///clip.wav' }), /Select a category/);
});

test('persists preferences and custom categories; reset removes sample metadata', async () => {
  const storage = memoryStorage();
  const store = createSettingsStore(storage);
  await store.updatePreferences({ hapticIntensity: 'high', retainAudioSamples: true });
  await store.addCategory('Train horn');
  await store.addSample({ filename: 'train.wav', category: 'Train horn', uri: 'file:///train.wav' });
  const saved = await createSettingsStore(storage).load();
  assert.equal(saved.preferences.hapticIntensity, 'high');
  assert.ok(saved.categories.includes('Train horn'));
  assert.equal(saved.samples.length, 1);
  const reset = await store.resetPreferences();
  assert.deepEqual(reset.preferences, DEFAULT_PREFERENCES);
  assert.equal(reset.samples.length, 0);
});

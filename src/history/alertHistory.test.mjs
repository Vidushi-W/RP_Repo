import test from 'node:test';
import assert from 'node:assert/strict';
import { ALERT_FEEDBACK, createAlertHistoryStore, filterAlerts } from './alertHistory.mjs';
import { reasonEvent } from '../sound-analysis/reasoning.mjs';

function memoryStorage() {
  const values = new Map();
  return {
    getItem: async key => values.get(key) ?? null,
    setItem: async (key, value) => values.set(key, value),
    peek: key => values.get(key),
  };
}

test('persists and reloads structured metadata without raw audio', async () => {
  const storage = memoryStorage();
  const store = createAlertHistoryStore(storage);
  await store.record({ id: 'a1', label: 'Doorbell', timestamp: '2026-10-15T10:00:00.000Z', urgency: 'low', confidence: 88, direction: null, action: 'Recorded', rawAudio: 'sensitive-bytes', audioUri: '/private/sample.wav' });
  const reloaded = await createAlertHistoryStore(storage).load();
  assert.equal(reloaded.length, 1);
  assert.equal(reloaded[0].label, 'Doorbell');
  assert.equal(reloaded[0].direction, 'Unknown');
  assert.equal(reloaded[0].confidence, 88);
  assert.equal(reloaded[0].action, 'Recorded');
  assert.doesNotMatch(storage.peek('signlanka.alert-history.v1'), /sensitive-bytes|private\/sample/);
});

test('filters by event and urgency and excludes dismissed alerts by default', () => {
  const records = [
    { label: 'Fire alarm', urgency: 'critical', dismissed: false },
    { label: 'Doorbell', urgency: 'low', dismissed: false },
    { label: 'Doorbell', urgency: 'low', dismissed: true },
  ];
  assert.equal(filterAlerts(records, { event: 'Doorbell' }).length, 1);
  assert.equal(filterAlerts(records, { urgency: 'critical' })[0].label, 'Fire alarm');
  assert.equal(filterAlerts(records, { event: 'Doorbell', urgency: 'low', includeDismissed: true }).length, 2);
});

test('feedback persists as evaluation metadata without changing critical safety priority', async () => {
  const storage = memoryStorage();
  const store = createAlertHistoryStore(storage);
  await store.record({ id: 'critical-1', label: 'Fire alarm', urgency: 'critical', action: 'Interrupted', priority: 'critical', critical: true, reason: 'Immediate fixed safety priority.' });
  const withFeedback = await store.setFeedback('critical-1', ALERT_FEEDBACK.INCORRECT);
  assert.equal(withFeedback[0].feedback, 'incorrect');
  assert.equal(withFeedback[0].priority, 'critical');
  assert.equal(withFeedback[0].critical, true);
  assert.equal(withFeedback[0].action, 'Interrupted');
  await store.dismiss('critical-1');
  const dismissed = await store.load();
  assert.equal(dismissed[0].dismissed, true);
  assert.equal(dismissed[0].priority, 'critical');
});

test('rejects unsupported feedback values', async () => {
  const store = createAlertHistoryStore(memoryStorage());
  await assert.rejects(store.setFeedback('missing', 'train'), /Unsupported feedback/);
});

test('accepts structured reasoning results and maps decisions without losing the reason log', async () => {
  const storage = memoryStorage();
  const store = createAlertHistoryStore(storage);
  const result = reasonEvent({ soundCategory: 'fire_alarm', confidence: 0.94, estimatedUrgency: 'low', attentionChannelState: 'busy' }, { now: () => new Date('2026-10-15T10:30:00.000Z') });
  const [alert] = await store.record({ ...result, rawAudio: 'must-not-persist' });
  assert.equal(alert.action, 'Interrupted');
  assert.equal(alert.priority, 'critical');
  assert.equal(alert.confidence, 94);
  assert.ok(alert.reasonLog.some(entry => entry.code === 'confirmed_fire_alarm_safety_override'));
  assert.doesNotMatch(storage.peek('signlanka.alert-history.v1'), /must-not-persist/);
});

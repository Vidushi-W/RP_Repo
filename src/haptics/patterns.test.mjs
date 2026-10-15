import test from 'node:test';
import assert from 'node:assert/strict';
import { SOUND_LABELS } from '../sound-analysis/analysis.mjs';
import { GLOVE_POSITIONS, HAPTIC_URGENCY, PATTERN_DEFINITIONS, composeHapticPattern } from './patterns.mjs';
import { createBleActuatorAdapter, encodeActuatorCommand } from './bleActuatorAdapter.mjs';

test('each sound category maps to a reusable, distinct rhythm', () => {
  const categories = [
    SOUND_LABELS.FIRE_ALARM, SOUND_LABELS.SIREN, SOUND_LABELS.VEHICLE_HORN,
    SOUND_LABELS.DOORBELL, SOUND_LABELS.HUMAN_CALLING, SOUND_LABELS.UNKNOWN,
  ];
  const rhythms = categories.map(category => composeHapticPattern({ soundCategory: category }).pulseDurationsMs.join(','));
  assert.equal(Object.keys(PATTERN_DEFINITIONS).length, categories.length);
  assert.equal(new Set(rhythms).size, categories.length);
});

test('urgency changes intensity without changing category rhythm', () => {
  const levels = [HAPTIC_URGENCY.LOW, HAPTIC_URGENCY.NORMAL, HAPTIC_URGENCY.HIGH, HAPTIC_URGENCY.CRITICAL]
    .map(urgency => composeHapticPattern({ soundCategory: SOUND_LABELS.DOORBELL, urgency }));
  assert.deepEqual(levels.map(pattern => pattern.intensity.level), [1, 2, 3, 4]);
  assert.ok(levels.every(pattern => pattern.pulseDurationsMs.join(',') === levels[0].pulseDurationsMs.join(',')));
});

test('fire alarm always composes as critical and visually marked', () => {
  const pattern = composeHapticPattern({ soundCategory: SOUND_LABELS.FIRE_ALARM, urgency: HAPTIC_URGENCY.LOW });
  assert.equal(pattern.urgency, HAPTIC_URGENCY.CRITICAL);
  assert.equal(pattern.intensity.amplitude, 1);
  assert.equal(pattern.critical, true);
  assert.equal(pattern.repeatCount, 2);
});

test('direction maps to one actuator; unknown direction produces an undirected whole-glove pattern', () => {
  const right = composeHapticPattern({ soundCategory: SOUND_LABELS.VEHICLE_HORN, direction: 'right' });
  assert.deepEqual(right.actuatorPositions, ['right']);
  assert.equal(right.directionMode, 'directional');

  const unknown = composeHapticPattern({ soundCategory: SOUND_LABELS.DOORBELL, direction: 'unknown' });
  assert.deepEqual(unknown.actuatorPositions, GLOVE_POSITIONS);
  assert.equal(unknown.directionMode, 'undirected');
  assert.equal(unknown.direction, null);
});

test('unsupported category falls back to the explicit unknown rhythm', () => {
  const pattern = composeHapticPattern({ soundCategory: 'ambulance', urgency: 'extreme' });
  assert.equal(pattern.category, SOUND_LABELS.UNKNOWN);
  assert.equal(pattern.urgency, HAPTIC_URGENCY.UNKNOWN);
  assert.deepEqual(pattern.pulseDurationsMs, [...PATTERN_DEFINITIONS[SOUND_LABELS.UNKNOWN].pulseDurationsMs]);
});

test('BLE adapter reports disconnected by default and never claims tested actuation', async () => {
  const offline = createBleActuatorAdapter();
  const pattern = composeHapticPattern({ soundCategory: SOUND_LABELS.FIRE_ALARM });
  assert.equal(await offline.getStatus(), 'disconnected');
  assert.deepEqual(await offline.sendPattern(pattern), { status: 'disconnected', hardwareTested: false });

  let command;
  const transport = { isConnected: async () => true, write: async value => { command = value; } };
  const adapter = createBleActuatorAdapter({ transport });
  assert.equal(await adapter.getStatus(), 'connected_unverified');
  assert.deepEqual(await adapter.sendPattern(pattern), { status: 'command_written_unverified', hardwareTested: false });
  assert.equal(command.protocol, 'signlanka-haptics-v1');
  assert.equal(command.critical, true);
});

test('direction is serialized as actuator position in future BLE payloads', () => {
  const pattern = composeHapticPattern({ soundCategory: SOUND_LABELS.SIREN, urgency: HAPTIC_URGENCY.HIGH, direction: 'front' });
  const command = encodeActuatorCommand(pattern);
  assert.deepEqual(command.actuators, ['front']);
  assert.equal(command.intensity.level, 3);
  assert.deepEqual(command.rhythm.onMs, pattern.pulseDurationsMs);
});

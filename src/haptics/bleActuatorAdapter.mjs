/** Protocol-neutral BLE payload boundary. No BLE transport or glove is included. */
export function encodeActuatorCommand(pattern) {
  return {
    protocol: 'signlanka-haptics-v1',
    category: pattern.category,
    rhythm: { onMs: [...pattern.pulseDurationsMs], gapMs: [...pattern.gapDurationsMs], repeats: pattern.repeatCount },
    intensity: { level: pattern.intensity.level, amplitude: pattern.intensity.amplitude },
    actuators: [...pattern.actuatorPositions],
    critical: pattern.critical,
  };
}

/**
 * Future BLE adapter seam. A transport write is not proof of motor actuation;
 * report it as unverified until the command is tested on a connected glove.
 */
export function createBleActuatorAdapter({ transport = null } = {}) {
  async function getStatus() {
    if (!transport || typeof transport.isConnected !== 'function' || !(await transport.isConnected())) return 'disconnected';
    return 'connected_unverified';
  }

  return {
    getStatus,
    async sendPattern(pattern) {
      const status = await getStatus();
      if (status !== 'connected_unverified' || typeof transport.write !== 'function') {
        return { status: 'disconnected', hardwareTested: false };
      }
      await transport.write(encodeActuatorCommand(pattern));
      return { status: 'command_written_unverified', hardwareTested: false };
    },
  };
}

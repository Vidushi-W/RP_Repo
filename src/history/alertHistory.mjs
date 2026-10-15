export const ALERT_FEEDBACK = Object.freeze({ HELPFUL: 'helpful', NOT_HELPFUL: 'not_helpful', INCORRECT: 'incorrect' });
export const ALERT_ACTIONS = Object.freeze(['Interrupted', 'Queued', 'Recorded', 'Uncertain']);
export const ALERT_HISTORY_KEY = 'signlanka.alert-history.v1';

const validFeedback = new Set(Object.values(ALERT_FEEDBACK));

/** Store structured alert metadata only. Raw audio and audio paths are discarded. */
export function normalizeAlert(alert) {
  const { rawAudio, audio, audioUri, audioPath, ...metadata } = alert;
  const sourceEvent = metadata.event || {};
  const decision = metadata.decision || metadata.action;
  const decisionAction = decision === 'interrupt' ? 'Interrupted' : decision === 'queue' ? 'Queued' : decision === 'record' ? 'Recorded' : null;
  const derivedAction = sourceEvent.state === 'uncertain' || sourceEvent.state === 'unknown' ? 'Uncertain' : decisionAction;
  const reasonText = typeof metadata.reason === 'string' ? metadata.reason : metadata.reason?.explanation || metadata.reasoning?.explanation;
  const log = metadata.reasonLog || metadata.decisionLog || metadata.reasoning?.log;
  const urgencyValue = metadata.urgency || metadata.priority || 'unknown';
  const timestamp = metadata.timestamp || sourceEvent.timestamp || new Date().toISOString();
  const label = String(metadata.label || metadata.kind || sourceEvent.category || 'Unknown sound');
  const action = ALERT_ACTIONS.includes(metadata.action) ? metadata.action : ALERT_ACTIONS.includes(derivedAction) ? derivedAction : 'Uncertain';
  const reason = reasonText || metadata.reasoning?.explanation || 'Insufficient reasoning detail was recorded.';
  return {
    id: metadata.id || `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    label,
    kind: label,
    timestamp,
    time: timestamp,
    urgency: String(urgencyValue).toLowerCase(),
    confidence: Number.isFinite(metadata.confidence) ? (metadata.confidence <= 1 ? metadata.confidence * 100 : metadata.confidence) : Number.isFinite(sourceEvent.confidence) ? sourceEvent.confidence * 100 : null,
    direction: metadata.direction || sourceEvent.directionEvidence?.direction || 'Unknown',
    action,
    decision: action,
    detail: reason,
    reason,
    reasonLog: Array.isArray(log) ? log : [],
    priority: String(metadata.priority || 'normal').toLowerCase(),
    critical: Boolean(metadata.critical || String(metadata.priority || '').toLowerCase() === 'critical'),
    dismissed: Boolean(metadata.dismissed),
    feedback: validFeedback.has(metadata.feedback) ? metadata.feedback : null,
    demo: Boolean(metadata.demo),
  };
}

export function filterAlerts(alerts, { event = 'all', urgency = 'all', includeDismissed = false } = {}) {
  return alerts.filter(alert => (includeDismissed || !alert.dismissed)
    && (event === 'all' || alert.label === event)
    && (urgency === 'all' || alert.urgency.toLowerCase() === urgency.toLowerCase()));
}

export function createAlertHistoryStore(storage, key = ALERT_HISTORY_KEY) {
  async function read() {
    const serialized = await storage.getItem(key);
    if (!serialized) return [];
    try {
      const parsed = JSON.parse(serialized);
      return Array.isArray(parsed) ? parsed.map(normalizeAlert) : [];
    } catch {
      return [];
    }
  }
  async function write(alerts) {
    await storage.setItem(key, JSON.stringify(alerts.map(normalizeAlert)));
    return alerts;
  }
  return {
    load: read,
    async record(alert) {
      const normalized = normalizeAlert(alert);
      const current = await read();
      return write([normalized, ...current.filter(item => item.id !== normalized.id)]);
    },
    async recordMany(alerts) {
      const current = await read();
      const byId = new Map(current.map(item => [item.id, item]));
      for (const alert of alerts) if (!byId.has(alert.id)) byId.set(alert.id, normalizeAlert(alert));
      return write([...byId.values()].sort((a, b) => b.timestamp.localeCompare(a.timestamp)));
    },
    async setFeedback(id, feedback) {
      if (!validFeedback.has(feedback)) throw new Error(`Unsupported feedback: ${feedback}`);
      const current = await read();
      return write(current.map(item => item.id === id ? { ...item, feedback } : item));
    },
    async dismiss(id) {
      const current = await read();
      return write(current.map(item => item.id === id ? { ...item, dismissed: true } : item));
    },
    async clearDemo() {
      const current = await read();
      return write(current.filter(item => !item.demo));
    },
    async clearAll() { return write([]); },
  };
}

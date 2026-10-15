import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAlertHistoryStore, filterAlerts } from '../history/alertHistory.mjs';
import { createSettingsStore, DEFAULT_PREFERENCES } from '../settings/settingsStore.mjs';

const AppContext = createContext(null);
const historyStore = createAlertHistoryStore(AsyncStorage);
const settingsStore = createSettingsStore(AsyncStorage);

const demoEvents = [
  {
    id: 'demo-1', label: 'Fire alarm', timestamp: '2026-10-15T09:05:00.000Z',
    confidence: 98, urgency: 'critical', direction: 'Unknown', action: 'Interrupted', critical: true,
    reason: 'Fire alarm confidence exceeded the provisional safety threshold; critical events interrupt immediately, even when attention is busy.',
    reasonLog: [{ code: 'critical_fire_alarm', explanation: 'Fixed safety priority; attention and feedback cannot suppress this alert.' }], demo: true,
  },
  {
    id: 'demo-2', label: 'Emergency vehicle siren', timestamp: '2026-10-15T09:03:00.000Z',
    confidence: 91, urgency: 'high', direction: 'Unknown', action: 'Queued', critical: false,
    reason: 'Siren was treated as potentially urgent. The supplied attention state was busy, so the non-critical event was queued.',
    reasonLog: [{ code: 'high_priority_queued_while_busy', explanation: 'Queued until the attention channel is available.' }], demo: true,
  },
  {
    id: 'demo-3', label: 'Doorbell', timestamp: '2026-10-15T08:57:00.000Z',
    confidence: 87, urgency: 'low', direction: 'Unknown', action: 'Recorded', critical: false,
    reason: 'Low urgency non-critical event was recorded as a reminder.',
    reasonLog: [{ code: 'low_priority_recorded', explanation: 'No interruption was needed.' }], demo: true,
  },
];

function historyView(alert) {
  return { ...alert, detail: alert.reason, decision: alert.action, time: new Date(alert.timestamp).toLocaleString() };
}

export function AppProvider({ children }) {
  const [demoMode, setDemoMode] = useState(false);
  const [monitoring, setMonitoring] = useState(false);
  const [attentionTestState, setAttentionTestState] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');
  const [preferences, setPreferences] = useState({ ...DEFAULT_PREFERENCES });

  const refreshHistory = useCallback(async () => {
    try { setHistory(await historyStore.load()); setHistoryError(''); }
    catch { setHistoryError('Alert history could not be loaded from this device.'); }
    finally { setHistoryLoading(false); }
  }, []);

  useEffect(() => { refreshHistory(); }, [refreshHistory]);
  useEffect(() => { settingsStore.load().then(saved => setPreferences(saved.preferences)).catch(() => {}); }, []);

  const saveHistory = useCallback(async operation => {
    try { setHistory(await operation()); setHistoryError(''); return true; }
    catch { setHistoryError('Your change could not be saved locally. Please try again.'); return false; }
  }, []);

  const recordAlert = useCallback(alert => saveHistory(historyStore.record(alert)), [saveHistory]);
  const setAlertFeedback = useCallback((id, feedback) => saveHistory(historyStore.setFeedback(id, feedback)), [saveHistory]);
  const dismissAlert = useCallback(id => saveHistory(historyStore.dismiss(id)), [saveHistory]);
  const updatePreferences = useCallback(async changes => {
    try { const saved = await settingsStore.updatePreferences(changes); setPreferences(saved.preferences); return saved.preferences; }
    catch (storageError) { setHistoryError('Your preference could not be saved on this device.'); throw storageError; }
  }, []);

  const visibleHistory = useMemo(() => history
    .filter(item => !item.dismissed && (demoMode ? item.demo : !item.demo))
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp)), [history, demoMode]);
  const alerts = visibleHistory.map(historyView);
  const latestEvent = alerts[0] || null;

  const value = useMemo(() => ({
    demoMode,
    async setDemoMode(enabled) {
      if (enabled) await saveHistory(historyStore.recordMany(demoEvents));
      setDemoMode(enabled);
      setError('');
      if (!enabled) setMonitoring(false);
    },
    monitoring,
    setMonitoring,
    attentionTestState,
    setAttentionTestState,
    connectionStatus: 'disconnected',
    attentionStatus: attentionTestState || (demoMode && monitoring && latestEvent ? 'busy' : 'idle'),
    preferences,
    updatePreferences,
    alerts,
    latestEvent,
    historyLoading,
    historyError,
    historyFilters: filterAlerts,
    recordAlert,
    setAlertFeedback,
    dismissAlert,
    async clearDemoData() {
      const saved = await saveHistory(historyStore.clearDemo());
      if (!saved) return false;
      setDemoMode(false);
      setMonitoring(false);
      setAttentionTestState(null);
      return true;
    },
    async clearAlertHistory() { return saveHistory(historyStore.clearAll()); },
    queuedAlerts: alerts.filter(alert => alert.action === 'Queued'),
    error,
    setError,
    startMonitoring() {
      if (!demoMode) {
        setError('Microphone access and the sound recognition model are not configured yet. No audio is being monitored.');
        return;
      }
      setError('');
      setMonitoring(true);
    },
    stopMonitoring() { setMonitoring(false); setError(''); },
  }), [demoMode, monitoring, attentionTestState, preferences, updatePreferences, alerts, latestEvent, historyLoading, historyError, recordAlert, setAlertFeedback, dismissAlert, error, saveHistory]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useAppState must be used inside AppProvider');
  return context;
}

import React, { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { Card, PageHeader, Pill, StateNotice } from '../components/UI';
import { useAppState } from '../state/AppContext';
import { ALERT_FEEDBACK, filterAlerts } from '../history/alertHistory.mjs';
import { colors } from '../theme';

const urgencyFilters = ['all', 'critical', 'high', 'normal', 'low', 'unknown'];
const feedbackOptions = [
  { value: ALERT_FEEDBACK.HELPFUL, label: 'Helpful', icon: 'thumbs-up' },
  { value: ALERT_FEEDBACK.NOT_HELPFUL, label: 'Not helpful', icon: 'minus-circle' },
  { value: ALERT_FEEDBACK.INCORRECT, label: 'Incorrect', icon: 'alert-circle' },
];

function FilterChips({ label, options, value, onChange }) {
  return <View style={styles.filterBlock}><Text style={styles.filterLabel}>{label}</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
    {options.map(option => <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected: value === option.value }} onPress={() => onChange(option.value)} style={[styles.chip, value === option.value && styles.chipSelected]}><Text style={[styles.chipText, value === option.value && styles.chipTextSelected]}>{option.label}</Text></Pressable>)}
  </ScrollView></View>;
}

function AlertCard({ alert, expanded, onExpand, onFeedback, onDismiss }) {
  const critical = alert.critical || alert.priority === 'critical';
  const actionTone = alert.action === 'Interrupted' ? 'critical' : alert.action === 'Queued' ? 'high' : 'neutral';
  const confidence = alert.confidence == null ? 'Unknown' : `${Math.round(alert.confidence)}%`;
  const time = new Date(alert.timestamp);
  return <Card style={[styles.alertCard, critical && styles.criticalCard]}>
    <View style={styles.eventTop}>
      <View style={[styles.eventIcon, critical && styles.criticalIcon]}><Feather name={critical ? 'alert-triangle' : 'volume-2'} size={18} color={critical ? colors.red : colors.orangeDark} /></View>
      <View style={styles.eventCopy}><Text style={[styles.eventName, critical && styles.criticalText]}>{alert.label}</Text><Text style={styles.eventTime}>{Number.isNaN(time.valueOf()) ? 'Date/time unknown' : time.toLocaleString()}</Text></View>
      <Pill label={alert.urgency} tone={critical ? 'critical' : alert.urgency === 'high' ? 'high' : 'neutral'} />
    </View>
    <View style={styles.metadataGrid}>
      <Metadata label="CONFIDENCE" value={confidence} />
      <Metadata label="DIRECTION" value={alert.direction || 'Unknown'} />
      <View><Text style={styles.metaLabel}>ACTION</Text><Pill label={alert.action} tone={actionTone} /></View>
    </View>
    {critical && <View style={styles.safetyLine}><Feather name="shield" size={14} color={colors.red} /><Text style={styles.safetyText}>Fixed safety priority · feedback cannot lower this alert</Text></View>}
    <Pressable accessibilityRole="button" accessibilityState={{ expanded }} onPress={onExpand} style={styles.reasonToggle}><Text style={styles.reasonToggleText}>{expanded ? 'Hide decision reasoning' : 'View decision reasoning'}</Text><Feather name={expanded ? 'chevron-up' : 'chevron-down'} size={17} color={colors.orangeDark} /></Pressable>
    {expanded && <View style={styles.reasonPanel}>
      <Text style={styles.reasonTitle}>Why this action?</Text><Text style={styles.reasonText}>{alert.reason || 'No reasoning explanation was recorded.'}</Text>
      {!!alert.reasonLog?.length && <View style={styles.reasonLog}>{alert.reasonLog.map((entry, index) => <View key={`${entry.code || 'reason'}-${index}`} style={styles.reasonLogRow}><Feather name="check-circle" size={13} color={critical ? colors.red : colors.orangeDark} /><Text style={styles.reasonLogText}>{entry.explanation || entry.message || entry.code}</Text></View>)}</View>}
      {alert.demo && <Text style={styles.demoLabel}>DEMO SAMPLE</Text>}
    </View>}
    <View style={styles.feedbackHeader}><Text style={styles.feedbackPrompt}>Was this alert useful?</Text>{alert.feedback && <Text style={styles.feedbackSaved}>Saved · {feedbackOptions.find(option => option.value === alert.feedback)?.label || alert.feedback}</Text>}</View>
    <View style={styles.feedbackRow}>{feedbackOptions.map(option => <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected: alert.feedback === option.value }} onPress={() => onFeedback(alert.id, option.value)} style={[styles.feedbackButton, alert.feedback === option.value && styles.feedbackSelected]}><Feather name={option.icon} size={14} color={alert.feedback === option.value ? colors.orangeDark : colors.muted} /><Text style={[styles.feedbackText, alert.feedback === option.value && styles.feedbackTextSelected]}>{option.label}</Text></Pressable>)}</View>
    <Pressable accessibilityRole="button" onPress={() => onDismiss(alert.id)} style={styles.dismissButton}><Feather name="archive" size={14} color={colors.muted} /><Text style={styles.dismissText}>Dismiss from history</Text></Pressable>
  </Card>;
}

function Metadata({ label, value }) { return <View><Text style={styles.metaLabel}>{label}</Text><Text style={styles.metaValue}>{value}</Text></View>; }

export function AlertsScreen() {
  const { alerts, demoMode, historyLoading, historyError, setAlertFeedback, dismissAlert, queuedAlerts } = useAppState();
  const [eventFilter, setEventFilter] = useState('all');
  const [urgencyFilter, setUrgencyFilter] = useState('all');
  const [queueOnly, setQueueOnly] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const eventOptions = useMemo(() => [{ value: 'all', label: 'All events' }, ...[...new Set(alerts.map(alert => alert.label))].map(label => ({ value: label, label }))], [alerts]);
  const filtered = useMemo(() => filterAlerts(alerts, { event: eventFilter, urgency: urgencyFilter }).filter(alert => !queueOnly || alert.action === 'Queued'), [alerts, eventFilter, urgencyFilter, queueOnly]);

  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
    <PageHeader eyebrow="Your activity" title="Alert history" subtitle="Review what was detected, why it was handled that way, and share feedback for future evaluation." />
    {demoMode && <StateNotice icon="play-circle" title="Demo events" body="These clearly labelled examples are samples. They were not recorded from a microphone." tone="success" />}
    {!!historyError && <StateNotice icon="alert-circle" title="History storage issue" body={historyError} tone="error" />}
    {historyLoading ? <View style={styles.loading}><ActivityIndicator color={colors.orangeDark} /><Text style={styles.emptyBody}>Loading saved alert history…</Text></View> : <>
      <Pressable accessibilityRole="button" accessibilityState={{ selected: queueOnly }} onPress={() => setQueueOnly(value => !value)} style={[styles.queueReview, queueOnly && styles.queueReviewActive]}><View style={styles.queueIcon}><Feather name="clock" size={17} color={colors.orangeDark} /></View><View style={styles.queueCopy}><Text style={styles.queueTitle}>Review queued alerts</Text><Text style={styles.queueSubtitle}>{queuedAlerts.length ? `${queuedAlerts.length} waiting for your review` : 'No alerts are currently queued'}</Text></View><View style={styles.queueCount}><Text style={styles.queueCountText}>{queuedAlerts.length}</Text></View></Pressable>
      <FilterChips label="EVENT" options={eventOptions} value={eventFilter} onChange={setEventFilter} />
      <FilterChips label="URGENCY" options={urgencyFilters.map(value => ({ value, label: value === 'all' ? 'All' : value[0].toUpperCase() + value.slice(1) }))} value={urgencyFilter} onChange={setUrgencyFilter} />
      {!alerts.length ? <View style={styles.empty}><View style={styles.emptyIcon}><Feather name="bell-off" size={22} color={colors.muted} /></View><Text style={styles.emptyTitle}>No alerts yet</Text><Text style={styles.emptyBody}>Saved sound events will appear here when detection is configured. This app does not currently monitor audio.</Text></View>
        : !filtered.length ? <View style={styles.filteredEmpty}><Feather name="filter" size={20} color={colors.muted} /><Text style={styles.emptyTitle}>No matching alerts</Text><Text style={styles.emptyBody}>Try another event or urgency filter.</Text></View>
          : filtered.map(alert => <AlertCard key={alert.id} alert={alert} expanded={expandedId === alert.id} onExpand={() => setExpandedId(id => id === alert.id ? null : alert.id)} onFeedback={setAlertFeedback} onDismiss={dismissAlert} />)}
      <Text style={styles.feedbackNote}>Feedback is saved locally for evaluation. It does not train or adapt a model, and cannot change the fixed priority of critical events. Raw audio is not stored.</Text>
    </>}
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream }, content: { padding: 20, paddingTop: 24, paddingBottom: 32, maxWidth: 620, width: '100%', alignSelf: 'center' },
  loading: { alignItems: 'center', gap: 10, paddingVertical: 45 }, empty: { alignItems: 'center', paddingVertical: 50, paddingHorizontal: 24 }, emptyIcon: { width: 54, height: 54, borderRadius: 18, backgroundColor: colors.blueSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 15 }, emptyTitle: { color: colors.navy, fontWeight: '800', fontSize: 16, textAlign: 'center' }, emptyBody: { color: colors.muted, fontSize: 12, lineHeight: 19, textAlign: 'center', marginTop: 6, maxWidth: 300 }, filteredEmpty: { alignItems: 'center', paddingVertical: 38, gap: 8 },
  queueReview: { marginTop: 14, marginBottom: 14, flexDirection: 'row', alignItems: 'center', gap: 11, padding: 13, borderRadius: 16, backgroundColor: colors.surfaceWarm, borderWidth: 1, borderColor: '#F1D6B6' }, queueReviewActive: { borderColor: colors.orangeDark, backgroundColor: '#FFF0DE' }, queueIcon: { width: 37, height: 37, borderRadius: 13, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' }, queueCopy: { flex: 1 }, queueTitle: { color: colors.navy, fontSize: 13, fontWeight: '800' }, queueSubtitle: { color: colors.muted, fontSize: 11, marginTop: 3 }, queueCount: { minWidth: 28, height: 28, borderRadius: 14, backgroundColor: colors.orange, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 }, queueCountText: { color: '#FFFFFF', fontWeight: '900', fontSize: 12 },
  filterBlock: { marginBottom: 10 }, filterLabel: { color: colors.muted, fontSize: 9, letterSpacing: 1, fontWeight: '900', marginBottom: 6 }, chips: { gap: 7, paddingRight: 18 }, chip: { borderRadius: 99, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line, paddingVertical: 7, paddingHorizontal: 11 }, chipSelected: { backgroundColor: colors.orange, borderColor: colors.orangeDark }, chipText: { color: colors.muted, fontSize: 11, fontWeight: '700' }, chipTextSelected: { color: '#FFFFFF' },
  alertCard: { marginTop: 12, padding: 14 }, criticalCard: { borderColor: '#CC7469', borderWidth: 1.6, backgroundColor: '#FFF8F6' }, eventTop: { flexDirection: 'row', gap: 9, alignItems: 'center' }, eventIcon: { width: 40, height: 40, borderRadius: 14, backgroundColor: colors.surfaceWarm, alignItems: 'center', justifyContent: 'center' }, criticalIcon: { backgroundColor: '#FBE0DB' }, eventCopy: { flex: 1 }, eventName: { color: colors.navy, fontSize: 14, fontWeight: '900' }, eventTime: { color: colors.muted, fontSize: 10, marginTop: 4 }, criticalText: { color: colors.red }, metadataGrid: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, marginTop: 15, paddingBottom: 3 }, metaLabel: { color: colors.muted, fontSize: 8, letterSpacing: 0.8, fontWeight: '900', marginBottom: 5 }, metaValue: { color: colors.navy, fontSize: 11, fontWeight: '800' }, safetyLine: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, padding: 9, borderRadius: 10, backgroundColor: '#FBE0DB' }, safetyText: { color: colors.red, fontSize: 10, fontWeight: '800', flex: 1 },
  reasonToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 13, paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line }, reasonToggleText: { color: colors.orangeDark, fontSize: 11, fontWeight: '800' }, reasonPanel: { padding: 11, borderRadius: 12, backgroundColor: '#F8F5EF', marginBottom: 8 }, reasonTitle: { color: colors.navy, fontSize: 11, fontWeight: '900' }, reasonText: { color: colors.navy, fontSize: 11, lineHeight: 17, marginTop: 5 }, reasonLog: { marginTop: 9, gap: 7 }, reasonLogRow: { flexDirection: 'row', gap: 7, alignItems: 'flex-start' }, reasonLogText: { flex: 1, color: colors.muted, fontSize: 10, lineHeight: 15 }, demoLabel: { color: colors.green, fontSize: 9, fontWeight: '900', letterSpacing: 0.8, marginTop: 10 }, feedbackHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 5, marginTop: 5 }, feedbackPrompt: { color: colors.navy, fontSize: 11, fontWeight: '800' }, feedbackSaved: { color: colors.green, fontSize: 9, fontWeight: '800' }, feedbackRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 }, feedbackButton: { minHeight: 34, flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 9, borderRadius: 10, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.cream }, feedbackSelected: { backgroundColor: '#FFF0DE', borderColor: colors.orangeDark }, feedbackText: { color: colors.muted, fontSize: 10, fontWeight: '700' }, feedbackTextSelected: { color: colors.orangeDark }, dismissButton: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingVertical: 9, marginTop: 3 }, dismissText: { color: colors.muted, fontSize: 10, fontWeight: '700' }, feedbackNote: { color: colors.muted, fontSize: 10, lineHeight: 16, textAlign: 'center', marginTop: 20, paddingHorizontal: 9 },
});

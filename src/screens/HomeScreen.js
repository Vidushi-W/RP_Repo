import React from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { Card, IconBox, PageHeader, Pill, SectionTitle, StateNotice } from '../components/UI';
import { useAppState } from '../state/AppContext';
import { createSoundAnalyzer, SOUND_LABELS, unavailableInferenceAdapter } from '../sound-analysis/analysis.mjs';
import { createReasoningEngine } from '../sound-analysis/reasoning.mjs';
import { colors, spacing } from '../theme';

const soundAnalyzer = createSoundAnalyzer({ adapter: unavailableInferenceAdapter });
const reasoningEngine = createReasoningEngine();
const soundNames = {
  [SOUND_LABELS.FIRE_ALARM]: 'Fire alarm',
  [SOUND_LABELS.SIREN]: 'Emergency vehicle siren',
  [SOUND_LABELS.VEHICLE_HORN]: 'Vehicle horn',
  [SOUND_LABELS.DOORBELL]: 'Doorbell',
  [SOUND_LABELS.HUMAN_CALLING]: 'Human calling / shouting',
  [SOUND_LABELS.UNKNOWN]: 'Unknown sound',
};

function Metric({ label, value, helper, icon, tone }) {
  return <View style={styles.metric}>
    <View style={styles.metricTop}><Text style={styles.metricLabel}>{label}</Text><Feather name={icon} size={15} color={tone || colors.muted} /></View>
    <Text style={styles.metricValue}>{value}</Text>
    <Text style={styles.metricHelper}>{helper}</Text>
  </View>;
}

function QuickLink({ icon, label, detail, onPress }) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={styles.quickLink}>
    <IconBox name={icon} size={40} />
    <View style={styles.quickCopy}><Text style={styles.quickLabel}>{label}</Text><Text style={styles.quickDetail}>{detail}</Text></View>
    <Feather name="chevron-right" color={colors.muted} size={18} />
  </Pressable>;
}

function RecentAlertRow({ event }) {
  return <View style={styles.recentRow}>
    <View style={[styles.recentIcon, event.critical && styles.recentIconCritical]}><Feather name={event.critical ? 'alert-triangle' : 'volume-2'} size={16} color={event.critical ? colors.red : colors.orangeDark} /></View>
    <View style={styles.recentCopy}><Text style={styles.recentName}>{event.kind}</Text><Text style={styles.recentMeta}>{event.time}</Text></View>
    <Pill label={event.urgency} tone={event.critical ? 'critical' : 'high'} />
  </View>;
}

export function HomeScreen({ navigate }) {
  const { demoMode, monitoring, startMonitoring, stopMonitoring, connectionStatus, attentionStatus, latestEvent, alerts, error } = useAppState();
  const [isAnalyzingFile, setIsAnalyzingFile] = React.useState(false);
  const [audioResult, setAudioResult] = React.useState(null);
  const [audioDecision, setAudioDecision] = React.useState(null);
  const [audioFileError, setAudioFileError] = React.useState('');
  const attentionLabel = attentionStatus === 'busy' ? 'Busy' : 'Idle';

  async function pickAndAnalyzeFile() {
    setAudioFileError('');
    setAudioResult(null);
    setAudioDecision(null);
    try {
      const picked = await DocumentPicker.getDocumentAsync({ type: 'audio/*', multiple: false, copyToCacheDirectory: false });
      if (picked.canceled) return;
      const file = picked.assets?.[0];
      if (!file) throw new Error('The selected file could not be read.');
      const isAudio = file.mimeType?.startsWith('audio/') || /\.(wav|mp3|m4a|aac|flac|ogg|opus)$/i.test(file.name || '');
      if (!isAudio) {
        setAudioFileError('Choose an audio file such as WAV, MP3, or M4A.');
        return;
      }
      setIsAnalyzingFile(true);
      const result = await soundAnalyzer.analyzeAudioFile({ uri: file.uri, mimeType: file.mimeType });
      // Only the structured prediction is retained; the URI, filename, and audio are discarded.
      setAudioResult(result);
      setAudioDecision(reasoningEngine.evaluate({
        soundCategory: result.label,
        confidence: result.score,
        estimatedUrgency: 'unknown',
        attentionChannelState: attentionStatus,
        availableDirectionEvidence: null,
      }));
    } catch (pickerError) {
      setAudioFileError(pickerError?.message || 'Could not open the selected audio file.');
    } finally {
      setIsAnalyzingFile(false);
    }
  }

  return <ScrollView style={styles.screen} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
    <PageHeader eyebrow="Environmental awareness" title="Your dashboard" subtitle="Stay aware of the sounds around you." right={<View style={styles.brandMark}><Feather name="activity" color={colors.orangeDark} size={21} /></View>} />

    {!demoMode && <StateNotice icon="info" title="Demo mode is off" body="Microphone access and the recognition model are not configured. The app is not listening or detecting sounds." />}
    {demoMode && <StateNotice icon="play-circle" title="Demo mode · sample data" body="This dashboard uses labelled sample events. No microphone, sound model, or glove is connected." tone="success" />}
    {!!error && <View style={styles.spacer}><StateNotice icon="alert-circle" title="Monitoring unavailable" body={error} tone="error" />}</View>}

    <Card style={styles.monitorCard}>
      <View style={styles.monitorHeading}>
        <View style={styles.monitorIcon}><Feather name="activity" size={19} color={monitoring ? colors.green : colors.orangeDark} /></View>
        <View style={styles.monitorCopy}>
          <Text style={styles.monitorTitle}>Sound monitoring</Text>
          <View style={styles.statusLine}><View style={[styles.statusDot, { backgroundColor: monitoring ? colors.green : colors.muted }]} /><Text style={styles.statusText}>{monitoring ? (demoMode ? 'Running in demo' : 'Monitoring') : 'Stopped'}</Text></View>
        </View>
        <Pill label={monitoring ? 'ON' : 'OFF'} tone={monitoring ? 'connected' : 'neutral'} />
      </View>
      <Pressable accessibilityRole="button" onPress={monitoring ? stopMonitoring : startMonitoring} style={[styles.monitorButton, monitoring && styles.stopButton]}>
        <Feather name={monitoring ? 'square' : 'play'} size={16} color={colors.surface} />
        <Text style={styles.monitorButtonText}>{monitoring ? 'Stop monitoring' : 'Start monitoring'}</Text>
      </Pressable>
      <Text style={styles.controlHint}>{demoMode ? 'Sample monitoring only. No live audio is used.' : 'Enable demo mode in Settings to preview sample events.'}</Text>
    </Card>

    <View style={styles.spacer}>
      <SectionTitle title="System status" />
      <View style={styles.metricsRow}>
        <Metric label="Connection" value={connectionStatus[0].toUpperCase() + connectionStatus.slice(1)} helper="Glove not connected" icon="link-2" tone={colors.muted} />
        <Metric label="Attention" value={attentionLabel} helper={demoMode && monitoring ? 'Demo event active' : 'No active event'} icon="eye" tone={attentionLabel === 'Busy' ? colors.orangeDark : colors.muted} />
      </View>
    </View>

    <View style={styles.spacer}>
      <SectionTitle title="Latest sound" action={demoMode ? 'Demo data' : undefined} />
      <Card style={styles.latestCard}>
        {latestEvent ? <>
          <View style={styles.latestTop}><IconBox name="bell" size={42} /><View style={styles.latestName}><Text style={styles.eventName}>{latestEvent.kind}</Text><Text style={styles.eventDetail}>{latestEvent.detail}</Text></View><Pill label={latestEvent.urgency} tone={latestEvent.critical ? 'critical' : 'high'} /></View>
          <View style={styles.divider} />
          <View style={styles.eventGrid}>
            <Metric label="Confidence" value={`${latestEvent.confidence}%`} helper="Sample score" icon="check-circle" />
            <Metric label="Direction" value={latestEvent.direction || 'Unavailable'} helper="Single mic cannot infer direction" icon="compass" />
          </View>
          <View style={styles.decision}><Feather name="zap" size={15} color={colors.orangeDark} /><Text style={styles.decisionText}>Alert decision: {latestEvent.decision}</Text></View>
        </> : <View style={styles.emptyLatest}>
          <View style={styles.emptyIcon}><Feather name="volume-x" size={20} color={colors.muted} /></View>
          <Text style={styles.emptyTitle}>No sound detected yet</Text>
          <Text style={styles.emptyBody}>Your latest event, confidence, urgency, direction, and alert decision will appear here when detection is configured.</Text>
        </View>}
      </Card>
    </View>

    <View style={styles.spacer}>
      <SectionTitle title="Test an audio file" />
      <Card style={styles.fileCard}>
        <Text style={styles.fileIntro}>Run a one-off file check through the configured inference adapter. The app does not record audio.</Text>
        <Pressable accessibilityRole="button" accessibilityState={{ disabled: isAnalyzingFile }} disabled={isAnalyzingFile} onPress={pickAndAnalyzeFile} style={[styles.fileButton, isAnalyzingFile && styles.fileButtonDisabled]}>
          {isAnalyzingFile ? <ActivityIndicator size="small" color={colors.surface} /> : <Feather name="upload" size={16} color={colors.surface} />}
          <Text style={styles.fileButtonText}>{isAnalyzingFile ? 'Analyzing file…' : 'Choose audio file'}</Text>
        </Pressable>
        {!!audioFileError && <View style={styles.fileState}><StateNotice icon="alert-circle" title="Audio file not analyzed" body={audioFileError} tone="error" /></View>}
        {audioResult && <View style={styles.fileResult}>
          <View style={styles.fileResultTop}><Text style={styles.fileResultTitle}>{soundNames[audioResult.label] || 'Unknown sound'}</Text><Pill label={audioResult.modelStatus.status === 'ready' ? 'MODEL READY' : audioResult.modelStatus.status.toUpperCase()} tone={audioResult.modelStatus.status === 'ready' ? 'connected' : 'neutral'} /></View>
          <Text style={styles.fileResultDetail}>Score: {audioResult.score === null ? 'Unavailable' : `${Math.round(audioResult.score * 100)}%`} · {new Date(audioResult.timestamp).toLocaleString()}</Text>
          {audioResult.reason !== 'classified' && <Text style={styles.fileResultDetail}>{audioResult.reason === 'inference_unavailable' ? 'No inference model is configured. No audio was classified.' : audioResult.reason === 'low_confidence' ? `Low confidence; kept as unknown (${soundNames[audioResult.candidateLabel] || audioResult.candidateLabel}).` : audioResult.reason === 'unsupported_sound' ? `Unsupported sound${audioResult.candidateLabel ? `: ${audioResult.candidateLabel}` : ''}.` : `Analysis status: ${audioResult.reason.replaceAll('_', ' ')}.`}</Text>}
          {audioDecision && <View style={styles.reasoningSummary}>
            <Text style={styles.reasoningTitle}>Reasoning · provisional policy</Text>
            <Text style={styles.fileResultDetail}>Decision: {audioDecision.decision} · Priority: {audioDecision.priority}</Text>
            <Text style={styles.fileResultDetail}>{audioDecision.reason.explanation}</Text>
            <Text style={styles.fileResultDetail}>Haptic recommendation only: {audioDecision.hapticMessage.message}</Text>
          </View>}
        </View>}
      </Card>
    </View>

    <View style={styles.spacer}>
      <SectionTitle title="Safety alert" />
      <View style={[styles.safetyCard, latestEvent?.critical && demoMode ? styles.safetyCritical : null]}>
        <View style={[styles.safetyIcon, latestEvent?.critical && demoMode ? styles.safetyIconCritical : null]}><Feather name={latestEvent?.critical && demoMode ? 'alert-triangle' : 'shield'} size={20} color={latestEvent?.critical && demoMode ? colors.red : colors.green} /></View>
        <View style={styles.safetyCopy}>
          <Text style={[styles.safetyTitle, latestEvent?.critical && demoMode ? { color: colors.red } : null]}>{latestEvent?.critical && demoMode ? 'Critical demo alert' : 'No active safety alert'}</Text>
          <Text style={styles.safetyBody}>{latestEvent?.critical && demoMode ? 'Sample smoke alarm · immediate alert · no direction inferred' : 'Critical events will appear here. Nothing is being detected while live services are unavailable.'}</Text>
        </View>
      </View>
    </View>

    <View style={styles.spacer}>
      <SectionTitle title="Recent alerts" action="View history" onAction={() => navigate('alerts')} />
      <Card style={styles.recentCard}>
        {alerts.length ? alerts.slice(0, 2).map((event, index) => <React.Fragment key={event.id}><RecentAlertRow event={event} />{index === 0 && alerts.length > 1 && <View style={styles.divider} />}</React.Fragment>) : <View style={styles.noRecent}><Feather name="bell-off" size={16} color={colors.muted} /><Text style={styles.noRecentText}>No recent alerts. Events will appear here once detection is configured.</Text></View>}
      </Card>
    </View>

    <View style={styles.spacer}>
      <SectionTitle title="Quick access" />
      <Card style={styles.quickCard}>
        <QuickLink icon="bell" label="Alert History" detail={demoMode ? 'Review sample events' : 'No alerts recorded'} onPress={() => navigate('alerts')} />
        <View style={styles.divider} />
        <QuickLink icon="radio" label="Haptic Guide" detail="Learn the alert patterns" onPress={() => navigate('guide')} />
        <View style={styles.divider} />
        <QuickLink icon="settings" label="Settings" detail={demoMode ? 'Demo mode is on' : 'Configure app preferences'} onPress={() => navigate('settings')} />
      </Card>
    </View>
    <Text style={styles.footerNote}>Designed for visual awareness. Do not rely on this prototype for emergency alerts.</Text>
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream }, content: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 28, maxWidth: 620, width: '100%', alignSelf: 'center' },
  brandMark: { backgroundColor: colors.surfaceWarm, width: 44, height: 44, borderRadius: 15, alignItems: 'center', justifyContent: 'center', marginTop: 5 },
  spacer: { marginTop: spacing.lg }, monitorCard: { marginTop: spacing.lg, padding: 18 }, monitorHeading: { flexDirection: 'row', alignItems: 'center', gap: 12 }, monitorIcon: { width: 40, height: 40, borderRadius: 14, backgroundColor: colors.surfaceWarm, alignItems: 'center', justifyContent: 'center' }, monitorCopy: { flex: 1 }, monitorTitle: { color: colors.navy, fontSize: 15, fontWeight: '800' },
  statusLine: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 }, statusDot: { width: 7, height: 7, borderRadius: 4 }, statusText: { color: colors.muted, fontSize: 12, fontWeight: '600' },
  monitorButton: { marginTop: 16, backgroundColor: colors.orange, minHeight: 48, borderRadius: 15, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 8 }, stopButton: { backgroundColor: colors.navy }, monitorButtonText: { color: colors.surface, fontSize: 14, fontWeight: '800' }, controlHint: { color: colors.muted, textAlign: 'center', marginTop: 9, fontSize: 11, lineHeight: 16 },
  metricsRow: { flexDirection: 'row', gap: 10 }, metric: { flex: 1, minWidth: 0 }, metricTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 5 }, metricLabel: { color: colors.muted, fontSize: 11, fontWeight: '700' }, metricValue: { color: colors.navy, fontWeight: '800', fontSize: 16, marginTop: 8 }, metricHelper: { color: colors.muted, fontSize: 11, marginTop: 3, lineHeight: 15 },
  latestCard: { padding: 16 }, latestTop: { flexDirection: 'row', alignItems: 'center', gap: 11 }, latestName: { flex: 1 }, eventName: { fontSize: 16, color: colors.navy, fontWeight: '800' }, eventDetail: { color: colors.muted, fontSize: 12, marginTop: 3 }, divider: { height: 1, backgroundColor: colors.line, marginVertical: 13 }, eventGrid: { flexDirection: 'row', gap: 18 }, decision: { flexDirection: 'row', alignItems: 'center', gap: 7, backgroundColor: colors.surfaceWarm, padding: 10, borderRadius: 12, marginTop: 13 }, decisionText: { color: colors.orangeDark, fontSize: 12, fontWeight: '700', flexShrink: 1 },
  fileCard: { padding: 16 }, fileIntro: { color: colors.muted, fontSize: 12, lineHeight: 18 }, fileButton: { marginTop: 12, minHeight: 45, borderRadius: 14, backgroundColor: colors.navy, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }, fileButtonDisabled: { opacity: 0.7 }, fileButtonText: { color: colors.surface, fontSize: 13, fontWeight: '800' }, fileState: { marginTop: 12 }, fileResult: { marginTop: 12, backgroundColor: colors.surfaceWarm, borderRadius: 14, padding: 12, gap: 6 }, fileResultTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }, fileResultTitle: { flex: 1, color: colors.navy, fontWeight: '800', fontSize: 14 }, fileResultDetail: { color: colors.muted, fontSize: 11, lineHeight: 16 }, reasoningSummary: { borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 9, marginTop: 3, gap: 5 }, reasoningTitle: { color: colors.orangeDark, fontWeight: '800', fontSize: 11 },
  emptyLatest: { paddingVertical: 12, alignItems: 'center' }, emptyIcon: { width: 40, height: 40, borderRadius: 14, backgroundColor: colors.blueSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 9 }, emptyTitle: { color: colors.navy, fontSize: 14, fontWeight: '800' }, emptyBody: { maxWidth: 290, textAlign: 'center', color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 5 },
  safetyCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, borderRadius: 18, padding: 15, backgroundColor: colors.greenSoft, borderWidth: 1, borderColor: '#CFE7D8' }, safetyCritical: { backgroundColor: colors.redSoft, borderColor: '#F0C9C0' }, safetyIcon: { width: 38, height: 38, borderRadius: 13, backgroundColor: '#D8EDDF', alignItems: 'center', justifyContent: 'center' }, safetyIconCritical: { backgroundColor: '#F9D9D2' }, safetyCopy: { flex: 1 }, safetyTitle: { color: colors.green, fontSize: 14, fontWeight: '800' }, safetyBody: { color: colors.navy, fontSize: 12, lineHeight: 18, marginTop: 4 },
  recentCard: { paddingHorizontal: 14, paddingVertical: 4 }, recentRow: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 58 }, recentIcon: { width: 34, height: 34, borderRadius: 12, backgroundColor: colors.surfaceWarm, alignItems: 'center', justifyContent: 'center' }, recentIconCritical: { backgroundColor: colors.redSoft }, recentCopy: { flex: 1 }, recentName: { color: colors.navy, fontWeight: '800', fontSize: 13 }, recentMeta: { color: colors.muted, fontSize: 11, marginTop: 3 }, noRecent: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingVertical: 14 }, noRecentText: { flex: 1, color: colors.muted, fontSize: 12, lineHeight: 17 },
  quickCard: { paddingVertical: 2, paddingHorizontal: 14 }, quickLink: { flexDirection: 'row', alignItems: 'center', gap: 11, minHeight: 66 }, quickCopy: { flex: 1 }, quickLabel: { color: colors.navy, fontWeight: '800', fontSize: 13 }, quickDetail: { color: colors.muted, fontSize: 11, marginTop: 3 }, footerNote: { color: colors.muted, fontSize: 10, textAlign: 'center', lineHeight: 15, marginTop: 21, paddingHorizontal: 18 },
});

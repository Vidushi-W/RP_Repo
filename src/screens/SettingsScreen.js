import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as DocumentPicker from 'expo-document-picker';
import * as Haptics from 'expo-haptics';
import { Directory, File, Paths } from 'expo-file-system';
import { Card, PageHeader, StateNotice } from '../components/UI';
import { useAppState } from '../state/AppContext';
import { colors } from '../theme';
import { createSettingsStore, DEFAULT_CATEGORIES, DEFAULT_PREFERENCES } from '../settings/settingsStore.mjs';

const settingsStore = createSettingsStore(AsyncStorage);
const intensityLevels = ['low', 'normal', 'high', 'critical'];
const intensityLabels = { low: 'Low', normal: 'Normal', high: 'High', critical: 'Critical' };

function Section({ title, subtitle, children }) {
  return <View style={styles.section}><View style={styles.sectionHeading}><Text accessibilityRole="header" style={styles.sectionTitle}>{title}</Text>{!!subtitle && <Text style={styles.sectionSubtitle}>{subtitle}</Text>}</View>{children}</View>;
}

function SettingRow({ icon, title, detail, trailing, last = false }) {
  return <View style={[styles.settingRow, !last && styles.dividerRow]}><View style={styles.icon}><Feather name={icon} size={17} color={colors.orangeDark} /></View><View style={styles.copy}><Text style={styles.settingTitle}>{title}</Text><Text style={styles.settingDetail}>{detail}</Text></View>{trailing}</View>;
}

function ActionButton({ icon, label, onPress, tone = 'default', disabled = false }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={[styles.actionButton, tone === 'danger' && styles.dangerButton, disabled && styles.disabledButton]}><Feather name={icon} size={15} color={tone === 'danger' ? colors.red : colors.orangeDark} /><Text style={[styles.actionText, tone === 'danger' && styles.dangerText]}>{label}</Text></Pressable>;
}

function Segmented({ label, options, value, onChange }) {
  return <View style={styles.segmentBlock}><Text style={styles.settingTitle}>{label}</Text><View style={styles.segments}>{options.map(option => <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected: value === option.value }} onPress={() => onChange(option.value)} style={[styles.segment, value === option.value && styles.segmentActive]}><Text style={[styles.segmentText, value === option.value && styles.segmentTextActive]}>{option.label}</Text></Pressable>)}</View></View>;
}

export function SettingsScreen() {
  const {
    demoMode, setDemoMode, monitoring, startMonitoring, stopMonitoring, attentionStatus, attentionTestState, setAttentionTestState,
    preferences: sharedPreferences, updatePreferences, clearDemoData, clearAlertHistory,
  } = useAppState();
  const [settings, setSettings] = useState(null);
  const [categoryDraft, setCategoryDraft] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(DEFAULT_CATEGORIES[0]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [activePreviewPulse, setActivePreviewPulse] = useState(-1);

  useEffect(() => {
    let active = true;
    settingsStore.load().then(value => { if (active) { setSettings(value); setSelectedCategory(value.categories[0]); } }).catch(() => { if (active) setError('Could not load saved settings.'); });
    return () => { active = false; };
  }, []);

  const categories = settings?.categories || [...DEFAULT_CATEGORIES];
  const samples = settings?.samples || [];
  const preferences = settings?.preferences || sharedPreferences;
  const updateLocal = async fn => {
    setError(''); setStatus('');
    try { const value = await fn(); setSettings(value); return value; }
    catch (exception) { const message = exception?.message || 'Could not save this change.'; setError(message); return null; }
  };
  const setPreference = async changes => {
    const saved = await updateLocal(() => settingsStore.updatePreferences(changes));
    if (saved) { try { await updatePreferences(changes); setStatus('Preference saved on this device.'); } catch { setError('Preference could not be saved.'); } }
  };
  const switchMonitoring = value => {
    if (value) { startMonitoring(); setStatus(demoMode ? 'Demo monitoring enabled. This does not use the microphone.' : 'Monitoring could not start. Microphone permission and sound recognition are unavailable.'); }
    else { stopMonitoring(); setStatus('Monitoring is off.'); }
  };
  const switchDemoMode = async value => {
    await setDemoMode(value);
    setStatus(value ? 'Demo mode enabled with labelled sample events only.' : 'Demo mode turned off.');
  };
  const addCategory = async () => {
    const added = await updateLocal(() => settingsStore.addCategory(categoryDraft));
    if (added) { setCategoryDraft(''); setSelectedCategory(added.categories.at(-1)); setStatus(`Category ${added.categories.at(-1)} added. It does not change the recognition model.`); }
  };
  const importSample = async () => {
    setBusy(true); setError(''); setStatus('');
    let destination;
    try {
      if (!settings?.preferences.retainAudioSamples) throw new Error('Audio retention is off. Review and enable the local audio retention consent before importing a clip.');
      const result = await DocumentPicker.getDocumentAsync({ type: 'audio/*', multiple: false, copyToCacheDirectory: true });
      if (result.canceled) { setStatus('Clip import cancelled.'); return; }
      const asset = result.assets?.[0];
      if (!asset) throw new Error('The selected audio file could not be read.');
      const folder = new Directory(Paths.document, 'signlanka-audio-samples');
      folder.create({ idempotent: true, intermediates: true });
      const safeFilename = (asset.name || 'sample.wav').replace(/[^a-zA-Z0-9._-]/g, '_');
      destination = new File(folder, `${Date.now()}_${Math.random().toString(36).slice(2, 7)}_${safeFilename}`);
      await new File(asset.uri).copy(destination);
      const next = await settingsStore.addSample({ filename: asset.name || 'sample.wav', category: selectedCategory, uri: destination.uri });
      setSettings(next);
      setStatus(`Sample labelled ${selectedCategory} and stored locally. The app does not use samples to train or adapt a model.`);
    } catch (exception) {
      try { if (destination?.exists) destination.delete(); } catch { /* best-effort cleanup of incomplete import */ }
      setError(exception?.message || 'Could not import this audio sample.');
    } finally { setBusy(false); }
  };
  const removeSample = sample => {
    Alert.alert('Remove sample?', `${sample.filename} and its saved audio copy will be deleted from this app.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => {
        try { if (sample.uri.startsWith(new Directory(Paths.document, 'signlanka-audio-samples').uri)) new File(sample.uri).delete(); const next = await settingsStore.removeSample(sample.id); setSettings(next); setStatus('Sample and saved audio removed.'); }
        catch { setError('Could not remove this sample.'); }
      } },
    ]);
  };
  const requestRetention = value => {
    if (value) {
      Alert.alert('Before retaining audio', 'Selected clips will be copied into this app’s local documents folder. Audio remains on this device and is not sent or used to retrain a model. Local app storage is not encrypted by this preference. You can delete clips or turn retention off at any time.', [
        { text: 'Cancel', style: 'cancel', onPress: () => setStatus('Audio retention remains off.') },
        { text: 'I understand · enable', onPress: async () => { await setPreference({ retainAudioSamples: true }); setStatus('Audio retention enabled after confirmation.'); } },
      ]);
      return;
    }
    Alert.alert('Turn off audio retention?', 'This deletes all imported clip copies and their sample labels from this app.', [
      { text: 'Cancel', style: 'cancel', onPress: () => setStatus('Audio retention remains enabled.') },
      { text: 'Delete clips and turn off', style: 'destructive', onPress: purgeAudioAndDisable },
    ]);
  };
  const purgeAudioAndDisable = async () => {
    try {
      const folder = new Directory(Paths.document, 'signlanka-audio-samples');
      if (folder.exists) folder.delete();
      const next = await settingsStore.clearSamples();
      const updated = await settingsStore.updatePreferences({ retainAudioSamples: false });
      setSettings({ ...next, preferences: updated.preferences });
      await updatePreferences({ retainAudioSamples: false });
      setStatus('Imported audio and sample labels deleted; retention is off.');
    } catch { setError('Could not clear all imported clips. Audio retention was not changed.'); }
  };
  const removeAllAlertHistory = () => Alert.alert('Delete local alert history?', 'This removes saved event metadata and feedback from this device. It does not affect fixed safety priority.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Delete history', style: 'destructive', onPress: async () => { const saved = await clearAlertHistory(); if (saved) setStatus('Local alert history deleted.'); else setError('Could not delete local alert history.'); } },
  ]);
  const resetDemo = () => Alert.alert('Reset demo data?', 'This removes sample demo alerts and turns demo monitoring off.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Reset demo data', style: 'destructive', onPress: async () => { const saved = await clearDemoData(); if (saved) setStatus('Demo alerts cleared and demo mode turned off.'); else setError('Could not reset demo data.'); } },
  ]);
  const restoreDefaults = () => Alert.alert('Restore defaults?', 'This clears custom categories, imported sample labels and audio, and restores app preferences.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Restore defaults', style: 'destructive', onPress: async () => {
      try {
        const folder = new Directory(Paths.document, 'signlanka-audio-samples'); if (folder.exists) folder.delete();
        const next = await settingsStore.resetPreferences(); setSettings(next);
        await updatePreferences(DEFAULT_PREFERENCES); setAttentionTestState(null); setDemoMode(false); stopMonitoring();
        setSelectedCategory(DEFAULT_CATEGORIES[0]); setStatus('Settings and personalization restored to defaults.');
      } catch { setError('Could not restore every default. Please try again.'); }
    } },
  ]);
  const previewPhone = async () => {
    setBusy(true); setStatus('Previewing a two-pulse pattern.');
    let vibrationFailed = false;
    try {
      const style = preferences.hapticIntensity === 'low' ? Haptics.ImpactFeedbackStyle.Soft : preferences.hapticIntensity === 'normal' ? Haptics.ImpactFeedbackStyle.Light : preferences.hapticIntensity === 'high' ? Haptics.ImpactFeedbackStyle.Medium : Haptics.ImpactFeedbackStyle.Heavy;
      for (let pulse = 0; pulse < 2; pulse += 1) {
        setActivePreviewPulse(pulse);
        if (preferences.phoneVibrationEnabled) {
          try { await Haptics.impactAsync(style); }
          catch { vibrationFailed = true; setError('Phone vibration is unavailable or blocked by device settings. The visual pattern preview can still be used.'); }
        }
        await new Promise(resolve => setTimeout(resolve, 220));
      }
      if (!vibrationFailed) setStatus(`Pattern preview finished${preferences.phoneVibrationEnabled ? ' with optional phone vibration' : ' visually only'}. It does not test glove motors or directional cues.`);
    } catch { setError('Could not preview this haptic pattern.'); }
    finally { setActivePreviewPulse(-1); setBusy(false); }
  };

  if (!settings) return <View style={styles.loading}><ActivityIndicator color={colors.orangeDark} /><Text style={styles.body}>Loading settings…</Text></View>;

  return <ScrollView style={styles.screen} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
    <PageHeader eyebrow="Preferences" title="Settings" subtitle="Control previews, privacy, and personalization. Live microphone recognition and glove connection are not configured." />
    {demoMode && <StateNotice icon="play-circle" title="Demo mode is active" body="Home and Alert History contain labelled examples only. These are not live detections." tone="success" />}
    <Section title="Monitoring and attention" subtitle="Live microphone access is not available in this build.">
      <Card style={styles.card}>
        <SettingRow icon={monitoring ? 'activity' : 'mic-off'} title="Monitoring" detail={monitoring ? (demoMode ? 'On · demo events only; microphone is not used' : 'Unexpected active state') : 'Off · live detection is unavailable'} trailing={<Switch accessibilityLabel="Enable monitoring or demo monitoring" value={monitoring} onValueChange={switchMonitoring} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={monitoring ? colors.orangeDark : '#F7F4EF'} />} />
        <SettingRow icon="play-circle" title="Demo mode" detail="Show clearly labelled examples; no microphone is used" trailing={<Switch accessibilityLabel="Enable labelled demo mode" value={demoMode} onValueChange={switchDemoMode} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={demoMode ? colors.orangeDark : '#F7F4EF'} />} />
        <SettingRow icon="mic" title="Microphone permission" detail="Not requested · microphone permission flow is not implemented" trailing={<Text style={styles.statusOff}>NOT REQUESTED</Text>} />
        <SettingRow icon="radio" title="Attention channel" detail={`Current state: ${attentionStatus === 'busy' ? 'Busy' : 'Idle'}${attentionTestState ? ' · test state' : ''}`} trailing={<View style={[styles.stateBadge, attentionStatus === 'busy' && styles.busyBadge]}><Text style={[styles.stateBadgeText, attentionStatus === 'busy' && styles.busyText]}>{attentionStatus.toUpperCase()}</Text></View>} />
        <View style={styles.inlineActions}><ActionButton icon="play" label={attentionTestState === 'busy' ? 'Test Idle' : 'Test Busy'} onPress={() => { const next = attentionTestState === 'busy' ? 'idle' : 'busy'; setAttentionTestState(next); setStatus(`Attention test set to ${next === 'busy' ? 'Busy' : 'Idle'}. This is a test state only.`); }} />{attentionTestState && <ActionButton icon="x" label="Clear attention test" onPress={() => { setAttentionTestState(null); setStatus('Attention test cleared.'); }} />}<Text style={styles.smallNote}>Test control · does not change sound detection.</Text></View>
      </Card>
    </Section>

    <Section title="Haptics and notifications" subtitle="Saved preferences configure previews only; no external alert delivery is active.">
      <Card style={styles.card}>
        <Segmented label="Haptic intensity" value={preferences.hapticIntensity} options={intensityLevels.map(value => ({ value, label: intensityLabels[value] }))} onChange={value => setPreference({ hapticIntensity: value })} />
        <ActionButton icon="play-circle" label={busy ? 'Please wait…' : 'Preview pattern'} onPress={previewPhone} disabled={busy} />
        <View accessibilityLabel={`Two-pulse preview. First pulse ${activePreviewPulse === 0 ? 'active' : 'inactive'}, second pulse ${activePreviewPulse === 1 ? 'active' : 'inactive'}`} accessibilityLiveRegion="polite" style={styles.previewTimeline}><View style={[styles.previewPulse, activePreviewPulse === 0 && styles.previewPulseActive]} /><View style={styles.previewGap} /><View style={[styles.previewPulse, activePreviewPulse === 1 && styles.previewPulseActive]} /><Text style={styles.previewHint}>Preview only · no glove actuation</Text></View>
        <SettingRow icon="bell" title="Notifications preference" detail="Saved locally · notification delivery is not configured" trailing={<Switch accessibilityLabel="Enable notification preference" value={preferences.notificationsEnabled} onValueChange={value => setPreference({ notificationsEnabled: value })} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={preferences.notificationsEnabled ? colors.orangeDark : '#F7F4EF'} />} />
        <SettingRow icon="smartphone" title="Phone vibration preview" detail="Optional · phone vibration cannot represent glove position or proven intensity" trailing={<Switch accessibilityLabel="Enable optional phone vibration preview" value={preferences.phoneVibrationEnabled} onValueChange={value => setPreference({ phoneVibrationEnabled: value })} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={preferences.phoneVibrationEnabled ? colors.orangeDark : '#F7F4EF'} />} last />
      </Card>
      <StateNotice icon="shield" title="Safety priority stays fixed" body="User preferences and personalization cannot suppress confirmed fire-alarm alerts or reduce their fixed critical priority." />
    </Section>

    <Section title="Sound personalization" subtitle="Add labels and clips for future evaluation. Samples do not retrain or adapt a model.">
      <Card style={styles.card}>
        <View style={styles.addCategoryRow}><TextInput accessibilityLabel="New sound category" value={categoryDraft} onChangeText={setCategoryDraft} placeholder="Add a sound category" placeholderTextColor={colors.muted} maxLength={40} style={styles.input} returnKeyType="done" onSubmitEditing={addCategory} /><Pressable accessibilityRole="button" accessibilityLabel="Add sound category" onPress={addCategory} style={styles.addButton}><Feather name="plus" size={17} color="#FFFFFF" /></Pressable></View>
        <View style={styles.categoryChips}>{categories.map(category => <Pressable key={category} accessibilityRole="button" accessibilityState={{ selected: selectedCategory === category }} onPress={() => setSelectedCategory(category)} style={[styles.categoryChip, selectedCategory === category && styles.categoryChipSelected]}><Text style={[styles.categoryChipText, selectedCategory === category && styles.categoryChipTextSelected]}>{category}</Text></Pressable>)}</View>
        <View style={styles.sampleSummary}><Feather name="music" size={17} color={colors.orangeDark} /><View style={styles.copy}><Text style={styles.settingTitle}>Labelled sample clips · {samples.length}</Text><Text style={styles.settingDetail}>{samples.length ? `${samples.length} stored on this device · not used for recognition` : 'No sample clips imported'}</Text></View></View>
        <ActionButton icon="upload" label={busy ? 'Importing…' : `Import clip for ${selectedCategory}`} onPress={importSample} disabled={busy || !preferences.retainAudioSamples} />
        {!preferences.retainAudioSamples && <Text style={styles.smallNote}>Turn on audio retention below and confirm consent before importing audio clips.</Text>}
        {samples.length > 0 && <View style={styles.sampleList}>{samples.map(sample => <View key={sample.id} style={styles.sampleRow}><View style={styles.copy}><Text style={styles.settingTitle}>{sample.filename}</Text><Text style={styles.settingDetail}>{sample.category} · Stored locally · not used for training</Text></View><Pressable accessibilityRole="button" accessibilityLabel={`Remove ${sample.filename}`} onPress={() => removeSample(sample)} hitSlop={8}><Feather name="trash-2" size={17} color={colors.red} /></Pressable></View>)}</View>}
      </Card>
      <StateNotice icon="info" title="No few-shot recognition" body="The current inference adapter does not consume these sample clips. Collection does not train a model, enable few-shot recognition, or change alert decisions." />
    </Section>

    <Section title="Privacy and local data" subtitle="Raw audio is not recorded by monitoring. Imported clips are separate and require explicit consent.">
      <Card style={styles.card}>
        <SettingRow icon="database" title="Alert history and preferences" detail="Structured metadata is saved locally on this device. Local preferences storage is not encrypted." trailing={<Text style={styles.statusOff}>LOCAL</Text>} />
        <SettingRow icon="hard-drive" title="Retain imported audio samples" detail={preferences.retainAudioSamples ? 'On · imported clips saved in app documents' : 'Off · no imported clip audio is retained'} trailing={<Switch accessibilityLabel="Retain imported audio sample clips on this device" value={preferences.retainAudioSamples} onValueChange={requestRetention} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={preferences.retainAudioSamples ? colors.orangeDark : '#F7F4EF'} />} last />
        <ActionButton icon="trash-2" label="Delete local alert history" onPress={removeAllAlertHistory} tone="danger" />
      </Card>
    </Section>

    <Section title="Glove and BLE" subtitle="No glove is paired or connected in this build.">
      <Card style={styles.card}>
        <SettingRow icon="watch" title="Glove connection" detail="Disconnected · BLE discovery and command transport are not configured" trailing={<Text style={styles.statusOff}>OFFLINE</Text>} last />
      </Card>
      <StateNotice icon="tool" title="Troubleshooting" body="Check that the glove is powered and charged, then confirm its BLE service and actuator positions with the hardware integration. This app cannot scan for, pair, or verify glove motors yet." />
    </Section>

    <Section title="Reset" subtitle="These actions have separate effects and ask before deleting data.">
      <Card style={styles.card}>
        <ActionButton icon="refresh-cw" label="Reset demo data" onPress={resetDemo} />
        <ActionButton icon="rotate-ccw" label="Restore defaults and clear samples" onPress={restoreDefaults} tone="danger" />
      </Card>
    </Section>
    {!!error && <StateNotice icon="alert-circle" title="Action not completed" body={error} tone="error" />}
    {!!status && <View accessibilityLiveRegion="polite" accessibilityRole="status" style={styles.statusNotice}><Feather name="check-circle" size={15} color={colors.green} /><Text style={styles.statusNoticeText}>{status}</Text></View>}
    <Text style={styles.footer}>Personalization feedback and clips are evaluation material only. No model training or safety policy adaptation runs in this app.</Text>
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream }, content: { padding: 20, paddingTop: 24, paddingBottom: 34, maxWidth: 620, width: '100%', alignSelf: 'center', gap: 18 }, loading: { flex: 1, backgroundColor: colors.cream, alignItems: 'center', justifyContent: 'center', gap: 9 },
  section: { gap: 9 }, sectionHeading: { marginBottom: 1 }, sectionTitle: { color: colors.navy, fontSize: 17, fontWeight: '900' }, sectionSubtitle: { color: colors.muted, fontSize: 11, lineHeight: 16, marginTop: 3 }, card: { paddingHorizontal: 14, paddingVertical: 4, gap: 8 }, settingRow: { minHeight: 66, flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8 }, dividerRow: { borderBottomWidth: 1, borderBottomColor: colors.line }, icon: { width: 35, height: 35, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surfaceWarm }, copy: { flex: 1 }, settingTitle: { fontSize: 12, fontWeight: '800', color: colors.navy }, settingDetail: { fontSize: 10, color: colors.muted, lineHeight: 15, marginTop: 3 }, statusOff: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 0.45, textAlign: 'right' }, stateBadge: { borderRadius: 99, paddingVertical: 6, paddingHorizontal: 9, backgroundColor: colors.greenSoft }, busyBadge: { backgroundColor: '#FFF0DE' }, stateBadgeText: { color: colors.green, fontSize: 9, fontWeight: '900' }, busyText: { color: colors.orangeDark },
  inlineActions: { paddingBottom: 9, gap: 5 }, smallNote: { color: colors.muted, fontSize: 10, lineHeight: 15, paddingHorizontal: 3 }, actionButton: { minHeight: 42, alignSelf: 'stretch', flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: colors.surfaceWarm, borderWidth: 1, borderColor: '#F1D6B6', marginTop: 6, paddingHorizontal: 10 }, actionText: { color: colors.orangeDark, fontSize: 11, fontWeight: '800' }, dangerButton: { backgroundColor: '#FFF5F3', borderColor: '#E8C1BA' }, dangerText: { color: colors.red }, disabledButton: { opacity: 0.55 },
  segmentBlock: { paddingVertical: 10, gap: 8 }, segments: { flexDirection: 'row', gap: 6 }, segment: { flex: 1, minHeight: 36, alignItems: 'center', justifyContent: 'center', borderRadius: 10, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.cream }, segmentActive: { backgroundColor: colors.orange, borderColor: colors.orangeDark }, segmentText: { color: colors.muted, fontSize: 10, fontWeight: '700' }, segmentTextActive: { color: '#FFFFFF' },
  previewTimeline: { minHeight: 35, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }, previewPulse: { width: 26, height: 12, borderRadius: 5, backgroundColor: '#E6B98D', opacity: 0.55 }, previewPulseActive: { backgroundColor: colors.orangeDark, height: 18, opacity: 1 }, previewGap: { width: 21, height: 2, backgroundColor: '#CFC6B9' }, previewHint: { color: colors.muted, fontSize: 9, marginLeft: 7 },
  addCategoryRow: { flexDirection: 'row', gap: 8, alignItems: 'center', marginTop: 7 }, input: { flex: 1, minHeight: 43, borderWidth: 1, borderColor: colors.line, borderRadius: 12, paddingHorizontal: 12, color: colors.navy, backgroundColor: colors.cream, fontSize: 12 }, addButton: { width: 43, height: 43, borderRadius: 13, backgroundColor: colors.orange, alignItems: 'center', justifyContent: 'center' }, categoryChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 9 }, categoryChip: { borderRadius: 99, paddingVertical: 7, paddingHorizontal: 10, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.cream }, categoryChipSelected: { backgroundColor: colors.orange, borderColor: colors.orangeDark }, categoryChipText: { color: colors.muted, fontSize: 9, fontWeight: '700' }, categoryChipTextSelected: { color: '#FFFFFF' }, sampleSummary: { flexDirection: 'row', gap: 10, alignItems: 'center', marginTop: 15, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.line }, sampleList: { marginTop: 8, borderTopWidth: 1, borderTopColor: colors.line }, sampleRow: { minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: colors.line, paddingVertical: 6 },
  statusNotice: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, padding: 11, backgroundColor: colors.greenSoft, borderRadius: 13 }, statusNoticeText: { color: colors.green, flex: 1, fontSize: 11, lineHeight: 16, fontWeight: '700' }, body: { color: colors.muted, fontSize: 12 }, footer: { color: colors.muted, textAlign: 'center', fontSize: 10, lineHeight: 16, paddingHorizontal: 12, marginTop: 2 },
});

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Card, PageHeader, StateNotice } from '../components/UI';
import { colors } from '../theme';
import { useAppState } from '../state/AppContext';
import { SOUND_LABELS } from '../sound-analysis/analysis.mjs';
import { composeHapticPattern, GLOVE_POSITIONS, HAPTIC_URGENCY, PATTERN_DEFINITIONS } from '../haptics/patterns.mjs';

const soundOrder = [SOUND_LABELS.FIRE_ALARM, SOUND_LABELS.SIREN, SOUND_LABELS.VEHICLE_HORN, SOUND_LABELS.DOORBELL, SOUND_LABELS.HUMAN_CALLING, SOUND_LABELS.UNKNOWN];
const urgencyOrder = [HAPTIC_URGENCY.LOW, HAPTIC_URGENCY.NORMAL, HAPTIC_URGENCY.HIGH, HAPTIC_URGENCY.CRITICAL, HAPTIC_URGENCY.UNKNOWN];
const urgencyLabels = { low: 'Low', normal: 'Normal', high: 'High', critical: 'Critical', unknown: 'Uncertain' };
const positionLabels = { front: 'Front', back: 'Back', left: 'Left', right: 'Right', unknown: 'No direction' };

function Timeline({ pattern, activePulse = -1, compact = false }) {
  const definition = PATTERN_DEFINITIONS[pattern.category];
  const color = pattern.critical ? colors.red : colors.orange;
  const bars = [];
  for (let i = 0; i < pattern.pulseDurationsMs.length; i += 1) {
    const width = Math.max(compact ? 18 : 26, Math.min(compact ? 42 : 74, pattern.pulseDurationsMs[i] / (compact ? 7 : 5)));
    const height = (compact ? 10 : 14) + pattern.intensity.level * (compact ? 2 : 3);
    bars.push(<View key={`pulse-${i}`} style={styles.timelineSegment}>
      <View style={[styles.pulseBar, { width, height, backgroundColor: activePulse === i ? (pattern.critical ? '#7D1E18' : colors.orangeDark) : color, opacity: activePulse === i ? 1 : 0.68 }]} />
      {i < pattern.pulseDurationsMs.length - 1 && <View style={[styles.gapBar, { width: Math.min(compact ? 18 : 28, pattern.gapDurationsMs[i] / 10) }]} />}
    </View>);
  }
  return <View accessibilityLabel={`${definition.rhythmName} rhythm, ${pattern.pulseDurationsMs.length} pulses${pattern.repeatCount > 1 ? `, repeats ${pattern.repeatCount} times` : ''}`} style={styles.timeline}>
    {bars}
    {pattern.repeatCount > 1 && <Text style={[styles.repeatLabel, pattern.critical && styles.criticalText]}>×{pattern.repeatCount}</Text>}
  </View>;
}

function GloveDiagram({ pattern, active }) {
  const activeSet = new Set(active ? pattern.actuatorPositions : []);
  const Node = ({ position, style }) => {
    const selected = activeSet.has(position);
    return <View accessibilityLabel={`${positionLabels[position]} actuator${selected ? ', active' : ''}`} style={[styles.actuatorNode, selected && styles.actuatorNodeActive, pattern.critical && selected && styles.actuatorNodeCritical, style]}>
      <View style={[styles.actuatorDot, selected && styles.actuatorDotActive, pattern.critical && selected && styles.actuatorDotCritical]} />
      <Text style={[styles.actuatorLabel, selected && styles.actuatorLabelActive, pattern.critical && selected && styles.criticalText]}>{positionLabels[position]}</Text>
    </View>;
  };
  return <View accessibilityLabel={`Four position glove diagram. ${pattern.directionMode === 'directional' ? `${positionLabels[pattern.direction]} actuator selected.` : 'Undirected pattern uses all four positions.'}`} style={[styles.diagram, pattern.critical && styles.diagramCritical]}>
    <Node position="front" style={styles.frontNode} />
    <Node position="left" style={styles.leftNode} />
    <View style={[styles.palm, pattern.critical && styles.palmCritical]}><Feather name="hand" size={26} color={pattern.critical ? colors.red : colors.muted} /><Text style={styles.palmLabel}>GLOVE</Text></View>
    <Node position="right" style={styles.rightNode} />
    <Node position="back" style={styles.backNode} />
  </View>;
}

function ChoiceRow({ label, value, options, onChange, disabled = false }) {
  return <View style={styles.choiceGroup}>
    <Text style={styles.choiceLabel}>{label}</Text>
    <View style={styles.choices}>
      {options.map(option => {
        const selected = value === option.value;
        return <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected, disabled }} accessibilityLabel={`${label}: ${option.label}`} disabled={disabled} onPress={() => onChange(option.value)} style={[styles.choice, selected && styles.choiceSelected, disabled && styles.choiceDisabled]}>
          <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>{option.label}</Text>
        </Pressable>;
      })}
    </View>
  </View>;
}

function impactStyleFor(urgency) {
  switch (urgency) {
    case HAPTIC_URGENCY.LOW:
    case HAPTIC_URGENCY.UNKNOWN: return Haptics.ImpactFeedbackStyle.Soft;
    case HAPTIC_URGENCY.NORMAL: return Haptics.ImpactFeedbackStyle.Light;
    case HAPTIC_URGENCY.HIGH: return Haptics.ImpactFeedbackStyle.Medium;
    default: return Haptics.ImpactFeedbackStyle.Heavy;
  }
}

export function GuideScreen() {
  const { preferences, updatePreferences } = useAppState();
  const [soundCategory, setSoundCategory] = useState(SOUND_LABELS.DOORBELL);
  const [urgency, setUrgency] = useState(preferences.hapticIntensity);
  const [direction, setDirection] = useState('unknown');
  const phoneVibration = preferences.phoneVibrationEnabled;
  const [previewing, setPreviewing] = useState(false);
  const [activePulse, setActivePulse] = useState(-1);
  const [previewError, setPreviewError] = useState('');
  const cancelled = useRef(false);
  const pattern = useMemo(() => composeHapticPattern({ soundCategory, urgency, direction }), [soundCategory, urgency, direction]);

  useEffect(() => () => { cancelled.current = true; }, []);
  useEffect(() => { setUrgency(preferences.hapticIntensity); }, [preferences.hapticIntensity]);

  async function runPreview() {
    if (previewing) {
      cancelled.current = true;
      setPreviewing(false);
      setActivePulse(-1);
      return;
    }

    cancelled.current = false;
    setPreviewError('');
    setPreviewing(true);
    const style = impactStyleFor(pattern.urgency);
    try {
      for (let repeat = 0; repeat < pattern.repeatCount; repeat += 1) {
        for (let i = 0; i < pattern.pulseDurationsMs.length; i += 1) {
          if (cancelled.current) return;
          setActivePulse(i);
          if (phoneVibration) {
            try { await Haptics.impactAsync(style); }
            catch { setPreviewError('Phone vibration was unavailable or blocked by device settings. The visual preview can still be used.'); }
          }
          await new Promise(resolve => setTimeout(resolve, pattern.pulseDurationsMs[i] + pattern.gapDurationsMs[i]));
        }
      }
    } finally {
      if (!cancelled.current) {
        setActivePulse(-1);
        setPreviewing(false);
      }
    }
  }

  const soundOptions = soundOrder.map(value => ({ value, label: PATTERN_DEFINITIONS[value].title }));
  const urgencyOptions = urgencyOrder.map(value => ({ value, label: urgencyLabels[value] }));
  const directionOptions = [...GLOVE_POSITIONS.map(value => ({ value, label: positionLabels[value] })), { value: 'unknown', label: 'No direction' }];

  return <ScrollView style={styles.screen} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
    <PageHeader eyebrow="Feel the cue" title="Haptic guide" subtitle="Sound sets the rhythm. Urgency sets intensity. Direction selects a glove position." />
    <View style={styles.simulationStatus}><Feather name="radio" size={15} color={colors.orangeDark} /><Text style={styles.simulationStatusText}>SIMULATION — glove not connected</Text></View>
    <StateNotice icon="info" title="Glove hardware unavailable" body="The guide and simulator show proposed patterns only. No glove motors are connected or actuated." />

    <View style={[styles.simulatorCard, pattern.critical && styles.simulatorCritical]}>
      <View style={styles.simulatorHeader}>
        <View style={styles.simulatorHeadingCopy}>
          <Text style={[styles.simulatorEyebrow, pattern.critical && styles.criticalText]}>PATTERN SIMULATOR</Text>
          <Text accessibilityRole="header" style={[styles.simulatorTitle, pattern.critical && styles.criticalText]}>{pattern.critical ? 'Critical fire alarm' : 'Build a haptic cue'}</Text>
        </View>
        {pattern.critical && <View style={styles.criticalBadge}><Feather name="alert-triangle" size={13} color="#FFFFFF" /><Text style={styles.criticalBadgeText}>CRITICAL</Text></View>}
      </View>

      <ChoiceRow label="Sound event" value={soundCategory} options={soundOptions} onChange={setSoundCategory} />
      <ChoiceRow label="Urgency · intensity" value={pattern.urgency} options={urgencyOptions} onChange={setUrgency} disabled={pattern.critical} />
      {pattern.critical && <Text style={styles.fireRule}>Fire alarms always use critical intensity.</Text>}
      <ChoiceRow label="Direction · actuator" value={direction} options={directionOptions} onChange={setDirection} />

      <GloveDiagram pattern={pattern} active />
      <View style={styles.patternMeta}>
        <View><Text style={styles.metaLabel}>RHYTHM</Text><Text style={[styles.metaValue, pattern.critical && styles.criticalText]}>{pattern.rhythmName}{pattern.repeatCount > 1 ? ` · repeats ${pattern.repeatCount}×` : ''}</Text></View>
        <View><Text style={styles.metaLabel}>INTENSITY</Text><Text style={[styles.metaValue, pattern.critical && styles.criticalText]}>{urgencyLabels[pattern.urgency]} · level {pattern.intensity.level}/4</Text></View>
      </View>
      <Timeline pattern={pattern} activePulse={activePulse} />
      <Text style={styles.patternExplanation}>{pattern.explanation}</Text>
      <Text style={styles.durationLabel}>Preview length · {Math.round(pattern.totalDurationMs / 100) / 10}s</Text>

      <View style={styles.vibrationRow}>
        <View style={styles.vibrationCopy}><Text style={styles.vibrationTitle}>Phone vibration preview</Text><Text style={styles.vibrationDetail}>Optional · phone preview cannot show glove direction or exact actuator intensity.</Text></View>
        <Switch accessibilityLabel="Enable optional phone vibration preview" value={phoneVibration} onValueChange={value => updatePreferences({ phoneVibrationEnabled: value })} trackColor={{ false: '#D8D3CA', true: '#E9A875' }} thumbColor={phoneVibration ? colors.orangeDark : '#F7F4EF'} />
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel={previewing ? 'Stop pattern simulation' : 'Preview haptic pattern'} onPress={runPreview} style={[styles.previewButton, pattern.critical && styles.previewButtonCritical]}>
        {previewing ? <Feather name="square" size={16} color="#FFFFFF" /> : <Feather name="play" size={17} color="#FFFFFF" />}
        <Text style={styles.previewButtonText}>{previewing ? 'Stop preview' : 'Preview pattern'}</Text>
      </Pressable>
      {!!previewError && <Text accessibilityRole="alert" style={styles.previewError}>{previewError}</Text>}
      {previewing && <View accessibilityLiveRegion="polite" style={styles.playingStatus}><ActivityIndicator size="small" color={pattern.critical ? colors.red : colors.orangeDark} /><Text style={styles.playingText}>Playing visual simulation{phoneVibration ? ' with phone vibration' : ''}…</Text></View>}
    </View>

    <Text accessibilityRole="header" style={styles.sectionHeading}>Pattern library</Text>
    <Text style={styles.sectionIntro}>Each sound has its own rhythm. Intensity varies independently with urgency.</Text>
    {soundOrder.map(category => {
      const sampleUrgency = category === SOUND_LABELS.FIRE_ALARM ? HAPTIC_URGENCY.CRITICAL : HAPTIC_URGENCY.NORMAL;
      const samplePattern = composeHapticPattern({ soundCategory: category, urgency: sampleUrgency, direction: 'unknown' });
      const definition = PATTERN_DEFINITIONS[category];
      return <Card key={category} style={[styles.libraryCard, samplePattern.critical && styles.libraryCardCritical]}>
        <View style={styles.libraryHeader}><View style={[styles.libraryIcon, samplePattern.critical && styles.libraryIconCritical]}><Feather name={samplePattern.critical ? 'alert-triangle' : 'activity'} size={17} color={samplePattern.critical ? colors.red : colors.orangeDark} /></View><View style={styles.libraryTitleCopy}><Text style={[styles.libraryTitle, samplePattern.critical && styles.criticalText]}>{definition.title}</Text><Text style={styles.libraryRhythm}>{definition.rhythmName} · {samplePattern.intensity.name} intensity</Text></View>{samplePattern.critical && <Text style={styles.criticalWord}>CRITICAL</Text>}</View>
        <Timeline pattern={samplePattern} compact />
        <Text style={styles.libraryExplanation}>{definition.explanation}</Text>
      </Card>;
    })}
    <Text style={styles.disclaimer}>Patterns are proposed interaction cues. Tune and test them with Deaf and hard-of-hearing users and the target glove hardware before relying on them.</Text>
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream }, content: { padding: 20, paddingTop: 24, paddingBottom: 30, maxWidth: 620, width: '100%', alignSelf: 'center' },
  simulationStatus: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'flex-start', backgroundColor: colors.surfaceWarm, borderColor: '#F1D6B6', borderWidth: 1, borderRadius: 99, paddingVertical: 8, paddingHorizontal: 12, marginBottom: 14 }, simulationStatusText: { color: colors.orangeDark, fontSize: 11, letterSpacing: 0.45, fontWeight: '900' },
  simulatorCard: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line, borderRadius: 23, padding: 17, marginTop: 18 }, simulatorCritical: { backgroundColor: '#FFF8F6', borderColor: '#C84B3C', borderWidth: 2 }, simulatorHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7, gap: 10 }, simulatorHeadingCopy: { flex: 1 }, simulatorEyebrow: { color: colors.orangeDark, fontSize: 10, fontWeight: '900', letterSpacing: 1.1 }, simulatorTitle: { color: colors.navy, fontWeight: '900', fontSize: 19, marginTop: 4 }, criticalText: { color: colors.red }, criticalBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: colors.red, paddingVertical: 7, paddingHorizontal: 9, borderRadius: 10 }, criticalBadgeText: { color: '#FFFFFF', fontSize: 10, fontWeight: '900', letterSpacing: 0.4 },
  choiceGroup: { marginTop: 13 }, choiceLabel: { color: colors.navy, fontSize: 12, fontWeight: '800', marginBottom: 7 }, choices: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 }, choice: { minHeight: 34, borderWidth: 1, borderColor: colors.line, borderRadius: 11, backgroundColor: colors.cream, paddingVertical: 7, paddingHorizontal: 10, justifyContent: 'center' }, choiceSelected: { backgroundColor: colors.orange, borderColor: colors.orangeDark }, choiceDisabled: { opacity: 0.75 }, choiceText: { color: colors.muted, fontSize: 11, fontWeight: '700' }, choiceTextSelected: { color: '#FFFFFF' }, fireRule: { color: colors.red, fontSize: 11, fontWeight: '700', marginTop: 6 },
  diagram: { width: '100%', maxWidth: 310, height: 204, alignSelf: 'center', marginTop: 18, marginBottom: 8, borderRadius: 19, backgroundColor: '#F8F5EF', borderWidth: 1, borderColor: colors.line, position: 'relative' }, diagramCritical: { backgroundColor: '#FFF1ED', borderColor: '#E5A9A0' }, palm: { position: 'absolute', width: 104, height: 95, left: '50%', top: '50%', marginLeft: -52, marginTop: -47, borderRadius: 34, borderWidth: 1, borderColor: '#DDD4C8', backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center', gap: 5 }, palmCritical: { borderColor: '#E7B5AC' }, palmLabel: { color: colors.muted, fontSize: 9, letterSpacing: 1, fontWeight: '900' }, actuatorNode: { position: 'absolute', minWidth: 60, minHeight: 37, borderRadius: 13, borderWidth: 1, borderColor: '#DAD1C5', backgroundColor: '#FFFFFF', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, paddingHorizontal: 7 }, actuatorNodeActive: { borderColor: colors.orangeDark, backgroundColor: '#FFF0DE' }, actuatorNodeCritical: { borderColor: colors.red, backgroundColor: '#FBE0DB' }, actuatorDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#C9C2B8' }, actuatorDotActive: { width: 11, height: 11, borderRadius: 6, backgroundColor: colors.orange }, actuatorDotCritical: { backgroundColor: colors.red }, actuatorLabel: { color: colors.muted, fontSize: 9, fontWeight: '800', textTransform: 'uppercase' }, actuatorLabelActive: { color: colors.orangeDark }, frontNode: { top: 8, left: '50%', marginLeft: -35 }, backNode: { bottom: 8, left: '50%', marginLeft: -35 }, leftNode: { left: 8, top: '50%', marginTop: -18 }, rightNode: { right: 8, top: '50%', marginTop: -18 },
  patternMeta: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, marginTop: 8 }, metaLabel: { color: colors.muted, fontSize: 9, letterSpacing: 1, fontWeight: '900' }, metaValue: { color: colors.navy, fontSize: 12, fontWeight: '800', marginTop: 4 }, timeline: { flexDirection: 'row', alignItems: 'center', minHeight: 44, paddingVertical: 8, marginTop: 5 }, timelineSegment: { flexDirection: 'row', alignItems: 'center' }, pulseBar: { borderRadius: 6 }, gapBar: { height: 2, backgroundColor: '#CFC6B9', marginHorizontal: 3 }, repeatLabel: { color: colors.orangeDark, fontSize: 12, fontWeight: '900', marginLeft: 5 }, patternExplanation: { color: colors.navy, fontSize: 12, lineHeight: 18, marginTop: 3 }, durationLabel: { color: colors.muted, fontSize: 10, marginTop: 6 },
  vibrationRow: { marginTop: 15, paddingTop: 13, borderTopWidth: 1, borderTopColor: colors.line, flexDirection: 'row', alignItems: 'center', gap: 10 }, vibrationCopy: { flex: 1 }, vibrationTitle: { color: colors.navy, fontSize: 12, fontWeight: '800' }, vibrationDetail: { color: colors.muted, fontSize: 10, lineHeight: 15, marginTop: 3 }, previewButton: { minHeight: 47, marginTop: 13, borderRadius: 14, backgroundColor: colors.navy, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }, previewButtonCritical: { backgroundColor: colors.red }, previewButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '900' }, previewError: { color: colors.red, fontSize: 11, lineHeight: 16, marginTop: 8 }, playingStatus: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10 }, playingText: { color: colors.navy, fontSize: 11, fontWeight: '700' },
  sectionHeading: { color: colors.navy, fontSize: 19, fontWeight: '900', marginTop: 27 }, sectionIntro: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 4, marginBottom: 4 }, libraryCard: { marginTop: 11, padding: 14 }, libraryCardCritical: { borderColor: '#D98276', borderWidth: 1.5, backgroundColor: '#FFF8F6' }, libraryHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 }, libraryIcon: { width: 36, height: 36, borderRadius: 13, backgroundColor: colors.surfaceWarm, alignItems: 'center', justifyContent: 'center' }, libraryIconCritical: { backgroundColor: '#FBE0DB' }, libraryTitleCopy: { flex: 1 }, libraryTitle: { color: colors.navy, fontSize: 13, fontWeight: '900' }, libraryRhythm: { color: colors.muted, fontSize: 10, marginTop: 3 }, criticalWord: { color: colors.red, fontSize: 9, fontWeight: '900' }, libraryExplanation: { color: colors.navy, fontSize: 11, lineHeight: 16, marginTop: 2 }, disclaimer: { color: colors.muted, textAlign: 'center', fontSize: 11, lineHeight: 17, marginTop: 22, paddingHorizontal: 12 },
});

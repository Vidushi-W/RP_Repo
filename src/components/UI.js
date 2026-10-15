import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { colors, spacing } from '../theme';

export function PageHeader({ eyebrow, title, subtitle, right }) {
  return (
    <View style={styles.headerRow}>
      <View style={styles.headerCopy}>
        {!!eyebrow && <Text style={styles.eyebrow}>{eyebrow}</Text>}
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
        {!!subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      </View>
      {right}
    </View>
  );
}

export function SectionTitle({ title, action, onAction }) {
  return <View style={styles.sectionRow}><Text accessibilityRole="header" style={styles.sectionTitle}>{title}</Text>{action && <Pressable accessibilityRole="button" onPress={onAction} hitSlop={8}><Text style={styles.action}>{action}</Text></Pressable>}</View>;
}

export function IconBox({ name, color = colors.orange, background = colors.surfaceWarm, size = 42 }) {
  return <View style={[styles.iconBox, { backgroundColor: background, width: size, height: size, borderRadius: size * 0.32 }]}><Feather name={name} size={size * 0.48} color={color} /></View>;
}

export function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function StateNotice({ icon, title, body, tone = 'neutral', action, onAction, accessibilityLabel }) {
  const palette = tone === 'error' ? { bg: colors.redSoft, fg: colors.red } : tone === 'success' ? { bg: colors.greenSoft, fg: colors.green } : { bg: colors.blueSoft, fg: colors.blue };
  return (
    <View accessibilityLabel={accessibilityLabel} style={[styles.notice, { backgroundColor: palette.bg }]}>
      <Feather name={icon} size={20} color={palette.fg} />
      <View style={styles.noticeCopy}>
        <Text style={[styles.noticeTitle, { color: palette.fg }]}>{title}</Text>
        <Text style={styles.noticeBody}>{body}</Text>
        {action && <Pressable accessibilityRole="button" onPress={onAction} style={styles.noticeAction}><Text style={[styles.action, { color: palette.fg }]}>{action}</Text></Pressable>}
      </View>
    </View>
  );
}

export function Pill({ label, tone = 'neutral' }) {
  const palette = tone === 'critical' ? [colors.redSoft, colors.red] : tone === 'high' ? ['#FFF3DB', '#8E5A00'] : tone === 'connected' ? [colors.greenSoft, colors.green] : [colors.blueSoft, colors.blue];
  return <View style={[styles.pill, { backgroundColor: palette[0] }]}><Text style={[styles.pillText, { color: palette[1] }]}>{label}</Text></View>;
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: spacing.md, marginBottom: spacing.lg },
  headerCopy: { flex: 1 }, eyebrow: { color: colors.orangeDark, fontSize: 12, fontWeight: '800', letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 6 },
  title: { color: colors.navy, fontSize: 30, lineHeight: 36, fontWeight: '800', letterSpacing: -0.6 },
  subtitle: { color: colors.muted, fontSize: 15, lineHeight: 22, marginTop: 5 },
  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  sectionTitle: { color: colors.navy, fontSize: 17, fontWeight: '800' }, action: { color: colors.orangeDark, fontSize: 13, fontWeight: '800' },
  iconBox: { alignItems: 'center', justifyContent: 'center' },
  card: { backgroundColor: colors.surface, borderColor: colors.line, borderWidth: 1, borderRadius: 22, padding: spacing.md, shadowColor: '#34210C', shadowOpacity: 0.045, shadowRadius: 12, shadowOffset: { width: 0, height: 5 }, elevation: 1 },
  notice: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, borderRadius: 16, padding: 14 }, noticeCopy: { flex: 1 },
  noticeTitle: { fontSize: 14, fontWeight: '800', marginBottom: 3 }, noticeBody: { fontSize: 13, color: colors.navy, lineHeight: 19 }, noticeAction: { marginTop: 8, alignSelf: 'flex-start' },
  pill: { alignSelf: 'flex-start', paddingVertical: 5, paddingHorizontal: 10, borderRadius: 99 }, pillText: { fontSize: 11, fontWeight: '800' },
});

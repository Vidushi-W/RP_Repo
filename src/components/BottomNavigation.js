import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { colors } from '../theme';

const items = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'alerts', label: 'Alerts', icon: 'bell' },
  { id: 'guide', label: 'Haptic Guide', icon: 'radio' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
];

export function BottomNavigation({ active, onNavigate }) {
  return (
    <View accessibilityRole="tablist" style={styles.bar}>
      {items.map(item => {
        const selected = active === item.id;
        return <Pressable key={item.id} accessibilityRole="tab" accessibilityState={{ selected }} accessibilityLabel={item.label} onPress={() => onNavigate(item.id)} style={styles.tab}>
          <View style={[styles.iconWrap, selected && styles.selectedIcon]}><Feather name={item.icon} size={19} color={selected ? colors.orangeDark : colors.muted} /></View>
          <Text numberOfLines={1} style={[styles.label, selected && styles.selectedLabel]}>{item.label}</Text>
        </Pressable>;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', backgroundColor: colors.surface, borderTopColor: colors.line, borderTopWidth: 1, paddingHorizontal: 8, paddingTop: 8, paddingBottom: 8 },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56, gap: 3 }, iconWrap: { width: 34, height: 28, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  selectedIcon: { backgroundColor: colors.surfaceWarm }, label: { color: colors.muted, fontSize: 10, fontWeight: '700' }, selectedLabel: { color: colors.orangeDark },
});

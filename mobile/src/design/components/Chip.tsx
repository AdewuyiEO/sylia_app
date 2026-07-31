import React from 'react';
import { Pressable, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme';

type Variant = 'filter' | 'plain';

export function Chip({
  label,
  selected,
  onPress,
  variant = 'filter',
}: {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  variant?: Variant;
}) {
  const { c, radius, type } = useTheme();
  const bg = selected ? c.signalTint : c.chalk;
  const fg = selected ? c.signal : c.graphite;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected }}
      style={[
        styles.chip,
        {
          backgroundColor: bg,
          borderRadius: radius.chip,
          borderWidth: selected ? 1 : 0,
          borderColor: selected ? c.signal : 'transparent',
        },
      ]}
    >
      <Text style={{ ...type.caption, color: fg, fontWeight: '500' }}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: { height: 32, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center' },
});

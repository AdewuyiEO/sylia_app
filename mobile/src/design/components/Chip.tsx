import React from 'react';
import { Pressable } from 'react-native';
import { useTheme } from '../theme';
import { Text } from './Text';

/** Selected filters go olive; anything AI-generated or needing attention goes
 * ember tint. Never both on one chip. */
export function Chip({ label, selected, attention, onPress }: {
  label: string; selected?: boolean; attention?: boolean; onPress?: () => void;
}) {
  const { c, radius, layout } = useTheme();
  const bg = selected ? c.brand : attention ? c.actionTint : c.inset;
  const fg = selected ? c.surface : attention ? c.action : c.ink;
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityState={{ selected: !!selected }}
      hitSlop={7}
      style={{ height: layout.chipHeight, paddingHorizontal: 12, borderRadius: radius.chip, backgroundColor: bg,
               alignItems: 'center', justifyContent: 'center' }}
    >
      <Text variant="small" style={{ color: fg, fontFamily: 'Inter_500Medium' }}>{label}</Text>
    </Pressable>
  );
}

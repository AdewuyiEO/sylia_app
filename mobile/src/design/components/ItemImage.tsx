import React from 'react';
import { View, type ViewStyle } from 'react-native';
import { Image } from 'expo-image';
import { useTheme } from '../theme';

/** Named colours the CV pipeline emits → swatches for items without a photo. */
export const SWATCH: Record<string, string> = {
  black: '#1A1A1E', charcoal: '#3A3A44', grey: '#96969E', white: '#F5F5F7', cream: '#E7DFCE',
  beige: '#D6C7AA', sand: '#C9A87C', brown: '#6E4C34', tan: '#AA825A', navy: '#2C3648',
  blue: '#466EA5', denim: '#4B698C', olive: '#6B6B4E', sage: '#8A9A82', green: '#467850',
  rust: '#B4603C', clay: '#A9694E', red: '#A83434', burgundy: '#6E2837', pink: '#D296A5',
  purple: '#6E508C', yellow: '#D2B95A', orange: '#CD823C', stone: '#9A958C', indigo: '#3B4A7A',
};

/** A garment on a linen mat: the photo/cut-out when there is one, else its colour. */
export function ItemImage({ uri, color, style, label }: { uri?: string | null; color?: string | null; style?: ViewStyle; label?: string }) {
  const { c, radius } = useTheme();
  return (
    <View
      accessible={!!label}
      accessibilityRole="image"
      accessibilityLabel={label}
      style={[{ backgroundColor: c.mat, borderRadius: radius.card, overflow: 'hidden' }, style]}
    >
      {uri ? (
        <Image source={{ uri }} style={{ flex: 1 }} contentFit="contain" transition={150} cachePolicy="memory-disk" />
      ) : (
        <View style={{ flex: 1, margin: '22%', borderRadius: 8, backgroundColor: (color && SWATCH[color]) || c.inset }} />
      )}
    </View>
  );
}

import React from 'react';
import { View, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { colorOf } from '../../domain/garments';
import { slotOf } from '../../domain/garments';
import { GarmentArt } from '../art/garments';
import type { ColorId, Garment } from '../../domain/types';

/**
 * The Rail — the signature element. A horizontally scrolling strip of the
 * user's own wardrobe colours: their identity, a live filter, and visible
 * proof Aura has looked at their closet.
 */
export function SwatchStrip({
  colors,
  selected,
  onSelect,
}: {
  colors: ColorId[];
  selected?: ColorId | null;
  onSelect?: (c: ColorId | null) => void;
}) {
  const { c, radius, layout } = useTheme();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ gap: 8, paddingHorizontal: layout.gutter, paddingVertical: 4 }}
    >
      {colors.map((id) => {
        const sel = selected === id;
        return (
          <Pressable
            key={id}
            onPress={() => onSelect?.(sel ? null : id)}
            accessibilityRole="button"
            accessibilityLabel={`${colorOf(id).name} filter`}
            accessibilityState={{ selected: sel }}
            style={{
              width: 44,
              height: 44,
              borderRadius: radius.content,
              backgroundColor: colorOf(id).hex,
              borderWidth: 1,
              borderColor: 'rgba(0,0,0,0.06)',
              ...(sel ? { borderWidth: 2, borderColor: c.ink } : null),
            }}
          />
        );
      })}
    </ScrollView>
  );
}

/**
 * OutfitComposite — the flat-lay. Hero (top or dress) on the left, the rest
 * stacked to the right. Matches the arrangement proven in the web reference.
 */
export function OutfitComposite({ pieces, height = 466 }: { pieces: Garment[]; height?: number }) {
  const { c, radius } = useTheme();
  const hero = pieces.find((p) => ['top', 'dress'].includes(slotOf(p.type))) ?? pieces[0];
  const bottom = pieces.find((p) => slotOf(p.type) === 'bottom');
  const outer = pieces.find((p) => slotOf(p.type) === 'outer');
  const shoes = pieces.find((p) => slotOf(p.type) === 'shoes');
  const acc = pieces.find((p) => slotOf(p.type) === 'acc');
  const stackLeft = bottom ?? outer;
  const stackRight = [outer && outer !== stackLeft ? outer : null, acc, shoes].filter(Boolean) as Garment[];

  return (
    <View style={[styles.composite, { height, backgroundColor: c.chalk, borderRadius: radius.content }]}>
      <View style={styles.heroCol}>
        {hero && <GarmentArt type={hero.type} color={hero.color} size={150} />}
      </View>
      <View style={styles.stackCol}>
        {stackLeft && <GarmentArt type={stackLeft.type} color={stackLeft.color} size={92} />}
        <View style={{ height: 10 }} />
        {stackRight.map((p) => (
          <View key={p.id} style={{ marginTop: 8 }}>
            <GarmentArt type={p.type} color={p.color} size={78} />
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  composite: {
    flexDirection: 'row',
    padding: 22,
    overflow: 'hidden',
  },
  heroCol: { flex: 1.15, alignItems: 'center', justifyContent: 'center' },
  stackCol: { flex: 1, alignItems: 'center', justifyContent: 'center' },
});

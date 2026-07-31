import React from 'react';
import { View, Text, ScrollView, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../../src/design/theme';
import { EmptyState } from '../../src/design/components/EmptyState';
import { useCloset } from '../../src/state/hooks';
import type { ApiItem } from '../../src/data/api/endpoints';

/**
 * Closet — the wardrobe grid, from the backend.
 * Pure renderer over useCloset() (loading / error / empty / data). No fetch here.
 * Redesign = re-style these states; the data hook stays untouched.
 */
export default function ClosetScreen() {
  const { c, type, layout, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const { items, loading, error, load } = useCloset();

  React.useEffect(() => { load(); }, [load]);

  const Header = (
    <View style={[styles.hdr, { paddingHorizontal: layout.gutter, paddingTop: insets.top + 8 }]}>
      <Text style={{ ...type.displayL, color: c.ink }}>Closet</Text>
      {!loading && !error ? (
        <Text style={{ ...type.caption, color: c.slate }}>{items.length} items</Text>
      ) : null}
    </View>
  );

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <View style={styles.center}><ActivityIndicator color={c.ink} /></View>
      </View>
    );
  }
  if (error) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <EmptyState title="Couldn't load your closet." body={error}
          primary={{ label: 'Try again', onPress: load }} />
      </View>
    );
  }
  if (items.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <EmptyState title="Your closet is empty."
          body="Add a few pieces and Sylia will start styling you." />
      </View>
    );
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: c.paper }}
      contentContainerStyle={{ paddingBottom: 120 }}>
      {Header}
      <View style={[styles.grid, { paddingHorizontal: layout.gutter }]}>
        {items.map((it: ApiItem) => (
          <View key={it.id} style={[styles.tile, { backgroundColor: c.chalk, borderRadius: radius.control }]}>
            <View style={[styles.swatch, { backgroundColor: swatch(it.primary_color) }]} />
            <Text style={{ ...type.micro, color: c.ink }} numberOfLines={1}>
              {it.subcategory ?? it.category}
            </Text>
            <Text style={{ ...type.micro, color: c.slate }} numberOfLines={1}>
              {it.primary_color ?? '—'}
              {it.classification_confidence != null && it.classification_confidence < 0.5 ? ' · review' : ''}
            </Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

// crude name→swatch so the grid reads before real cut-out images are shown
function swatch(name: string | null): string {
  const map: Record<string, string> = {
    navy: '#2C3648', cream: '#E7DFCE', black: '#1A1A1E', white: '#F4F4F7',
    grey: '#96969E', olive: '#6B6B4E', rust: '#B4603C', brown: '#6E4C34',
    sage: '#8A9A82', charcoal: '#3A3A44', beige: '#D6C7AA',
  };
  return (name && map[name]) || '#C9C9D0';
}

const styles = StyleSheet.create({
  hdr: { paddingBottom: 12 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: { width: '30%', aspectRatio: 0.8, padding: 8, gap: 4 },
  swatch: { flex: 1, borderRadius: 6, marginBottom: 4 },
});

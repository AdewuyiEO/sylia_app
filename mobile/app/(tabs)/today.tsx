import React from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../../src/design/theme';
import { useToast } from '../../src/ui/toast';
import { Button } from '../../src/design/components/Button';
import { ReasonPill } from '../../src/design/components/ReasonPill';
import { EmptyState } from '../../src/design/components/EmptyState';
import { useAsync } from '../../src/state/useAsync';
import { api, type ApiLook } from '../../src/data/api/endpoints';

/**
 * Today — the daily look, from the backend scorer.
 * The screen is a pure renderer of four states (loading / error / empty / data)
 * over api.dailyLook.get(). It never scores anything itself — the server does.
 * Redesign = re-render these four states differently; the fetch stays put.
 */
export default function TodayScreen() {
  const { c, type, space, layout } = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { data, loading, error, refetch } = useAsync(() => api.dailyLook.get());

  const Header = (
    <View style={[styles.hdr, { paddingHorizontal: layout.gutter, paddingTop: insets.top + 8 }]}>
      <Text style={{ ...type.micro, color: c.slate }}>{today().toUpperCase()}</Text>
      <Text style={{ ...type.displayL, color: c.ink }}>Today</Text>
    </View>
  );

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <View style={styles.center}>
          <ActivityIndicator color={c.ink} />
          <Text style={{ ...type.caption, color: c.slate, marginTop: 12 }}>Pulling your look…</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <EmptyState title="Couldn't reach Sylia." body={error}
          primary={{ label: 'Try again', onPress: refetch }} />
      </View>
    );
  }

  const looks = data?.looks ?? [];
  if (looks.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: c.paper }}>
        {Header}
        <EmptyState title="No look yet."
          body={data?.reason ?? 'Add a few items to your closet and Sylia will style you.'}
          primary={{ label: 'Go to Closet', onPress: () => toast({ message: 'Tap the Closet tab to add items' }) }}
          secondary={{ label: 'Refresh', onPress: refetch }} />
      </View>
    );
  }

  const hero = looks[0];
  return (
    <ScrollView style={{ flex: 1, backgroundColor: c.paper }}
      contentContainerStyle={{ paddingBottom: 64 + 24 }} showsVerticalScrollIndicator={false}>
      {Header}
      {data?.context?.weather ? (
        <View style={[styles.ctx, { paddingHorizontal: layout.gutter }]}>
          <Text style={{ ...type.label, color: c.graphite }}>{Math.round(data.context.weather.temp_f)}°F</Text>
          {data.context.weather.precipitation ? <Text style={{ ...type.label, color: c.slate }}> · Rain</Text> : null}
          {data.context.calendar?.driver ? <Text style={{ ...type.label, color: c.slate }}> · {data.context.calendar.driver}</Text> : null}
        </View>
      ) : null}
      <LookCard look={hero} onWear={() => onWear(toast)} />
      {looks.length > 1 ? (
        <>
          <Text style={{ ...type.heading, color: c.ink, paddingHorizontal: layout.gutter, marginTop: space.s7, marginBottom: 12 }}>
            More looks for today
          </Text>
          {looks.slice(1).map((l, i) => (
            <View key={i} style={{ paddingHorizontal: layout.gutter, marginBottom: space.s4 }}>
              <MiniLook look={l} onWear={() => onWear(toast)} />
            </View>
          ))}
        </>
      ) : null}
    </ScrollView>
  );
}

function LookCard({ look, onWear }: { look: ApiLook; onWear: () => void }) {
  const { c, type, radius, layout, space } = useTheme();
  return (
    <View style={{ paddingHorizontal: layout.gutter }}>
      <View style={[styles.card, { backgroundColor: c.chalk, borderRadius: radius.content }]}>
        <View style={styles.pieceRow}>
          {look.items.map((it) => (
            <View key={it.id} style={styles.piece}>
              <View style={[styles.swatch, { backgroundColor: swatch(it.primary_color, c) }]} />
              <Text style={{ ...type.micro, color: c.graphite, marginTop: 4 }}>{it.subcategory}</Text>
            </View>
          ))}
        </View>
        <View style={{ marginTop: space.s4 }}>
          <ReasonPill text={look.explanation} solid />
        </View>
      </View>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: space.s3 }}>
        <Button label="Wearing this" variant="signal" onPress={onWear} fill />
        <Text style={{ ...type.micro, color: c.slate, alignSelf: 'center' }}>{Math.round(look.score_total)}</Text>
      </View>
    </View>
  );
}

function MiniLook({ look, onWear }: { look: ApiLook; onWear: () => void }) {
  const { c, type, radius } = useTheme();
  return (
    <View style={[styles.mini, { backgroundColor: c.chalk, borderRadius: radius.content }]}>
      <View style={styles.pieceRow}>
        {look.items.map((it) => (
          <View key={it.id} style={[styles.swatchSm, { backgroundColor: swatch(it.primary_color, c) }]} />
        ))}
      </View>
      <Text numberOfLines={1} style={{ ...type.caption, color: c.graphite, flex: 1, marginLeft: 10 }}>{look.explanation}</Text>
      <Button label="Wear" variant="secondary" onPress={onWear} />
    </View>
  );
}

function onWear(toast: (t: { message: string }) => void) {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  toast({ message: 'Logged — nice choice.' });
}

function swatch(name: string | null, c: any): string {
  const map: Record<string, string> = {
    navy: '#2C3648', cream: '#E7DFCE', black: '#1A1A1E', white: '#F4F4F7',
    brown: '#6E4C34', rust: '#B4603C', olive: '#6B6B4E', grey: '#96969E',
    charcoal: '#3A3A44', sand: '#C9A87C', sage: '#8A9A82', burgundy: '#6E2837',
  };
  return (name && map[name]) || c.ash;
}

function today(): string {
  return new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

const styles = StyleSheet.create({
  hdr: { paddingBottom: 8 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  ctx: { flexDirection: 'row', alignItems: 'center', paddingBottom: 12 },
  card: { padding: 20 },
  pieceRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, alignItems: 'center' },
  piece: { alignItems: 'center' },
  swatch: { width: 56, height: 56, borderRadius: 6 },
  swatchSm: { width: 28, height: 28, borderRadius: 4, marginRight: -6, borderWidth: 1, borderColor: 'rgba(0,0,0,0.05)' },
  mini: { flexDirection: 'row', alignItems: 'center', padding: 12 },
});

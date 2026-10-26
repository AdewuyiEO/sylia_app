import React, { useState } from 'react';
import { View, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Chip } from '../../src/design/components/Chip';
import { Header, Body, Card, Loading, EmptyState } from '../../src/design/components/Screen';
import { ScoreRing, SubscoreRows } from '../../src/design/components/ScoreRing';
import { ItemImage } from '../../src/design/components/ItemImage';
import { useToast } from '../../src/ui/toast';
import { useDailyLook, useOnFocus } from '../../src/state/hooks';
import { useAuth } from '../../src/state/auth';
import { ApiError } from '../../src/data/api/client';
import type { ApiLook } from '../../src/data/api/endpoints';
import { errorText } from '../../src/state/useAsync';
import { longDate, temperature } from '../../src/lib/format';
import { t } from '../../src/i18n';

/**
 * Today — the core loop. Renders the server's looks (the scorer chose; Sylia
 * only explains). Four states: loading / error / empty / data.
 */
export default function TodayScreen() {
  const router = useRouter();
  const toast = useToast();
  const units = useAuth((s) => s.me?.units ?? 'metric');
  const { data, loading, error, refetch, stats, wear, swap } = useDailyLook();
  const [busy, setBusy] = useState<string | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  useOnFocus(refetch);

  const header = (
    <Header
      eyebrow={longDate()}
      title={t('today.title')}
      right={stats && stats.streak_days > 1 ? <Chip label={t('today.streak', { count: stats.streak_days })} /> : undefined}
    />
  );

  if (loading && !data) return <View style={{ flex: 1 }}>{header}<Loading label={t('today.loading')} /></View>;
  if (error && !data) {
    return <View style={{ flex: 1 }}>{header}<Body><EmptyState title={error} primary={{ label: t('common.tryAgain'), onPress: refetch }} /></Body></View>;
  }

  const looks = (data?.looks ?? []).filter((l) => l.user_feedback !== 'skipped');
  if (looks.length === 0) {
    return (
      <View style={{ flex: 1 }}>
        {header}
        <Body onRefresh={refetch} refreshing={loading}>
          <EmptyState title={t('today.emptyTitle')} body={data?.reason ?? t('today.emptyBody')}
                      primary={{ label: t('today.goCloset'), onPress: () => router.push('/capture') }} />
        </Body>
      </View>
    );
  }

  const hero = looks.find((l) => l.user_feedback === 'worn') ?? looks[0];
  const rest = looks.filter((l) => l.id !== hero.id);
  const ctx = data?.context;
  const ctxLine = [temperature(ctx?.weather, units), ctx?.weather?.precipitation ? t('today.rain') : null, ctx?.calendar?.driver]
    .filter(Boolean).join(' · ');

  const act = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) router.push('/paywall?reason=swap');
      else if (e instanceof ApiError && e.status === 409) toast({ message: t('today.noSwap') });
      else toast({ message: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  const onWear = (look: ApiLook) => act(`wear:${look.id}`, async () => {
    const n = await wear(look);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    toast({ message: t('today.wornToast', { count: n }) });
  });
  const onAnother = () => act('another', async () => { await swap(hero); setShowWhy(false); });
  const onSwapPiece = () => {
    const top = hero.items.find((i) => i.category === 'top' || i.category === 'dress') ?? hero.items[0];
    return act('piece', async () => { await swap(hero, top?.id); });
  };

  const worn = hero.user_feedback === 'worn';

  return (
    <View style={{ flex: 1 }}>
      {header}
      <Body onRefresh={refetch} refreshing={loading}>
        {ctxLine ? <Text variant="small" tone="ink60">{ctxLine}</Text> : null}

        <Card style={{ padding: 0, overflow: 'hidden', gap: 0 }}>
          <LookPieces look={hero} />
          <View style={{ padding: 16, gap: 14 }}>
            <View style={{ flexDirection: 'row', gap: 16, alignItems: 'center' }}>
              <ScoreRing breakdown={hero.score_breakdown} />
              <View style={{ flex: 1, gap: 6 }}>
                <Text variant="h2" numberOfLines={2}>{lookName(hero)}</Text>
                <Pressable onPress={() => setShowWhy(!showWhy)} accessibilityRole="button" hitSlop={8}>
                  <Text variant="small" tone="brand">{t('today.why')} {showWhy ? '▴' : '▾'}</Text>
                </Pressable>
              </View>
            </View>
            <Text>{hero.explanation}</Text>
            {showWhy ? <SubscoreRows breakdown={hero.score_breakdown} /> : null}
          </View>
        </Card>

        {worn ? (
          <Button label={`✓ ${t('today.worn')}`} variant="tertiary" disabled />
        ) : (
          <Button label={t('today.wear')} onPress={() => onWear(hero)} loading={busy === `wear:${hero.id}`} />
        )}
        {!worn ? (
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Button label={t('today.another')} variant="secondary" onPress={onAnother} loading={busy === 'another'} style={{ flex: 1 }} />
            <Button label={t('today.swapPiece')} variant="tertiary" onPress={onSwapPiece} loading={busy === 'piece'} style={{ flex: 1 }} />
          </View>
        ) : null}

        {rest.length ? (
          <View style={{ gap: 10, marginTop: 8 }}>
            <Text variant="h2">{t('today.more')}</Text>
            {rest.map((l) => (
              <Card key={l.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12 }}>
                <View style={{ flexDirection: 'row', gap: 4 }}>
                  {l.items.slice(0, 3).map((it) => (
                    <ItemImage key={it.id} uri={it.image_url} color={it.primary_color} style={{ width: 44, height: 56 }} />
                  ))}
                </View>
                <Text variant="small" tone="ink60" numberOfLines={2} style={{ flex: 1 }}>{l.explanation}</Text>
                <Button label={t('today.wear')} variant="secondary" onPress={() => onWear(l)}
                        loading={busy === `wear:${l.id}`} style={{ alignSelf: 'auto', paddingHorizontal: 12 }} />
              </Card>
            ))}
          </View>
        ) : null}
      </Body>
    </View>
  );
}

function LookPieces({ look }: { look: ApiLook }) {
  const { c } = useTheme();
  const items = look.items;
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', backgroundColor: c.mat, padding: 6, gap: 6 }}>
      {items.map((it) => (
        <ItemImage key={it.id} uri={it.image_url} color={it.primary_color}
                   label={[it.primary_color, it.subcategory ?? it.category].filter(Boolean).join(' ')}
                   style={{ width: items.length > 2 ? '48.5%' : '49%', aspectRatio: 0.85, borderRadius: 10 }} />
      ))}
    </View>
  );
}

/** "Navy trousers, cream blouse" — the outfit name, from its two main pieces. */
function lookName(look: ApiLook): string {
  const main = look.items.filter((i) => ['dress', 'top', 'bottom'].includes(i.category)).slice(0, 2);
  const name = main.map((i) => [i.primary_color, i.subcategory ?? i.category].filter(Boolean).join(' ')).join(', ');
  return name ? name.charAt(0).toUpperCase() + name.slice(1) : t('today.title');
}

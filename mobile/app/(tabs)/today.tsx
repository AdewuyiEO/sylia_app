import React, { useEffect, useState } from 'react';
import { View, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Image } from 'expo-image';
import { Flame } from '../../src/design/components/Flame';
import { scheduleDailyReveal } from '../../src/lib/reminders';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
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
  const { c } = useTheme();
  const units = useAuth((s) => s.me?.units ?? 'metric');
  const revealHour = useAuth((s) => s.me?.reveal_hour ?? 7);
  const { data, loading, error, refetch, stats, wear, swap } = useDailyLook();
  const [busy, setBusy] = useState<string | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  useOnFocus(refetch);

  // keep tomorrow's reminder current (copy carries the streak); no prompt here
  useEffect(() => {
    if (stats) scheduleDailyReveal(revealHour, stats.streak_days);
  }, [stats?.streak_days, revealHour]);

  const header = (
    <Header
      eyebrow={longDate()}
      title={t('today.title')}
      right={stats ? (
        <Pressable onPress={() => router.push('/journey')} accessibilityRole="button"
                   accessibilityLabel={t('journey.days', { count: stats.streak_days })}
                   style={{ minHeight: 36, paddingHorizontal: 12, borderRadius: 18, flexDirection: 'row', alignItems: 'center',
                            gap: 6, backgroundColor: c.actionTint }}>
          <Flame size={16} color={stats.streak_days ? c.action : c.inactive} />
          <Text variant="bodyStrong" style={{ color: '#A6431F' }}>{stats.streak_days}</Text>
        </Pressable>
      ) : undefined}
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
  const ctx = data?.context;
  const ctxLine = [temperature(ctx?.weather, units), ctx?.weather?.precipitation ? t('today.rain') : null, ctx?.calendar?.driver]
    .filter(Boolean).join(' · ');

  if (data && data.revealed === false) {
    const photo = hero.items.find((i) => i.category === 'dress' || i.category === 'top')?.image_url ?? hero.items[0]?.image_url;
    return (
      <View style={{ flex: 1 }}>
        {header}
        <Body onRefresh={refetch} refreshing={loading}>
          <Pressable onPress={() => router.push('/reveal')} accessibilityRole="button" accessibilityLabel={`${t('reveal.card')}. ${t('reveal.tap')}`}
                     style={{ height: 460, borderRadius: 20, overflow: 'hidden', backgroundColor: c.mat }}>
            {photo ? <Image source={{ uri: photo }} style={{ flex: 1 }} contentFit="cover" blurRadius={40} /> : null}
            <View style={{ position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center', gap: 14,
                           backgroundColor: 'rgba(36,28,20,0.35)' }}>
              <View style={{ width: 120, height: 120, borderRadius: 60, backgroundColor: c.action, alignItems: 'center', justifyContent: 'center' }}>
                <Text variant="bodyStrong" style={{ color: c.onAction, textAlign: 'center' }}>{t('reveal.tap')}</Text>
              </View>
              <Text variant="h2" style={{ color: '#FBF9F5', textAlign: 'center', paddingHorizontal: 24 }}>{t('reveal.card')}</Text>
            </View>
          </Pressable>
          {ctxLine ? <Text variant="small" tone="ink60" style={{ textAlign: 'center' }}>{ctxLine}</Text> : null}
        </Body>
      </View>
    );
  }
  const rest = looks.filter((l) => l.id !== hero.id);

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
          <Button label={t('today.wearStreak')} onPress={() => onWear(hero)} loading={busy === `wear:${hero.id}`} />
        )}
        {!worn ? (
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Button label={t('today.another')} variant="secondary" onPress={onAnother} loading={busy === 'another'} style={{ flex: 1 }} />
            <Button label={t('today.swapPiece')} variant="tertiary" onPress={onSwapPiece} loading={busy === 'piece'} style={{ flex: 1 }} />
          </View>
        ) : null}

        {data?.next_reveal_at ? (
          <Card inset style={{ flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12 }}>
            <Flame size={18} color={c.action} />
            <Text variant="small" style={{ flex: 1 }}>{t('reveal.next', { time: timeOf(data.next_reveal_at) })}</Text>
          </Card>
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

function timeOf(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch {
    return '7:00';
  }
}

/** "Navy trousers, cream blouse" — the outfit name, from its two main pieces. */
function lookName(look: ApiLook): string {
  const main = look.items.filter((i) => ['dress', 'top', 'bottom'].includes(i.category)).slice(0, 2);
  const name = main.map((i) => [i.primary_color, i.subcategory ?? i.category].filter(Boolean).join(' ')).join(', ');
  return name ? name.charAt(0).toUpperCase() + name.slice(1) : t('today.title');
}

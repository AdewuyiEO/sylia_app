import React, { useState } from 'react';
import { View, Pressable } from 'react-native';
import { Image } from 'expo-image';
import Animated, { FadeInDown, ZoomIn } from 'react-native-reanimated';
import { Flame } from '../src/design/components/Flame';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Header, Body, Card, Loading, EmptyState } from '../src/design/components/Screen';
import { useToast } from '../src/ui/toast';
import { useAsync, errorText } from '../src/state/useAsync';
import { useOnFocus } from '../src/state/hooks';
import { api, type Journey, type JourneyDay, type Badge } from '../src/data/api/endpoints';
import { t, type StringKey } from '../src/i18n';

/** Style journey: the reasons to come back tomorrow, all from real wear history. */
export default function JourneyScreen() {
  const { c } = useTheme();
  const toast = useToast();
  const { data, loading, error, refetch, setData } = useAsync(() => api.journey.get());
  const [accepting, setAccepting] = useState(false);
  useOnFocus(refetch);

  if (loading && !data) return <View style={{ flex: 1 }}><Header back title={t('journey.title')} /><Loading /></View>;
  if (!data) {
    return <View style={{ flex: 1 }}><Header back title={t('journey.title')} />
      <Body><EmptyState title={error ?? ''} primary={{ label: t('common.tryAgain'), onPress: refetch }} /></Body></View>;
  }

  const j: Journey = data;
  const accept = async () => {
    setAccepting(true);
    try {
      setData(await api.journey.acceptChallenge());
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setAccepting(false);
    }
  };
  const lvl = j.level;
  const pct = lvl.next_at ? (lvl.points - lvl.floor) / (lvl.next_at - lvl.floor) : 1;

  return (
    <View style={{ flex: 1 }}>
      <Header back title={t('journey.title')} />
      <Body onRefresh={refetch} refreshing={loading}>
        <Animated.View entering={FadeInDown.duration(400)} style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}
                       accessible accessibilityLabel={`${t('journey.days', { count: j.streak })}. ${t('journey.longest', { longest: j.longest, freezes: j.freezes, max: j.max_freezes })}`}>
          <Flame size={60} color={j.streak ? c.action : c.inactive} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="display">{t('journey.days', { count: j.streak })}</Text>
            <Text variant="small" tone="ink60">{t('journey.longest', { longest: j.longest, freezes: j.freezes, max: j.max_freezes })}</Text>
          </View>
        </Animated.View>
        {j.streak === 0 ? <Text tone="ink60">{t('journey.empty')}</Text> : null}

        <Card>
          <Text variant="h3">{t('journey.last14')}</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {j.days.map((d, i) => <DayCell key={d.date} day={d} index={i} />)}
          </View>
          <Text variant="small" tone="ink60">{t('journey.freezeHint')}</Text>
        </Card>

        {j.challenge ? (
          <Animated.View entering={FadeInDown.delay(80).duration(400)}
                         style={{ flexDirection: 'row', borderRadius: 14, overflow: 'hidden', backgroundColor: c.ink }}>
            {j.challenge.item.image_url ? <Image source={{ uri: j.challenge.item.image_url }} style={{ width: 112 }} contentFit="cover" /> : null}
            <View style={{ flex: 1, padding: 14, gap: 8 }}>
              <Text variant="label" style={{ color: c.occasion }}>{t('journey.challenge', { days: j.challenge.days_left })}</Text>
              <Text variant="bodyStrong" style={{ color: c.bg }}>{j.challenge.title}</Text>
              <Text variant="small" style={{ color: c.mat }}>{t('journey.points', { points: j.challenge.points })}</Text>
              {j.challenge.completed ? (
                <Text variant="bodyStrong" style={{ color: c.weather }}>✓ {t('journey.completed')}</Text>
              ) : j.challenge.accepted ? (
                <Text variant="bodyStrong" style={{ color: c.weather }}>✓ {t('journey.accepted')}</Text>
              ) : (
                <Pressable onPress={accept} disabled={accepting} accessibilityRole="button"
                           style={{ alignSelf: 'flex-start', minHeight: 40, paddingHorizontal: 14, borderRadius: 10,
                                    backgroundColor: c.action, justifyContent: 'center', opacity: accepting ? 0.6 : 1 }}>
                  <Text variant="bodyStrong" style={{ color: c.onAction }}>{t('journey.accept')}</Text>
                </Pressable>
              )}
            </View>
          </Animated.View>
        ) : null}

        <View style={{ gap: 8 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <Text variant="h3">{t('journey.level', { level: lvl.level, name: lvl.name })}</Text>
            <Text variant="small" tone="ink60">
              {lvl.next_at ? t('journey.toNext', { points: lvl.points, next: lvl.next_at, name: lvl.next_name ?? '' })
                           : t('journey.maxLevel', { points: lvl.points })}
            </Text>
          </View>
          <View style={{ height: 8, borderRadius: 4, backgroundColor: c.inset }}>
            <View style={{ height: 8, borderRadius: 4, width: `${Math.round(Math.min(1, pct) * 100)}%`, backgroundColor: c.brand }} />
          </View>
        </View>

        <Text variant="h3">{t('journey.badges')}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
          {j.badges.map((b, i) => <BadgeView key={b.id} badge={b} index={i} />)}
        </View>
      </Body>
    </View>
  );
}

function DayCell({ day, index }: { day: JourneyDay; index: number }) {
  const { c } = useTheme();
  const size = { width: '12.5%' as const, aspectRatio: 1, borderRadius: 10, overflow: 'hidden' as const };
  const label = `${day.date}: ${day.state}`;
  const style = day.state === 'frozen' ? { backgroundColor: '#DCE6F0', borderWidth: 2, borderStyle: 'dashed' as const, borderColor: '#6E8FB0' }
    : day.state === 'today' ? { backgroundColor: c.actionTint, borderWidth: 2, borderStyle: 'dashed' as const, borderColor: c.action }
    : day.state === 'missed' ? { backgroundColor: c.inset } : { backgroundColor: c.brand };
  return (
    <Animated.View entering={ZoomIn.delay(index * 30).duration(300)} style={[size, style]} accessible accessibilityLabel={label}>
      {day.state === 'worn' && day.image_url ? <Image source={{ uri: day.image_url }} style={{ flex: 1 }} contentFit="cover" /> : null}
    </Animated.View>
  );
}

function BadgeView({ badge, index }: { badge: Badge; index: number }) {
  const { c } = useTheme();
  const key = `badge.${badge.id}` as StringKey;
  return (
    <Animated.View entering={ZoomIn.delay(200 + index * 60).duration(350)}
                   style={{ width: 76, alignItems: 'center', gap: 6, opacity: badge.earned ? 1 : 0.5 }}
                   accessible accessibilityLabel={`${badge.title}${badge.earned ? '' : ` ${Math.round(badge.progress * 100)}%`}`}>
      <View style={{ width: 64, height: 64, borderRadius: 32, overflow: 'hidden', borderWidth: 3,
                     borderColor: badge.earned ? c.occasion : c.hair, backgroundColor: c.inset }}>
        {badge.image_url ? <Image source={{ uri: badge.image_url }} style={{ flex: 1 }} contentFit="cover" /> : null}
      </View>
      <Text variant="small" style={{ textAlign: 'center' }}>{t(key) === key ? badge.title : t(key)}</Text>
    </Animated.View>
  );
}

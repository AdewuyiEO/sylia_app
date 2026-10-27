import React, { useEffect, useState } from 'react';
import { View, Pressable, StyleSheet, AccessibilityInfo } from 'react-native';
import { useRouter } from 'expo-router';
import { Image } from 'expo-image';
import * as Haptics from 'expo-haptics';
import Animated, {
  useSharedValue, useAnimatedStyle, withTiming, withRepeat, withSequence, withDelay, Easing, type SharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';
import { color } from '../src/design/tokens';
import { Text } from '../src/design/components/Text';
import { ScoreRing } from '../src/design/components/ScoreRing';
import { Loading } from '../src/design/components/Screen';
import { useAsync } from '../src/state/useAsync';
import { api, type ApiLook } from '../src/data/api/endpoints';
import { coarseLocation } from '../src/lib/device';
import { askPermission, scheduleDailyReveal } from '../src/lib/reminders';
import { useAuth } from '../src/state/auth';
import { longDate, temperature } from '../src/lib/format';
import { t } from '../src/i18n';

const D = color.dark;   // the reveal is always on espresso — it's a moment, not a screen

/** The day's hero photo: the dress or top of the top look. */
function heroImage(look: ApiLook | undefined): string | null {
  if (!look) return null;
  const main = look.items.find((i) => i.category === 'dress') ?? look.items.find((i) => i.category === 'top') ?? look.items[0];
  return main?.image_url ?? look.items.find((i) => i.image_url)?.image_url ?? null;
}

export default function RevealScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const units = useAuth((s) => s.me?.units ?? 'metric');
  const revealHour = useAuth((s) => s.me?.reveal_hour ?? 7);
  const { data, loading } = useAsync(async () => api.dailyLook.get(await coarseLocation()));
  const [shown, setShown] = useState(false);
  const [streak, setStreak] = useState<number | null>(null);

  const curtain = useSharedValue(0);      // 0 closed → 1 open
  const blur = useSharedValue(1);         // 1 blurred overlay visible → 0
  const pulse = useSharedValue(0);
  const cta = useSharedValue(0);
  const conf = useSharedValue(0);

  const look = data?.looks?.[0];
  const hero = heroImage(look);

  useEffect(() => {
    if (data?.revealed) {   // already opened today: show it straight away
      curtain.value = 1; blur.value = 0; cta.value = 1; setShown(true);
    }
  }, [data?.revealed]);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then((reduce) => {
      if (!reduce) pulse.value = withRepeat(withSequence(withTiming(1, { duration: 900 }), withTiming(0, { duration: 900 })), -1);
    });
  }, []);

  const reveal = async () => {
    if (!look || shown) return;
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    setShown(true);
    const reduce = await AccessibilityInfo.isReduceMotionEnabled();
    const ease = Easing.bezier(0.65, 0, 0.35, 1);
    curtain.value = reduce ? 1 : withTiming(1, { duration: 800, easing: ease });
    blur.value = reduce ? 0 : withTiming(0, { duration: 900, easing: Easing.out(Easing.cubic) });
    cta.value = reduce ? 1 : withDelay(700, withTiming(1, { duration: 400 }));
    conf.value = reduce ? 0 : withDelay(400, withTiming(1, { duration: 1600, easing: Easing.out(Easing.quad) }));
    try {
      const r = await api.dailyLook.reveal(look.id);
      setStreak(r.streak);
      // ask for the reminder in context, after the user felt the moment once
      if (await askPermission()) await scheduleDailyReveal(revealHour, r.streak);
    } catch {
      /* offline: the reveal still happened on screen */
    }
  };

  const leftStyle = useAnimatedStyle(() => ({ transform: [{ translateX: -curtain.value * 200 }] }));
  const rightStyle = useAnimatedStyle(() => ({ transform: [{ translateX: curtain.value * 200 }] }));
  const blurStyle = useAnimatedStyle(() => ({ opacity: blur.value }));
  const btnStyle = useAnimatedStyle(() => ({
    opacity: 1 - curtain.value,
    transform: [{ scale: 1 + pulse.value * 0.06 }],
  }));
  const ctaStyle = useAnimatedStyle(() => ({ opacity: cta.value, transform: [{ translateY: (1 - cta.value) * 16 }] }));

  if (loading && !data) return <View style={[styles.root, { backgroundColor: D.bg }]}><Loading /></View>;

  const ctx = data?.context;
  const meta = [longDate(), temperature(ctx?.weather, units)].filter(Boolean).join(' · ');
  const title = shown && look ? lookName(look) : t('reveal.ready');

  return (
    <View style={[styles.root, { backgroundColor: D.bg, paddingTop: insets.top + 16, paddingBottom: insets.bottom + 16 }]}>
      <View style={{ paddingHorizontal: 20, gap: 6 }}>
        <Text variant="label" style={{ color: D.occasion }}>{meta}</Text>
        <Text variant="h1" style={{ color: D.ink }} accessibilityLiveRegion="polite">{title}</Text>
      </View>

      <View style={[styles.box, { backgroundColor: D.surface }]}>
        {hero ? <Image source={{ uri: hero }} style={StyleSheet.absoluteFill} contentFit="cover" contentPosition="top" /> : null}
        {hero ? (
          <Animated.View style={[StyleSheet.absoluteFill, blurStyle]} pointerEvents="none">
            <Image source={{ uri: hero }} style={StyleSheet.absoluteFill} contentFit="cover" contentPosition="top" blurRadius={40} />
          </Animated.View>
        ) : null}
        <Animated.View style={[styles.curtain, { left: 0, backgroundColor: D.mat }, leftStyle]} pointerEvents="none" />
        <Animated.View style={[styles.curtain, { right: 0, backgroundColor: D.mat }, rightStyle]} pointerEvents="none" />

        {!shown ? (
          <Animated.View style={[styles.btnWrap, btnStyle]}>
            <Pressable onPress={reveal} accessibilityRole="button" accessibilityLabel={t('reveal.tap')}
                       style={[styles.btn, { backgroundColor: D.action }]}>
              <Svg width={28} height={28} viewBox="0 0 24 24"><Path d="M12 3l2.2 5.2L20 9l-4.4 3.8L17 18.5 12 15.6 7 18.5l1.4-5.7L4 9l5.8-.8z" fill="none" stroke={D.bg} strokeWidth={1.8} strokeLinejoin="round" /></Svg>
              <Text variant="bodyStrong" style={{ color: D.bg }}>{t('reveal.tap')}</Text>
            </Pressable>
          </Animated.View>
        ) : null}

        {shown && look ? (
          <View style={[styles.ring, { backgroundColor: D.bg }]}>
            <ScoreRing breakdown={look.score_breakdown} size={86} />
          </View>
        ) : null}
        {shown ? <Confetti progress={conf} /> : null}
      </View>

      <View style={{ paddingHorizontal: 20, gap: 10 }}>
        {shown ? (
          <Animated.View style={ctaStyle}>
            {streak ? <Text variant="small" style={{ color: D.ink60, textAlign: 'center', marginBottom: 10 }}>{t('reveal.streakDay', { count: streak + 1 })}</Text> : null}
            <Pressable onPress={() => router.replace('/today')} accessibilityRole="button"
                       style={[styles.cta, { backgroundColor: D.action }]}>
              <Text variant="h3" style={{ color: D.bg }}>{t('reveal.see')}</Text>
            </Pressable>
          </Animated.View>
        ) : (
          <Text variant="small" style={{ color: D.ink60, textAlign: 'center' }}>{t('reveal.picked', { count: data?.looks?.length ?? 0 })}</Text>
        )}
      </View>
    </View>
  );
}

const CONFETTI = [{ x: 0.2, c: D.action }, { x: 0.34, c: D.occasion }, { x: 0.5, c: D.fit }, { x: 0.64, c: D.ink }, { x: 0.78, c: D.fit }];

function Confetti({ progress }: { progress: SharedValue<number> }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {CONFETTI.map((p, i) => <Piece key={i} x={p.x} c={p.c} i={i} progress={progress} />)}
    </View>
  );
}

function Piece({ x, c, i, progress }: { x: number; c: string; i: number; progress: SharedValue<number> }) {
  const style = useAnimatedStyle(() => {
    const p = Math.max(0, Math.min(1, progress.value * 1.2 - i * 0.04));
    return {
      opacity: p === 0 ? 0 : p < 0.2 ? p * 5 : 1 - p,
      transform: [{ translateY: -240 * p }, { rotate: `${180 * p * (i % 2 ? 1 : -1)}deg` }],
    };
  });
  return <Animated.View style={[{ position: 'absolute', bottom: 100, left: `${x * 100}%`, width: 8, height: 14, borderRadius: 2, backgroundColor: c }, style]} />;
}

function lookName(look: ApiLook): string {
  const main = look.items.filter((i) => ['dress', 'top', 'bottom'].includes(i.category)).slice(0, 2);
  const s = main.map((i) => [i.primary_color, i.subcategory ?? i.category].filter(Boolean).join(' ')).join(', ');
  return s ? s.charAt(0).toUpperCase() + s.slice(1) + '.' : t('reveal.ready');
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'space-between', gap: 16 },
  box: { flex: 1, marginHorizontal: 20, borderRadius: 24, overflow: 'hidden' },
  curtain: { position: 'absolute', top: 0, bottom: 0, width: '50.5%' },
  btnWrap: { position: 'absolute', top: '50%', left: '50%', marginLeft: -66, marginTop: -66 },
  btn: { width: 132, height: 132, borderRadius: 66, alignItems: 'center', justifyContent: 'center', gap: 6 },
  ring: { position: 'absolute', right: 14, bottom: 14, width: 98, height: 98, borderRadius: 49, alignItems: 'center', justifyContent: 'center' },
  cta: { height: 48, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
});

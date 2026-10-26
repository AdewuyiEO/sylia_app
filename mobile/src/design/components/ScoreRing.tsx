import React, { useEffect } from 'react';
import { View, AccessibilityInfo } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Animated, { useSharedValue, useAnimatedProps, withTiming, Easing, type SharedValue } from 'react-native-reanimated';
import { useTheme } from '../theme';
import { Text } from './Text';
import { t } from '../../i18n';
import type { Breakdown } from '../../data/api/endpoints';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** Display order, clockwise from top, and which scorer subscore each shows. */
export const SUBSCORES = [
  { key: 'body', label: () => t('score.fit'), color: 'fit' },
  { key: 'color', label: () => t('score.palette'), color: 'palette' },
  { key: 'context', label: () => t('score.occasion'), color: 'occasion' },
  { key: 'identity', label: () => t('score.you'), color: 'weather' },
] as const;

/**
 * The quartered score ring: four arcs, one per subscore, centre number is the
 * mean. It draws itself in once (600ms) — the only entrance animation in the
 * app — and snaps to the end state when Reduce Motion is on.
 */
export function ScoreRing({ breakdown, size = 104 }: { breakdown: Breakdown; size?: number }) {
  const { c, motion } = useTheme();
  const stroke = 7;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const quarter = circ / 4;
  const gap = 6;
  const progress = useSharedValue(0);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then((reduce) => {
      progress.value = reduce ? 1 : withTiming(1, { duration: motion.ring, easing: Easing.inOut(Easing.cubic) });
    });
  }, [breakdown]);

  const mean = Math.round(SUBSCORES.reduce((s, x) => s + (breakdown[x.key] ?? 0), 0) / SUBSCORES.length);

  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={`${t('today.match')} ${mean}. ` + SUBSCORES.map((s) => `${s.label()} ${Math.round(breakdown[s.key])}`).join(', ')}
      style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}
    >
      <Svg width={size} height={size} style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}>
        {SUBSCORES.map((s, i) => (
          <Arc key={s.key} i={i} r={r} size={size} stroke={stroke} quarter={quarter} gap={gap} circ={circ}
               value={Math.max(0, Math.min(100, breakdown[s.key] ?? 0)) / 100}
               color={c[s.color]} track={c.inset} progress={progress} />
        ))}
      </Svg>
      <Text variant="h1" style={{ fontVariant: ['tabular-nums'] }}>{mean}</Text>
      <Text variant="label" tone="ink60" style={{ fontSize: 9 }}>{t('today.match')}</Text>
    </View>
  );
}

function Arc({ i, r, size, stroke, quarter, gap, circ, value, color, track, progress }: {
  i: number; r: number; size: number; stroke: number; quarter: number; gap: number; circ: number;
  value: number; color: string; track: string; progress: SharedValue<number>;
}) {
  const len = quarter - gap;
  const offset = -(i * quarter + gap / 2);
  const animated = useAnimatedProps(() => ({
    strokeDasharray: [len * value * progress.value, circ],
  }));
  return (
    <>
      <Circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none"
              strokeDasharray={[len, circ]} strokeDashoffset={offset} strokeLinecap="round" />
      <AnimatedCircle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
                      strokeDashoffset={offset} strokeLinecap="round" animatedProps={animated} />
    </>
  );
}

/** Same four colours as the ring arcs, in the same order. */
export function SubscoreRows({ breakdown }: { breakdown: Breakdown }) {
  const { c, radius } = useTheme();
  return (
    <View style={{ gap: 10 }}>
      {SUBSCORES.map((s) => {
        const v = Math.round(breakdown[s.key] ?? 0);
        return (
          <View key={s.key} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <Text variant="small" tone="ink60" style={{ width: 72 }}>{s.label()}</Text>
            <View style={{ flex: 1, height: 6, borderRadius: radius.round, backgroundColor: c.inset }}>
              <View style={{ width: `${v}%`, height: 6, borderRadius: radius.round, backgroundColor: c[s.color] }} />
            </View>
            <Text variant="number" style={{ width: 28, textAlign: 'right' }}>{v}</Text>
          </View>
        );
      })}
    </View>
  );
}

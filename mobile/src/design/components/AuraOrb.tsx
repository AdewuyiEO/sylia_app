import React, { useEffect } from 'react';
import { Pressable, View, StyleSheet, AccessibilityInfo } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
  cancelAnimation,
} from 'react-native-reanimated';
import Svg, { Defs, RadialGradient, Stop, Circle } from 'react-native-svg';
import { auraMaterial } from '../tokens';

/**
 * The Aura orb — the ONE AI signifier in the product (no sparkles anywhere).
 * Iridescent, breathing when idle. This is a pragmatic RN approximation using
 * a rotating multi-stop gradient; the production-grade version uses a Skia
 * SweepGradient per tokens (auraMaterial). Honours Reduce Motion.
 */
export function AuraOrb({ size = 44, onPress }: { size?: number; onPress?: () => void }) {
  const rot = useSharedValue(0);
  const scale = useSharedValue(1);

  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled().then((reduce) => {
      if (!mounted || reduce) return;
      rot.value = withRepeat(withTiming(360, { duration: auraMaterial.rotationMs, easing: Easing.linear }), -1, false);
      scale.value = withRepeat(withTiming(1.04, { duration: 1500, easing: Easing.inOut(Easing.ease) }), -1, true);
    });
    return () => {
      mounted = false;
      cancelAnimation(rot);
      cancelAnimation(scale);
    };
  }, []);

  const aStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rot.value}deg` }, { scale: scale.value }],
  }));

  const stops = auraMaterial.stops;

  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel="Aura" hitSlop={8}>
      <Animated.View style={[{ width: size, height: size }, aStyle, styles.shadow]}>
        <Svg width={size} height={size} viewBox="0 0 100 100">
          <Defs>
            {/* approximated iridescence via overlapping radial gradients */}
            <RadialGradient id="a" cx="35%" cy="30%" r="80%">
              <Stop offset="0%" stopColor={stops[2]} />
              <Stop offset="45%" stopColor={stops[1]} />
              <Stop offset="100%" stopColor={stops[0]} />
            </RadialGradient>
            <RadialGradient id="b" cx="70%" cy="75%" r="70%">
              <Stop offset="0%" stopColor={stops[3]} stopOpacity={0.9} />
              <Stop offset="100%" stopColor={stops[4]} stopOpacity={0} />
            </RadialGradient>
          </Defs>
          <Circle cx="50" cy="50" r="50" fill="url(#a)" />
          <Circle cx="50" cy="50" r="50" fill="url(#b)" />
          {/* specular highlight */}
          <Circle cx="36" cy="30" r="14" fill="rgba(255,255,255,0.5)" />
        </Svg>
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shadow: {
    borderRadius: 999,
    shadowColor: '#14141A',
    shadowOpacity: 0.16,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
});

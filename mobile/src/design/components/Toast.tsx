import React, { useEffect } from 'react';
import { Pressable, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme';
import { Text } from './Text';

export interface ToastData {
  message: string;
  action?: { label: string; onPress: () => void };
}

/** One at a time, 12px above the tab bar, 3s auto-dismiss. */
export function Toast({ data, onClear }: { data: ToastData | null; onClear: () => void }) {
  const { c, radius, layout, motion } = useTheme();
  const insets = useSafeAreaInsets();
  const opacity = useSharedValue(0);

  useEffect(() => {
    if (!data) return;
    opacity.value = withTiming(1, { duration: motion.tap });
    const id = setTimeout(() => {
      opacity.value = withTiming(0, { duration: motion.tap });
      setTimeout(onClear, motion.tap);
    }, motion.toastMs);
    return () => clearTimeout(id);
  }, [data]);

  const aStyle = useAnimatedStyle(() => ({ opacity: opacity.value }));
  if (!data) return null;

  return (
    <Animated.View
      accessibilityLiveRegion="polite"
      accessibilityRole="alert"
      style={[styles.wrap, { bottom: insets.bottom + layout.tabBarHeight + 12, backgroundColor: c.ink, borderRadius: radius.btn }, aStyle]}
    >
      <Text style={{ color: c.bg, flex: 1 }}>{data.message}</Text>
      {data.action ? (
        <Pressable onPress={() => { data.action!.onPress(); onClear(); }} hitSlop={10} accessibilityRole="button">
          <Text variant="bodyStrong" style={{ color: c.bg }}>{data.action.label}</Text>
        </Pressable>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 16, right: 16, minHeight: 52, paddingHorizontal: 16, paddingVertical: 12,
          flexDirection: 'row', alignItems: 'center', gap: 12 },
});

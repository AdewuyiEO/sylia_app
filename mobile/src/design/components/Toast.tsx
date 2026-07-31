import React, { useEffect } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withTiming, withSpring } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme';

export interface ToastData {
  message: string;
  undo?: () => void;
}

/**
 * Single-slot toast. A new toast replaces, never stacks (spec). Anchored above
 * the tab bar. Auto-dismisses at 4s unless the caller clears it.
 */
export function Toast({ data, onClear }: { data: ToastData | null; onClear: () => void }) {
  const { c, radius, type } = useTheme();
  const insets = useSafeAreaInsets();
  const y = useSharedValue(200);

  useEffect(() => {
    if (data) {
      y.value = withSpring(0, { damping: 22, stiffness: 260 });
      const t = setTimeout(() => {
        y.value = withTiming(200, { duration: 260 });
        setTimeout(onClear, 260);
      }, 4200);
      return () => clearTimeout(t);
    } else {
      y.value = withTiming(200, { duration: 200 });
    }
  }, [data]);

  const aStyle = useAnimatedStyle(() => ({ transform: [{ translateY: y.value }] }));
  if (!data) return null;

  return (
    <Animated.View
      pointerEvents="box-none"
      style={[styles.wrap, { bottom: insets.bottom + 64 + 12 }, aStyle]}
    >
      <View style={[styles.toast, { backgroundColor: c.ink, borderRadius: radius.control }]}>
        <Text style={{ ...type.body, color: c.paper, flex: 1 }}>{data.message}</Text>
        {data.undo && (
          <Pressable
            onPress={() => {
              data.undo!();
              onClear();
            }}
            hitSlop={10}
          >
            <Text style={{ ...type.body, color: c.signal, fontWeight: '600' }}>Undo</Text>
          </Pressable>
        )}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 16, right: 16 },
  toast: {
    minHeight: 56,
    paddingHorizontal: 18,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
});

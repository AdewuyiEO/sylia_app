import React from 'react';
import { Pressable, Text, ActivityIndicator, StyleSheet, ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { useTheme } from '../theme';

type Variant = 'primary' | 'signal' | 'secondary' | 'ghost';

interface Props {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  fill?: boolean; // stretch to container width
}

export function Button({ label, onPress, variant = 'primary', disabled, loading, style, fill }: Props) {
  const { c, radius } = useTheme();
  const scale = useSharedValue(1);
  const aStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  const palette: Record<Variant, { bg: string; fg: string; border?: string }> = {
    primary: { bg: c.ink, fg: c.paper },
    signal: { bg: c.signal, fg: '#FFFFFF' },
    secondary: { bg: 'transparent', fg: c.ink, border: c.mist },
    ghost: { bg: 'transparent', fg: c.slate },
  };
  const p = palette[variant];

  return (
    <Animated.View style={[fill && { flex: 1 }, aStyle]}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: !!disabled }}
        disabled={disabled || loading}
        onPressIn={() => {
          scale.value = withTiming(0.97, { duration: 120 });
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }}
        onPressOut={() => (scale.value = withTiming(1, { duration: 120 }))}
        onPress={onPress}
        style={[
          styles.base,
          { backgroundColor: p.bg, borderRadius: radius.control, opacity: disabled ? 0.38 : 1 },
          p.border ? { borderWidth: 1, borderColor: p.border } : null,
          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator color={p.fg} />
        ) : (
          <Text style={[styles.label, { color: p.fg }]}>{label}</Text>
        )}
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  base: { height: 52, minWidth: 88, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center' },
  label: { fontFamily: 'Switzer-Variable', fontSize: 17, fontWeight: '600' },
});

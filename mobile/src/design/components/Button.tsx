import React from 'react';
import { Pressable, ActivityIndicator, StyleSheet, type ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme';
import { Text } from './Text';

/** primary = ember (one per screen) · secondary = outline · tertiary = olive tint · ghost = text */
type Variant = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'danger';

interface Props {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  icon?: React.ReactNode;
  accessibilityHint?: string;
}

export function Button({ label, onPress, variant = 'primary', disabled, loading, style, icon, accessibilityHint }: Props) {
  const { c, radius, layout } = useTheme();
  const look = {
    primary: { bg: c.action, fg: c.onAction, border: undefined },
    secondary: { bg: 'transparent', fg: c.ink, border: c.hair },
    tertiary: { bg: c.brandTint, fg: c.brand, border: undefined },
    ghost: { bg: 'transparent', fg: c.ink60, border: undefined },
    danger: { bg: 'transparent', fg: c.critical, border: c.hair },
  }[variant];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!disabled, busy: !!loading }}
      disabled={disabled || loading}
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress?.();
      }}
      style={({ pressed }) => [
        styles.base,
        {
          height: variant === 'ghost' ? layout.minTap : layout.buttonHeight,
          backgroundColor: look.bg,
          borderRadius: radius.btn,
          opacity: disabled ? 0.4 : pressed ? 0.85 : 1,
        },
        look.border ? { borderWidth: 1, borderColor: look.border } : null,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={look.fg} />
      ) : (
        <>
          {icon}
          <Text variant="h3" style={{ color: look.fg, fontSize: 16 }}>{label}</Text>
        </>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { flexDirection: 'row', gap: 8, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center', alignSelf: 'stretch' },
});

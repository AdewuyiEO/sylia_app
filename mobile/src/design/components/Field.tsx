import React, { useState } from 'react';
import { TextInput, View, type TextInputProps } from 'react-native';
import { useTheme } from '../theme';
import { Text } from './Text';

/** Rest · focus (olive ring) · error (ember border + message below). */
export function Field({ label, error, hint, style, ...rest }: TextInputProps & { label?: string; error?: string | null; hint?: string }) {
  const { c, radius, layout, type } = useTheme();
  const [focused, setFocused] = useState(false);
  const border = error ? c.action : focused ? c.brand : c.hair;
  return (
    <View style={{ gap: 6 }}>
      {label ? <Text variant="label" tone="ink60">{label}</Text> : null}
      <TextInput
        placeholderTextColor={c.ink40}
        {...rest}
        accessibilityLabel={rest.accessibilityLabel ?? label ?? rest.placeholder}
        onFocus={(e) => { setFocused(true); rest.onFocus?.(e); }}
        onBlur={(e) => { setFocused(false); rest.onBlur?.(e); }}
        style={[type.body, {
          minHeight: layout.fieldHeight, paddingHorizontal: 14, paddingVertical: 12,
          color: c.ink, backgroundColor: c.surface, borderRadius: radius.btn,
          borderWidth: focused || error ? 2 : 1, borderColor: border,
        }, style]}
      />
      {error ? <Text variant="small" tone="action">{error}</Text> : hint ? <Text variant="small" tone="ink60">{hint}</Text> : null}
    </View>
  );
}

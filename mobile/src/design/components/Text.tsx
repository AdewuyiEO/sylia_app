import React from 'react';
import { Text as RNText, type TextProps } from 'react-native';
import { useTheme } from '../theme';
import type { type as typeTokens } from '../tokens';

type Variant = keyof typeof typeTokens;
type Tone = 'ink' | 'ink60' | 'ink40' | 'brand' | 'action' | 'critical' | 'onAction';

/** All copy goes through here so type and colour always come from tokens. */
export function Text({ variant = 'body', tone = 'ink', style, ...rest }: TextProps & { variant?: Variant; tone?: Tone }) {
  const { c, type } = useTheme();
  return <RNText {...rest} style={[type[variant] as object, { color: c[tone] }, style]} />;
}

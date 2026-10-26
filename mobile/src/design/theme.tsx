/**
 * Theme provider. Exposes the active colour set (Olive Grove light / Earth Riches
 * dark) plus the static token groups. Every component reads colours through
 * useTheme(), so dark mode is a token swap.
 */
import React, { createContext, useContext, useMemo } from 'react';
import { useColorScheme } from 'react-native';
import { color, type, space, layout, radius, motion } from './tokens';

export type ColorSet = { [K in keyof typeof color.light]: string };

export interface Theme {
  c: ColorSet;
  scheme: 'light' | 'dark';
  type: typeof type;
  space: typeof space;
  layout: typeof layout;
  radius: typeof radius;
  motion: typeof motion;
}

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme() === 'dark' ? 'dark' : 'light';
  const theme = useMemo<Theme>(
    () => ({ c: color[scheme], scheme, type, space, layout, radius, motion }),
    [scheme],
  );
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const t = useContext(ThemeContext);
  if (!t) throw new Error('useTheme must be used within <ThemeProvider>');
  return t;
}

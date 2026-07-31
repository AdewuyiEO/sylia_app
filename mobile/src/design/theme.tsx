/**
 * Theme provider. Exposes the active colour set (light/dark) plus the static
 * token groups. Every component reads colours through useTheme() so dark mode
 * is free and `signal` can swap to its dark-safe variant.
 */

import React, { createContext, useContext } from 'react';
import { useColorScheme } from 'react-native';
import { color, type, space, layout, radius, motion, component } from './tokens';

// Widen the literal hex types so light and dark are the same shape (both are
// { paper: string, chalk: string, ... }) and `color[scheme]` type-checks.
type ColorSet = { [K in keyof typeof color.light]: string };

interface Theme {
  c: ColorSet;
  scheme: 'light' | 'dark';
  type: typeof type;
  space: typeof space;
  layout: typeof layout;
  radius: typeof radius;
  motion: typeof motion;
  component: typeof component;
}

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme() === 'dark' ? 'dark' : 'light';
  const theme: Theme = {
    c: color[scheme],
    scheme,
    type,
    space,
    layout,
    radius,
    motion,
    component,
  };
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const t = useContext(ThemeContext);
  if (!t) throw new Error('useTheme must be used within <ThemeProvider>');
  return t;
}

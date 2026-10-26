/**
 * Sylia design tokens — Design System v2 (Olive Grove / Earth Riches / Desert Sunset).
 *
 * Rules encoded here:
 *  - Bone is the base, linen for anything raised, olive for structure.
 *  - Ember is for actions only: one ember element per screen.
 *  - Dark mode (Earth Riches) is not an inversion: browns stay brown.
 *  - Components read semantic names, never hex values.
 */

export const color = {
  light: {
    bg: '#FBF9F5',        // bone — app background, sheets
    surface: '#FFFFFF',   // paper — cards, fields
    inset: '#EFE7DA',     // linen 50 — chips, skeletons, inset rows
    mat: '#D9C7B0',       // linen — photo mats, empty tiles
    ink: '#241F1B',       // body copy, headings
    ink60: '#6B6259',     // secondary copy
    ink40: '#9A9089',     // tertiary, placeholders
    hair: '#E4DED3',      // borders, dividers
    brand: '#556B2F',     // olive — structure, selected state, progress
    brandTint: '#E9EDE0',
    action: '#BC4F26',    // ember — primary button, active tab, links
    actionTint: '#FBEADF',
    onAction: '#FFFFFF',
    inactive: '#8A7B6A',  // taupe — inactive tab icons, disabled (never copy)
    critical: '#A33A2A',
    // quartered score ring, clockwise from top
    fit: '#556B2F',
    palette: '#BC4F26',
    occasion: '#C4A882',
    weather: '#8A9A5B',
    scrim: 'rgba(36,31,27,0.4)',
  },
  dark: {
    bg: '#241C14',        // espresso
    surface: '#3A2D22',   // walnut — cards, offline banner
    inset: '#4A3A2C',
    mat: '#5C3D2E',
    ink: '#F2EAE0',
    ink60: '#B8A794',     // cocoa taupe
    ink40: '#8A7B6A',
    hair: '#4A3A2C',
    brand: '#8A9A5B',     // sage stands in for olive on dark
    brandTint: '#33402180',
    action: '#E2703F',    // ember light
    actionTint: '#5A2E1B',
    onAction: '#241C14',
    inactive: '#8A7B6A',
    critical: '#F08A70',
    fit: '#8A9A5B',
    palette: '#E2703F',
    occasion: '#C4A882',
    weather: '#D9C7B0',
    scrim: 'rgba(0,0,0,0.5)',
  },
} as const;

export const font = {
  display: 'Fraunces_600SemiBold',
  ui: 'Inter_400Regular',
  uiMedium: 'Inter_500Medium',
  uiSemi: 'Inter_600SemiBold',
} as const;

type TypeStyle = {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing?: number;
  textTransform?: 'uppercase';
  fontVariant?: ('tabular-nums')[];
};

/** Fraunces never goes below 20px; small caps and labels are always Inter. */
export const type = {
  display: { fontFamily: font.display, fontSize: 34, lineHeight: 38 },
  h1: { fontFamily: font.display, fontSize: 28, lineHeight: 32 },
  h2: { fontFamily: font.display, fontSize: 22, lineHeight: 27 },
  h3: { fontFamily: font.uiSemi, fontSize: 17, lineHeight: 22 },
  body: { fontFamily: font.ui, fontSize: 15, lineHeight: 22 },
  bodyStrong: { fontFamily: font.uiSemi, fontSize: 15, lineHeight: 22 },
  small: { fontFamily: font.ui, fontSize: 13, lineHeight: 18 },
  label: { fontFamily: font.uiSemi, fontSize: 11, lineHeight: 14, letterSpacing: 1.4, textTransform: 'uppercase' },
  tab: { fontFamily: font.uiMedium, fontSize: 10, lineHeight: 12 },
  number: { fontFamily: font.uiSemi, fontSize: 15, lineHeight: 20, fontVariant: ['tabular-nums'] },
} satisfies Record<string, TypeStyle>;

/** 8pt grid, 20px screen gutters. */
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 32, xxxl: 48 } as const;

export const layout = {
  gutter: 20,
  minTap: 44,
  buttonHeight: 48,
  fieldHeight: 50,
  chipHeight: 30,
  tabBarHeight: 56,
} as const;

export const radius = { chip: 15, btn: 10, card: 14, sheet: 28, round: 999 } as const;

export const motion = {
  tap: 200,
  screen: 400,
  ring: 600,          // the score ring is the only entrance animation in the app
  toastMs: 3000,
} as const;

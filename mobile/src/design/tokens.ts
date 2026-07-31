/**
 * Aura — AI Stylist
 * Design tokens. Single source of truth for React Native.
 *
 * Rules encoded here:
 *  - UI is cool greyscale; garments supply all color.
 *  - Content radius is 4 (photographic), chrome radius is 28 (soft). No in-betweens.
 *  - `signal` is for human intent only. `aura` gradient is for AI presence only.
 */

export const color = {
  light: {
    paper: '#FFFFFF',
    chalk: '#F4F4F7',
    mist: '#E7E7EC',
    ash: '#B9B9C4',
    slate: '#74747F',
    graphite: '#3A3A44',
    ink: '#14141A',

    signal: '#E4005B',
    signalPress: '#C10049',
    signalTint: '#FDE7EF',

    positive: '#0E7C66',
    caution: '#B5730B',
    critical: '#B3261E',

    scrim: 'rgba(20,20,26,0.32)',
    glass: 'rgba(20,20,26,0.44)',
    glassBorder: 'rgba(255,255,255,0.14)',
  },
  dark: {
    paper: '#0B0B0F',       // screen bg (void)
    chalk: '#16161C',       // card / tile bg (carbon)
    mist: '#22222A',        // hairline (basalt)
    ash: '#3C3C47',         // disabled (steel)
    slate: '#8E8E9A',       // secondary text (fog)
    graphite: '#D7D7DE',    // body text (frost)
    ink: '#F7F7FA',         // primary text / inverted fill (snow)

    signal: '#FF3D80',
    signalPress: '#E4005B',
    signalTint: '#2A0E1B',

    positive: '#3BC7A8',
    caution: '#E5A93D',
    critical: '#FF6B5E',

    scrim: 'rgba(0,0,0,0.48)',
    glass: 'rgba(0,0,0,0.52)',
    glassBorder: 'rgba(255,255,255,0.10)',
  },
} as const;

/** The Aura material. Permitted on: the orb, AI loaders, the Pro badge. Nowhere else. */
export const auraMaterial = {
  stops: ['#BFC9FF', '#E4D3FF', '#FFD6E7', '#C9F3EA', '#DCE3FF'],
  locations: [0, 0.28, 0.52, 0.76, 1],
  rotationMs: 8000,
  glossMs: 3200,
  glossOpacity: 0.22,
  glossWidth: 0.18,
  blur: 8,
} as const;

export const font = {
  display: 'InstrumentSerif-Regular',
  displayItalic: 'InstrumentSerif-Italic',
  ui: 'Switzer-Variable',
  mono: 'GeistMono-Regular',
} as const;

type TypeStyle = {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  fontWeight: '400' | '500' | '600' | '700';
  textTransform?: 'uppercase';
};

export const type: Record<string, TypeStyle> = {
  displayXL:  { fontFamily: font.display, fontSize: 40, lineHeight: 40, letterSpacing: -0.8, fontWeight: '400' },
  displayL:   { fontFamily: font.display, fontSize: 32, lineHeight: 34, letterSpacing: -0.64, fontWeight: '400' },
  title:      { fontFamily: font.ui, fontSize: 24, lineHeight: 28, letterSpacing: -0.24, fontWeight: '600' },
  heading:    { fontFamily: font.ui, fontSize: 20, lineHeight: 26, letterSpacing: -0.2, fontWeight: '600' },
  bodyL:      { fontFamily: font.ui, fontSize: 17, lineHeight: 24, letterSpacing: 0, fontWeight: '400' },
  body:       { fontFamily: font.ui, fontSize: 15, lineHeight: 22, letterSpacing: 0, fontWeight: '400' },
  bodyStrong: { fontFamily: font.ui, fontSize: 15, lineHeight: 22, letterSpacing: 0, fontWeight: '600' },
  caption:    { fontFamily: font.ui, fontSize: 13, lineHeight: 18, letterSpacing: 0, fontWeight: '400' },
  label:      { fontFamily: font.mono, fontSize: 13, lineHeight: 18, letterSpacing: 0.26, fontWeight: '500' },
  micro:      { fontFamily: font.mono, fontSize: 11, lineHeight: 12, letterSpacing: 0.66, fontWeight: '500', textTransform: 'uppercase' },
};

/** Base unit 4. Use tokens, never raw numbers. */
export const space = {
  s1: 4, s2: 8, s3: 12, s4: 16, s5: 20, s6: 24,
  s7: 32, s8: 40, s9: 48, s10: 56, s11: 72, s12: 96,
} as const;

export const layout = {
  gutter: 20,
  cardPadding: 16,
  sectionGap: 32,
  headerHeight: 52,
  tabBarHeight: 49,
  minTapTarget: 44,
  maxBodyChars: 68,
  /** Anchor primary CTAs here, measured up from the bottom safe area. */
  thumbAnchor: 148,
} as const;

export const radius = {
  sharp: 0,
  content: 4,   // ALL garment / outfit / product imagery
  control: 8,   // buttons, inputs, segmented
  chip: 16,
  sheet: 28,    // top corners only
  round: 999,
} as const;

/** Only two shadows exist. Everything else separates with a 1px hairline. */
export const elevation = {
  sheet: {
    shadowColor: '#14141A', shadowOpacity: 0.12,
    shadowRadius: 32, shadowOffset: { width: 0, height: -8 }, elevation: 16,
  },
  orb: {
    shadowColor: '#14141A', shadowOpacity: 0.16,
    shadowRadius: 16, shadowOffset: { width: 0, height: 4 }, elevation: 8,
  },
} as const;

export const motion = {
  tap: { duration: 120, easing: [0.2, 0, 0, 1] },
  micro: { duration: 180, easing: [0.2, 0, 0, 1] },
  screen: { duration: 320, easing: [0.2, 0, 0, 1] },
  reveal: { duration: 420, stagger: 60, easing: [0.16, 1, 0.3, 1] },
  sheetSpring: { damping: 30, stiffness: 300, mass: 1 },
  pressScale: 0.97,
} as const;

export const component = {
  button: {
    primary:   { height: 52, radius: radius.control, fill: 'ink', label: 'paper' },
    signal:    { height: 52, radius: radius.control, fill: 'signal', label: 'paper' },
    secondary: { height: 52, radius: radius.control, fill: 'transparent', border: 'mist', label: 'ink' },
    ghost:     { height: 44, radius: radius.control, fill: 'transparent', label: 'slate' },
    icon:      { size: 44, glyph: 24, radius: radius.round },
    small:     { height: 36, radius: radius.control },
    minWidth: 88,
    paddingH: space.s5,
    disabledOpacity: 0.38,
  },
  chip: { height: 32, radius: radius.chip, paddingH: 12 },
  sheet: { radius: radius.sheet, grabber: { w: 36, h: 4 }, snapPoints: [0.45, 0.9] },
  toast: { height: 56, radius: radius.control, autoDismissMs: 4000 },
  input: { height: 52, radius: radius.control, fill: 'chalk' },
  orb: { tabSize: 44, heroSize: 88, breatheScale: 0.04, breatheMs: 3000 },
  grid: {
    closet3: { tile: 110, gap: 8 },
    closet2: { tile: 172, gap: 8 },
    closet4: { tile: 81, gap: 8 },
    outfit2: { w: 171, h: 228 },
    outfitRail: { w: 140, h: 187 },
    hero: { w: 350, h: 466 },
  },
} as const;

/** Feedback signal weights. Wear is ground truth; everything else is aspirational. */
export const signalWeight = {
  wear: 10,
  reasonChip: 4,
  save: 3,
  rate: 1,
  dwell: 0.5,
} as const;

export const limits = {
  reasonPillChars: 96,
  chatProseSentences: 2,
  freeGenerationsPerDay: 3,
  freeWardrobeItems: 60,
  freeCollections: 3,
  generationHardCapMs: 6000,
  undoWindowMs: 10000,
} as const;

/**
 * Aura — garment & colour taxonomy.
 * The single source of truth for what a garment IS: which slot it fills,
 * how warm/formal it is by default, what it's made of. The art layer and
 * the engine both read from here so they never drift.
 */

import type { ColorId, GarmentTypeId, Material, Slot } from './types';

export interface ColorDef {
  id: ColorId;
  hex: string;
  name: string;
  /** neutrals combine freely; accents are used one-at-a-time. */
  neutral: boolean;
}

export const COLORS: ColorDef[] = [
  { id: 'ink',   hex: '#22232A', name: 'Ink',   neutral: true },
  { id: 'ecru',  hex: '#E7DFCE', name: 'Ecru',  neutral: true },
  { id: 'bone',  hex: '#D9D2C5', name: 'Bone',  neutral: true },
  { id: 'slate', hex: '#5E6B78', name: 'Slate', neutral: true },
  { id: 'navy',  hex: '#2C3648', name: 'Navy',  neutral: true },
  { id: 'stone', hex: '#9A958C', name: 'Stone', neutral: true },
  { id: 'sand',  hex: '#C9A87C', name: 'Sand',  neutral: true },
  { id: 'brown', hex: '#6E4C34', name: 'Brown', neutral: true },
  { id: 'rust',  hex: '#B4603C', name: 'Rust',  neutral: false },
  { id: 'olive', hex: '#6B6B4E', name: 'Olive', neutral: false },
  { id: 'sage',  hex: '#8A9A82', name: 'Sage',  neutral: false },
  { id: 'clay',  hex: '#A9694E', name: 'Clay',  neutral: false },
];

const COLOR_MAP = new Map(COLORS.map((c) => [c.id, c]));
export const colorOf = (id: ColorId): ColorDef => COLOR_MAP.get(id) ?? COLORS[0];

export interface TypeDef {
  slot: Slot;
  label: string;
  warmth: number;    // 0..4 default
  formality: number; // 1..5 default
  material: Material; // default material
}

export const TYPES: Record<GarmentTypeId, TypeDef> = {
  tee:      { slot: 'top',    label: 'T-shirt',  warmth: 1, formality: 1, material: 'cotton' },
  shirt:    { slot: 'top',    label: 'Shirt',    warmth: 2, formality: 3, material: 'linen'  },
  knit:     { slot: 'top',    label: 'Knit',     warmth: 3, formality: 3, material: 'wool'   },
  blouse:   { slot: 'top',    label: 'Blouse',   warmth: 2, formality: 3, material: 'silk'   },
  trousers: { slot: 'bottom', label: 'Trousers', warmth: 2, formality: 3, material: 'wool'   },
  jeans:    { slot: 'bottom', label: 'Jeans',    warmth: 2, formality: 2, material: 'denim'  },
  shorts:   { slot: 'bottom', label: 'Shorts',   warmth: 1, formality: 1, material: 'cotton' },
  skirt:    { slot: 'bottom', label: 'Skirt',    warmth: 1, formality: 3, material: 'cotton' },
  dress:    { slot: 'dress',  label: 'Dress',    warmth: 1, formality: 3, material: 'linen'  },
  jacket:   { slot: 'outer',  label: 'Jacket',   warmth: 3, formality: 3, material: 'cotton' },
  blazer:   { slot: 'outer',  label: 'Blazer',   warmth: 3, formality: 4, material: 'wool'   },
  coat:     { slot: 'outer',  label: 'Coat',     warmth: 4, formality: 4, material: 'wool'   },
  sneaker:  { slot: 'shoes',  label: 'Sneakers', warmth: 2, formality: 2, material: 'leather'},
  loafer:   { slot: 'shoes',  label: 'Loafers',  warmth: 2, formality: 3, material: 'leather'},
  boot:     { slot: 'shoes',  label: 'Boots',    warmth: 3, formality: 3, material: 'leather'},
  belt:     { slot: 'acc',    label: 'Belt',     warmth: 0, formality: 2, material: 'leather'},
};

export const typeOf = (t: GarmentTypeId): TypeDef => TYPES[t];
export const slotOf = (t: GarmentTypeId): Slot => TYPES[t].slot;

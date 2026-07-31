/**
 * Aura — domain types.
 * Pure TypeScript. No React, no platform APIs. The vocabulary every
 * other layer speaks. Testable with plain node.
 */

export type Slot = 'top' | 'bottom' | 'dress' | 'outer' | 'shoes' | 'acc';

export type GarmentTypeId =
  | 'tee' | 'shirt' | 'knit' | 'blouse'
  | 'trousers' | 'jeans' | 'shorts' | 'skirt'
  | 'dress'
  | 'jacket' | 'blazer' | 'coat'
  | 'sneaker' | 'loafer' | 'boot'
  | 'belt';

export type ColorId =
  | 'ink' | 'ecru' | 'bone' | 'slate' | 'navy' | 'stone' | 'sand' | 'brown'
  | 'rust' | 'olive' | 'sage' | 'clay';

export type Material =
  | 'cotton' | 'linen' | 'wool' | 'silk' | 'denim' | 'leather';

export type GarmentStatus = 'active' | 'laundry' | 'archived' | 'processing';

export type TagSource = 'ai' | 'user';

export interface Tag {
  value: string;
  source: TagSource;
  confidence: number; // 0..1
}

export interface Garment {
  id: string;
  type: GarmentTypeId;
  color: ColorId;
  material: Material;
  /** 0 (none) .. 4 (heaviest). Drives weather matching. */
  warmth: number;
  /** 1 (casual) .. 5 (black tie). Drives occasion matching. */
  formality: number;
  status: GarmentStatus;
  tags: Tag[];
  confirmed: boolean; // has the user verified the AI's tags?
  wearCount: number;
  lastWorn: number | null; // epoch ms
  price?: number;
  brand?: string;
  size?: string;
  imageUrl?: string; // remote cut-out; falls back to schematic art
  addedAt: number;
}

export interface Outfit {
  id: string;
  garmentIds: string[];
  reason: string;
  source: 'drop' | 'generated' | 'manual' | 'mirror';
  context?: OutfitContext;
  wearCount: number;
  lastWorn: number | null;
  savedAt?: number;
}

export interface OutfitContext {
  tempC: number;
  condition?: string;
  occasion?: string;
  eventId?: string;
}

/** A generated candidate, before it's persisted as an Outfit. */
export interface GeneratedOutfit {
  pieces: Garment[];
  reason: string;
  /** 0..1, for internal ranking / the "match" chip. Never shown as a % for taste. */
  score: number;
  /** debug/telemetry */
  meta: {
    harmony: number;
    avgFormality: number;
    tempC: number;
    targetFormality: number;
  };
}

export interface GenerateOptions {
  tempC?: number;
  formality?: number;   // 1..5 target
  occasion?: string;
  palette?: ColorId | null; // require this colour to lead
  pins?: string[];      // garment ids that MUST appear
  count?: number;       // how many looks to return (default 3)
}

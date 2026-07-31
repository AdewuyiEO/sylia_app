/**
 * Colour-harmony scoring for an outfit.
 * The model is deliberately simple and legible (it has to justify itself to
 * the user via the reason string): neutrals combine freely; one accent is
 * ideal; multiple clashing accents are penalised; monochrome always works.
 */

import { colorOf } from '../garments';
import type { ColorId } from '../types';

/** Returns 0..1. Higher is more harmonious. */
export function harmonyScore(colors: ColorId[]): number {
  if (colors.length === 0) return 0;
  const defs = colors.map(colorOf);
  const accents = defs.filter((c) => !c.neutral);
  const distinct = new Set(colors);

  if (distinct.size === 1) return 1.0;                 // monochrome
  if (accents.length === 0) return 0.9;                // all neutral — always safe
  if (accents.length === 1) return 0.8;                // neutrals + one accent — ideal
  // two of the SAME accent still reads intentional
  if (accents.length === 2 && accents[0].id === accents[1].id) return 0.6;
  return 0.3;                                          // multiple clashing accents
}

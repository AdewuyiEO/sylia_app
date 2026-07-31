/**
 * Reason generation. Spec rule: no look ships without a concrete, evidence-
 * based reason (≤96 chars). Grammar = [constraint satisfied] + [evidence].
 * We never say "our algorithm" or "based on your preferences" — too vague to
 * be evidence. We name the specific input that drove the choice.
 */

import { slotOf } from '../garments';
import type { Garment } from '../types';

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const LIGHT: Garment['material'][] = ['linen', 'cotton', 'silk'];

export interface ReasonInput {
  pieces: Garment[];
  tempC: number;
  targetFormality: number;
  avgFormality: number;
  harmony: number;
}

export function reasonFor(r: ReasonInput): string {
  const { pieces, tempC, targetFormality, avgFormality, harmony } = r;
  const hero = pieces.find((p) => ['top', 'dress'].includes(slotOf(p.type)));

  // hot day + a breathable fabric
  if (tempC >= 28) {
    const light = pieces.find((p) => LIGHT.includes(p.material));
    if (light) return clamp(`${cap(light.material)} keeps you cool and it's ${tempC}°C today`);
  }
  // cold day + something warm
  if (tempC < 12) {
    const warm = pieces.find((p) => p.warmth >= 3);
    if (warm) return clamp(`${cap(warm.material)} for ${tempC}°C — you'll stay warm`);
  }
  // formal target met
  if (targetFormality >= 4 && avgFormality >= 3.5) {
    return clamp('Sharp enough for the occasion, built from pieces you own');
  }
  // a proven, well-worn hero
  if (hero && hero.wearCount >= 4) {
    return clamp(`You've worn this ${hero.wearCount} times — it works with the rest`);
  }
  // clean neutral pairing
  if (harmony >= 0.9) return clamp('A quiet, all-neutral pairing that always lands');

  return clamp(`Balanced for ${tempC}°C and the day ahead`);
}

function clamp(s: string, max = 96): string {
  return s.length <= max ? s : s.slice(0, max - 1).trimEnd() + '…';
}

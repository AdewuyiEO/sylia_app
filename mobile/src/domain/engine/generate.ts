/**
 * Aura — outfit generation engine.
 *
 * A pure function: (garments, options) -> ranked looks. No globals, no I/O,
 * no randomness that can't be seeded. This is the on-device floor that makes
 * Today render with zero network latency; a server re-ranker can improve the
 * ORDER later but this always produces something wearable.
 *
 * Scoring = colour harmony (0.5) + formality fit (0.3) + wear-recency (0.2),
 * with a tiny jitter for day-to-day variety.
 */

import { slotOf } from '../garments';
import { harmonyScore } from './harmony';
import { reasonFor } from './reason';
import type { Garment, GeneratedOutfit, GenerateOptions, Slot } from '../types';

const RECENCY_WINDOW = 30 * 864e5; // 30 days in ms

/** Allowed garment-warmth band for a temperature (°C). */
export function tempToWarmth(tempC: number): number[] {
  if (tempC >= 28) return [0, 1, 2];
  if (tempC >= 20) return [1, 2, 3];
  if (tempC >= 12) return [2, 3, 4];
  return [3, 4];
}

export const needsOuter = (tempC: number): boolean => tempC < 16;

/** Deterministic-ish jitter so results vary by day but are reproducible in tests. */
function makeRng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

export function generate(
  items: Garment[],
  opts: GenerateOptions = {},
  seed = Date.now(),
  now = Date.now(),
): GeneratedOutfit[] {
  const tempC = opts.tempC ?? 22;
  const targetFormality = opts.formality ?? 3;
  const palette = opts.palette ?? null;
  const pins = opts.pins ?? [];
  const count = opts.count ?? 3;
  const rng = makeRng(seed);

  const band = tempToWarmth(tempC);
  const active = items.filter((i) => i.status === 'active' && band.includes(i.warmth));
  const bySlot = (slot: Slot) => active.filter((i) => slotOf(i.type) === slot);

  const tops = bySlot('top');
  const bottoms = bySlot('bottom');
  const dresses = bySlot('dress');
  const shoes = bySlot('shoes');
  const outers = bySlot('outer');
  const accs = bySlot('acc');

  // Can't build a look without shoes and (a top+bottom OR a dress).
  const canTopBottom = tops.length > 0 && bottoms.length > 0;
  const canDress = dresses.length > 0;
  if (shoes.length === 0 || (!canTopBottom && !canDress)) return [];

  const pinnedItems = pins
    .map((id) => items.find((i) => i.id === id))
    .filter((x): x is Garment => Boolean(x));

  const combos: GeneratedOutfit[] = [];

  const consider = (pieces: Garment[]) => {
    if (pieces.length === 0) return;
    // every pin must be present
    for (const p of pinnedItems) {
      if (!pieces.some((x) => x.id === p.id)) return;
    }
    const colors = pieces.map((p) => p.color);
    if (palette && !colors.includes(palette)) return;

    const harmony = harmonyScore(colors);
    const avgFormality = pieces.reduce((a, p) => a + p.formality, 0) / pieces.length;
    const formFit = 1 - Math.min(1, Math.abs(avgFormality - targetFormality) / 3);
    const recency =
      pieces.reduce((a, p) => {
        const r = p.lastWorn ? Math.min(1, (now - p.lastWorn) / RECENCY_WINDOW) : 1;
        return a + r;
      }, 0) / pieces.length;

    const score = harmony * 0.5 + formFit * 0.3 + recency * 0.2 + rng() * 0.04;
    const reason = reasonFor({ pieces, tempC, targetFormality, avgFormality, harmony });
    combos.push({
      pieces,
      reason,
      score,
      meta: { harmony, avgFormality, tempC, targetFormality },
    });
  };

  const pick = <T,>(arr: T[]): T => arr[Math.floor(rng() * arr.length)];

  // top + bottom looks
  for (const t of tops) {
    for (const b of bottoms) {
      const pieces = [t, b, pick(shoes)];
      if (needsOuter(tempC) && outers.length) pieces.push(pick(outers));
      if (accs.length && rng() < 0.5) pieces.push(accs[0]);
      consider(pieces);
    }
  }
  // dresses
  for (const d of dresses) {
    const pieces = [d, pick(shoes)];
    if (needsOuter(tempC) && outers.length) pieces.push(outers[0]);
    consider(pieces);
  }

  combos.sort((a, b) => b.score - a.score);

  // de-duplicate by the top/bottom/dress signature, keep the best `count`
  const seen = new Set<string>();
  const out: GeneratedOutfit[] = [];
  for (const c of combos) {
    const sig = c.pieces
      .filter((p) => ['top', 'bottom', 'dress'].includes(slotOf(p.type)))
      .map((p) => p.id)
      .sort()
      .join('|');
    if (seen.has(sig)) continue;
    seen.add(sig);
    out.push(c);
    if (out.length >= count) break;
  }
  return out;
}

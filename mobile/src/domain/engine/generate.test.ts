/**
 * Engine tests. Runnable with plain node (see scripts/run-tests.mjs) — no
 * simulator, no RN. This is the contract the whole app leans on.
 */

import { generate, tempToWarmth, needsOuter } from './generate';
import { harmonyScore } from './harmony';
import { reasonFor } from './reason';
import { TYPES } from '../garments';
import type { Garment, GarmentTypeId, ColorId } from '../types';

// ---- tiny test harness (no jest dependency) ----
let passed = 0;
let failed = 0;
const failures: string[] = [];
function test(name: string, fn: () => void) {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    failures.push(`✗ ${name}\n    ${(e as Error).message}`);
  }
}
function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}
function eq<T>(a: T, b: T, msg?: string) {
  if (a !== b) throw new Error(msg ?? `expected ${b}, got ${a}`);
}

// ---- fixtures ----
let idc = 0;
function g(type: GarmentTypeId, color: ColorId, over: Partial<Garment> = {}): Garment {
  const t = TYPES[type];
  return {
    id: `g${idc++}`,
    type,
    color,
    material: t.material,
    warmth: t.warmth,
    formality: t.formality,
    status: 'active',
    tags: [],
    confirmed: true,
    wearCount: 0,
    lastWorn: null,
    addedAt: Date.now(),
    ...over,
  };
}

function basicCloset(): Garment[] {
  return [
    g('shirt', 'ecru'),
    g('tee', 'ink'),
    g('trousers', 'ink'),
    g('jeans', 'navy'),
    g('sneaker', 'bone'),
    g('loafer', 'brown'),
    g('dress', 'rust'),
    g('jacket', 'navy'),
  ];
}

// ============================ harmony ============================
test('harmony: monochrome is perfect', () => {
  eq(harmonyScore(['ink', 'ink', 'ink']), 1.0);
});
test('harmony: all-neutral is safe', () => {
  eq(harmonyScore(['ink', 'ecru', 'navy']), 0.9);
});
test('harmony: neutrals + one accent is ideal', () => {
  eq(harmonyScore(['ink', 'ecru', 'rust']), 0.8);
});
test('harmony: two clashing accents is penalised', () => {
  assert(harmonyScore(['rust', 'olive', 'ink']) < 0.5, 'clashing accents should score low');
});
test('harmony: empty is zero', () => {
  eq(harmonyScore([]), 0);
});

// ============================ weather ============================
test('weather: hot day allows only light warmth', () => {
  const band = tempToWarmth(31);
  assert(band.includes(0) && band.includes(2) && !band.includes(4), 'hot band wrong');
});
test('weather: cold day requires warm items', () => {
  const band = tempToWarmth(4);
  assert(band.includes(4) && !band.includes(1), 'cold band wrong');
});
test('weather: needsOuter below 16°C', () => {
  assert(needsOuter(8) && !needsOuter(24), 'needsOuter threshold wrong');
});

// ============================ generate: shape ============================
test('generate: returns at most `count` looks', () => {
  const out = generate(basicCloset(), { tempC: 22, count: 3 }, 1);
  assert(out.length <= 3, `got ${out.length}`);
  assert(out.length >= 1, 'should produce at least one look');
});
test('generate: every look has shoes and a top-or-dress', () => {
  const out = generate(basicCloset(), { tempC: 22 }, 2);
  for (const o of out) {
    const slots = o.pieces.map((p) => TYPES[p.type].slot);
    assert(slots.includes('shoes'), 'missing shoes');
    assert(slots.includes('top') || slots.includes('dress'), 'missing top/dress');
  }
});
test('generate: every look carries a non-empty reason ≤96 chars', () => {
  const out = generate(basicCloset(), { tempC: 31 }, 3);
  for (const o of out) {
    assert(o.reason.length > 0, 'empty reason');
    assert(o.reason.length <= 96, `reason too long: ${o.reason.length}`);
  }
});
test('generate: results are de-duplicated by top/bottom signature', () => {
  const out = generate(basicCloset(), { tempC: 22, count: 5 }, 4);
  const sigs = out.map((o) =>
    o.pieces
      .filter((p) => ['top', 'bottom', 'dress'].includes(TYPES[p.type].slot))
      .map((p) => p.id)
      .sort()
      .join('|'),
  );
  eq(new Set(sigs).size, sigs.length, 'duplicate outfits returned');
});

// ============================ generate: constraints ============================
test('generate: respects the warmth band (no coat on a 31°C day)', () => {
  const closet = [...basicCloset(), g('coat', 'stone')]; // coat warmth 4
  const out = generate(closet, { tempC: 31 }, 5);
  for (const o of out) {
    assert(!o.pieces.some((p) => p.type === 'coat'), 'coat leaked into a hot-day look');
  }
});
test('generate: a pinned item appears in every look', () => {
  const closet = basicCloset();
  const pin = closet.find((c) => c.type === 'shirt')!;
  const out = generate(closet, { tempC: 22, pins: [pin.id] }, 6);
  assert(out.length > 0, 'pinning should still yield looks');
  for (const o of out) {
    assert(o.pieces.some((p) => p.id === pin.id), 'pin missing from a look');
  }
});
test('generate: palette filter forces the colour to appear', () => {
  const out = generate(basicCloset(), { tempC: 22, palette: 'navy' }, 7);
  for (const o of out) {
    assert(o.pieces.some((p) => p.color === 'navy'), 'palette colour missing');
  }
});
test('generate: returns [] when there are no shoes', () => {
  const noShoes = basicCloset().filter((c) => TYPES[c.type].slot !== 'shoes');
  eq(generate(noShoes, { tempC: 22 }, 8).length, 0);
});
test('generate: returns [] when there is nothing to wear on top', () => {
  const bottomsOnly = [g('trousers', 'ink'), g('sneaker', 'bone')];
  eq(generate(bottomsOnly, { tempC: 22 }, 9).length, 0);
});
test('generate: laundry/archived items are excluded', () => {
  const closet = basicCloset().map((c) =>
    c.type === 'sneaker' ? { ...c, status: 'laundry' as const } : c,
  );
  // only the brown loafer remains as shoes
  const out = generate(closet, { tempC: 22 }, 10);
  for (const o of out) {
    assert(!o.pieces.some((p) => p.type === 'sneaker'), 'laundry sneaker leaked in');
  }
});
test('generate: cold day adds outerwear when available', () => {
  // jeans/trousers are warmth 2 (excluded at 4°C); a warm bottom is needed.
  const closet = [
    g('knit', 'olive'),
    g('trousers', 'ink', { warmth: 3 }), // heavy wool trousers
    g('boot', 'ink'),
    g('coat', 'stone'),
  ];
  const out = generate(closet, { tempC: 4 }, 11);
  assert(out.length > 0, 'cold-day look should exist');
  assert(out.some((o) => o.pieces.some((p) => TYPES[p.type].slot === 'outer')), 'no outer on a cold day');
});

// ============================ reason ============================
test('reason: hot day + linen mentions staying cool', () => {
  const pieces = [g('shirt', 'ecru'), g('trousers', 'ink'), g('sneaker', 'bone')];
  const r = reasonFor({ pieces, tempC: 31, targetFormality: 3, avgFormality: 3, harmony: 0.9 });
  assert(/cool|31/.test(r), `reason didn't reference heat: "${r}"`);
});
test('reason: formal target produces a "sharp" line', () => {
  const pieces = [g('blazer', 'ink'), g('trousers', 'ink'), g('loafer', 'brown')];
  const r = reasonFor({ pieces, tempC: 20, targetFormality: 5, avgFormality: 4, harmony: 1 });
  assert(/sharp|occasion/i.test(r), `expected a formal reason: "${r}"`);
});

// ============================ determinism ============================
test('generate: same seed → same result (reproducible)', () => {
  const NOW = 1_700_000_000_000;
  idc = 0;
  const c1 = basicCloset();
  idc = 0;
  const c2 = basicCloset(); // identical ids to c1
  const a = generate(c1, { tempC: 22 }, 42, NOW);
  const b = generate(c2, { tempC: 22 }, 42, NOW);
  eq(JSON.stringify(a.map((o) => o.pieces.map((p) => p.id))),
     JSON.stringify(b.map((o) => o.pieces.map((p) => p.id))),
     'engine is not deterministic under a fixed seed');
});

// ---- report ----
console.log(`\nAura engine tests`);
console.log(`${'─'.repeat(40)}`);
if (failures.length) console.log(failures.join('\n') + '\n');
console.log(`${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);

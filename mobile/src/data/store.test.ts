/**
 * Store integration test. Drives the Zustand store exactly as a screen would,
 * proving the vertical slice works: store state -> domain engine -> wear loop
 * -> persistence-shaped mutations. Runs under plain `tsx` (persist falls back
 * to the in-memory storage in persist.ts, so no MMKV/native needed).
 */

import { useStore } from './store';

let passed = 0, failed = 0;
const fails: string[] = [];
function test(name: string, fn: () => void) {
  try { fn(); passed++; } catch (e) { failed++; fails.push(`✗ ${name}\n    ${(e as Error).message}`); }
}
function assert(c: boolean, m: string) { if (!c) throw new Error(m); }

const s = () => useStore.getState();
const reset = () => useStore.setState({
  onboarded: false, items: [], savedOutfits: [], wearLog: [],
  streak: 0, lastWear: null, genUsedToday: 0, genDate: null,
} as any);

test('seedDemo populates a styleable closet', () => {
  reset();
  s().seedDemo();
  assert(s().items.length >= 15, `expected >=15 demo items, got ${s().items.length}`);
  assert(s().activeItems().length >= 15, 'demo items should be active');
});

test('generateLooks returns wearable outfits from the store', () => {
  reset(); s().seedDemo();
  const looks = s().generateLooks({ tempC: 31, formality: 3 });
  assert(looks.length > 0, 'expected at least one look');
  assert(looks.length <= 3, 'default should cap at 3');
  for (const l of looks) {
    assert(l.pieces.length >= 2, 'a look needs at least 2 pieces');
    assert(!!l.reason && l.reason.length <= 96, `reason must be present and ≤96 chars: "${l.reason}"`);
    const slots = l.pieces.map(p => p.type);
    assert(slots.length === new Set(l.pieces.map(p => p.id)).size, 'no duplicate garments in a look');
  }
});

test('addGarment appends and returns the new item', () => {
  reset();
  const before = s().items.length;
  const g = s().addGarment('shirt', 'ecru');
  assert(s().items.length === before + 1, 'item count should increase by 1');
  assert(g.type === 'shirt' && g.color === 'ecru', 'returned garment matches input');
  assert(g.confirmed === false, 'new garment starts unconfirmed (AI-guessed tags)');
});

test('confirmTags flips the guessed→confirmed flag', () => {
  reset();
  const g = s().addGarment('knit', 'olive');
  assert(g.confirmed === false, 'starts unconfirmed');
  s().confirmTags(g.id);
  assert(s().items.find(i => i.id === g.id)!.confirmed === true, 'should be confirmed after');
});

test('wearOutfit logs a wear, bumps counts, starts a streak', () => {
  reset(); s().seedDemo();
  const look = s().generateLooks({ tempC: 31, formality: 3 })[0];
  const heroId = look.pieces[0].id;
  const beforeWears = s().items.find(i => i.id === heroId)!.wearCount;
  s().wearOutfit(look);
  assert(s().wearLog.length === 1, 'one wear event logged');
  assert(s().streak === 1, `streak should be 1, got ${s().streak}`);
  assert(s().items.find(i => i.id === heroId)!.wearCount === beforeWears + 1, 'hero wearCount bumped');
});

test('wearOutfit returns a working undo', () => {
  reset(); s().seedDemo();
  const look = s().generateLooks({ tempC: 31, formality: 3 })[0];
  const heroId = look.pieces[0].id;
  const before = s().items.find(i => i.id === heroId)!.wearCount;
  const undo = s().wearOutfit(look);
  undo();
  assert(s().wearLog.length === 0, 'wear event removed on undo');
  assert(s().items.find(i => i.id === heroId)!.wearCount === before, 'wearCount restored on undo');
});

test('generation quota decrements and floors at zero', () => {
  reset(); s().seedDemo();
  useStore.setState({ genUsedToday: 0, genDate: new Date().toISOString().slice(0, 10) } as any);
  const start = s().looksLeftToday();
  assert(start === 3, `fresh day should have 3 looks, got ${start}`);
  s().consumeGeneration(); s().consumeGeneration(); s().consumeGeneration();
  assert(s().looksLeftToday() === 0, 'should be exhausted');
  s().consumeGeneration();
  assert(s().looksLeftToday() === 0, 'must not go negative');
});

test('setStatus=laundry removes an item from generation', () => {
  reset(); s().seedDemo();
  const shoe = s().items.find(i => ['sneaker','loafer','boot'].includes(i.type))!;
  s().setStatus(shoe.id, 'laundry');
  assert(s().activeItems().every(i => i.id !== shoe.id), 'laundry item excluded from active');
});

console.log('\nAura store integration\n' + '─'.repeat(40));
if (fails.length) console.log(fails.join('\n\n'));
console.log(`${passed} passed, ${failed} failed\n`);
if (failed) (process as any).exit(1);

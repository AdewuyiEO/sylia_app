/**
 * Aura — application store (Zustand + MMKV).
 *
 * This is the LOCAL SOURCE OF TRUTH. Every screen reads from here; the sync
 * layer (src/data/api/sync.ts) reconciles it with Supabase in the background.
 * The store never awaits the network for a read — that's the offline-first
 * contract that makes Today instant.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { storage } from './persist';
import { generate } from '../domain/engine/generate';
import { TYPES } from '../domain/garments';
import type {
  Garment,
  GarmentTypeId,
  ColorId,
  GeneratedOutfit,
  GenerateOptions,
} from '../domain/types';

const uid = () => Math.random().toString(36).slice(2, 9);
const todayStr = () => new Date().toISOString().slice(0, 10);
const DAY = 864e5;

export interface Taste {
  palette: ColorId[];
  axes: { structure: number; volume: number; era: number };
}

interface SavedOutfit {
  ids: string[];
  reason: string;
  at: number;
}

interface WearEvent {
  at: number;
  ids: string[];
}

export interface AuraState {
  onboarded: boolean;
  taste: Taste;
  items: Garment[];
  savedOutfits: SavedOutfit[];
  wearLog: WearEvent[];
  streak: number;
  lastWear: string | null;
  genUsedToday: number;
  genDate: string | null;

  // selectors
  activeItems: () => Garment[];
  generateLooks: (opts?: GenerateOptions) => GeneratedOutfit[];
  looksLeftToday: () => number;

  // actions
  setOnboarded: (taste?: Taste) => void;
  addGarment: (type: GarmentTypeId, color: ColorId) => Garment;
  confirmTags: (id: string) => void;
  setStatus: (id: string, status: Garment['status']) => void;
  wearOutfit: (o: GeneratedOutfit | { pieces: Garment[]; reason: string }) => () => void;
  saveOutfit: (o: { pieces: Garment[]; reason: string }) => void;
  consumeGeneration: () => void;
  seedDemo: () => void;
  reset: () => void;
}

const FREE_LOOKS_PER_DAY = 3;

export const useStore = create<AuraState>()(
  persist(
    (set, get) => ({
      onboarded: false,
      taste: { palette: ['ink', 'ecru', 'slate', 'rust', 'bone'], axes: { structure: 50, volume: 35, era: 45 } },
      items: [],
      savedOutfits: [],
      wearLog: [],
      streak: 0,
      lastWear: null,
      genUsedToday: 0,
      genDate: null,

      activeItems: () => get().items.filter((i) => i.status === 'active'),

      generateLooks: (opts) => generate(get().items, opts),

      looksLeftToday: () => {
        const s = get();
        if (s.genDate !== todayStr()) return FREE_LOOKS_PER_DAY;
        return Math.max(0, FREE_LOOKS_PER_DAY - s.genUsedToday);
      },

      setOnboarded: (taste) =>
        set((s) => ({ onboarded: true, taste: taste ?? s.taste })),

      addGarment: (type, color) => {
        const t = TYPES[type];
        const item: Garment = {
          id: uid(),
          type,
          color,
          material: t.material,
          warmth: t.warmth,
          formality: t.formality,
          status: 'active',
          tags: [
            { value: t.material, source: 'ai', confidence: 0.86 },
            { value: color, source: 'ai', confidence: 0.94 },
            { value: t.label.toLowerCase(), source: 'ai', confidence: 0.9 },
          ],
          confirmed: false,
          wearCount: 0,
          lastWorn: null,
          addedAt: Date.now(),
        };
        set((s) => ({ items: [item, ...s.items] }));
        return item;
      },

      confirmTags: (id) =>
        set((s) => ({
          items: s.items.map((i) =>
            i.id === id
              ? { ...i, confirmed: true, tags: i.tags.map((t) => ({ ...t, source: 'user' as const, confidence: 1 })) }
              : i,
          ),
        })),

      setStatus: (id, status) =>
        set((s) => ({ items: s.items.map((i) => (i.id === id ? { ...i, status } : i)) })),

      wearOutfit: (o) => {
        const ids = o.pieces.map((p) => p.id);
        const t = todayStr();
        set((s) => {
          const items = s.items.map((i) =>
            ids.includes(i.id) ? { ...i, wearCount: i.wearCount + 1, lastWorn: Date.now() } : i,
          );
          let streak = s.streak;
          let lastWear = s.lastWear;
          if (s.lastWear !== t) {
            const yesterday = new Date(Date.now() - DAY).toISOString().slice(0, 10);
            streak = s.lastWear === yesterday ? s.streak + 1 : 1;
            lastWear = t;
          }
          return { items, streak, lastWear, wearLog: [...s.wearLog, { at: Date.now(), ids }] };
        });
        // returns an undo fn
        return () =>
          set((s) => ({
            items: s.items.map((i) =>
              ids.includes(i.id) ? { ...i, wearCount: Math.max(0, i.wearCount - 1) } : i,
            ),
            wearLog: s.wearLog.slice(0, -1),
          }));
      },

      saveOutfit: (o) =>
        set((s) => ({
          savedOutfits: [{ ids: o.pieces.map((p) => p.id), reason: o.reason, at: Date.now() }, ...s.savedOutfits],
        })),

      consumeGeneration: () =>
        set((s) => {
          const t = todayStr();
          const used = s.genDate === t ? s.genUsedToday + 1 : 1;
          return { genUsedToday: used, genDate: t };
        }),

      seedDemo: () => {
        const demo: [GarmentTypeId, ColorId][] = [
          ['shirt', 'ecru'], ['tee', 'ink'], ['knit', 'olive'], ['blouse', 'bone'],
          ['trousers', 'ink'], ['jeans', 'navy'], ['trousers', 'slate'], ['skirt', 'sand'],
          ['dress', 'rust'], ['dress', 'navy'],
          ['jacket', 'navy'], ['blazer', 'ink'], ['coat', 'stone'],
          ['sneaker', 'bone'], ['loafer', 'brown'], ['boot', 'ink'],
          ['belt', 'brown'], ['shirt', 'stone'], ['knit', 'rust'], ['trousers', 'navy'],
        ];
        const items: Garment[] = demo.map(([type, color]) => {
          const t = TYPES[type];
          const wearCount = Math.floor(Math.random() * 9);
          return {
            id: uid(),
            type,
            color,
            material: t.material,
            warmth: t.warmth,
            formality: t.formality,
            status: 'active',
            tags: [{ value: t.material, source: 'ai', confidence: 0.85 }],
            confirmed: false,
            wearCount,
            lastWorn: wearCount ? Date.now() - (1 + Math.floor(Math.random() * 40)) * DAY : null,
            price: [39, 49, 59, 79, 89, 120][Math.floor(Math.random() * 6)],
            addedAt: Date.now(),
          };
        });
        set({ items });
      },

      reset: () =>
        set({
          onboarded: false,
          items: [],
          savedOutfits: [],
          wearLog: [],
          streak: 0,
          lastWear: null,
          genUsedToday: 0,
          genDate: null,
        }),
    }),
    {
      name: 'aura:v1',
      storage: createJSONStorage(() => storage),
      // don't persist the selector fns
      partialize: (s) => ({
        onboarded: s.onboarded, taste: s.taste, items: s.items,
        savedOutfits: s.savedOutfits, wearLog: s.wearLog, streak: s.streak,
        lastWear: s.lastWear, genUsedToday: s.genUsedToday, genDate: s.genDate,
      }),
    },
  ),
);

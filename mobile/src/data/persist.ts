/**
 * Persistence adapter. MMKV is synchronous and fast (~30× AsyncStorage),
 * which is what lets the store hydrate before first paint and keep the
 * cold-launch budget. Falls back to an in-memory map on web/SSR/tests.
 */

import type { StateStorage } from 'zustand/middleware';

let mmkv: { getString(k: string): string | undefined; set(k: string, v: string): void; delete(k: string): void } | null = null;

try {
  // Lazily required so the domain layer stays importable under plain node.
  const { MMKV } = require('react-native-mmkv');
  mmkv = new MMKV({ id: 'aura' });
} catch {
  const mem = new Map<string, string>();
  mmkv = {
    getString: (k) => mem.get(k),
    set: (k, v) => void mem.set(k, v),
    delete: (k) => void mem.delete(k),
  };
}

export const storage: StateStorage = {
  getItem: (name) => mmkv!.getString(name) ?? null,
  setItem: (name, value) => mmkv!.set(name, value),
  removeItem: (name) => mmkv!.delete(name),
};

/** Raw synchronous key-value access (used for auth tokens). */
export const kv = {
  getString: (k: string) => mmkv!.getString(k) ?? null,
  set: (k: string, v: string) => mmkv!.set(k, v),
  delete: (k: string) => mmkv!.delete(k),
};

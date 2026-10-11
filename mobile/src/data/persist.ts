/**
 * Persistence adapter. expo-sqlite's kv-store gives synchronous reads, which
 * is what lets the store hydrate before first paint and keep the cold-launch
 * budget. Falls back to an in-memory map on web/SSR/tests.
 */

import type { StateStorage } from 'zustand/middleware';

let kvStore: { getString(k: string): string | undefined; set(k: string, v: string): void; delete(k: string): void } | null = null;

try {
  // Lazily required so the domain layer stays importable under plain node.
  const Storage = require('expo-sqlite/kv-store').default;
  Storage.getItemSync('__probe__');
  kvStore = {
    getString: (k) => Storage.getItemSync(k) ?? undefined,
    set: (k, v) => void Storage.setItemSync(k, v),
    delete: (k) => void Storage.removeItemSync(k),
  };
} catch {
  const mem = new Map<string, string>();
  kvStore = {
    getString: (k) => mem.get(k),
    set: (k, v) => void mem.set(k, v),
    delete: (k) => void mem.delete(k),
  };
}

export const storage: StateStorage = {
  getItem: (name) => kvStore!.getString(name) ?? null,
  setItem: (name, value) => kvStore!.set(name, value),
  removeItem: (name) => kvStore!.delete(name),
};

/** Raw synchronous key-value access (used for auth tokens). */
export const kv = {
  getString: (k: string) => kvStore!.getString(k) ?? null,
  set: (k: string, v: string) => kvStore!.set(k, v),
  delete: (k: string) => kvStore!.delete(k),
};

/**
 * Repository interface — the single seam between the app and any backend.
 * The app talks to `Repo`; swapping Supabase for your own API means writing
 * one new implementation and changing one line in `index.ts`. The store works
 * fully offline against the local (no-op remote) impl, so `expo start` needs
 * zero backend configuration.
 */

import type { Garment, Outfit } from '../../domain/types';

export interface Repo {
  /** Pull the user's wardrobe + outfits (remote → local reconcile). */
  pullGarments(): Promise<Garment[]>;
  pushGarment(g: Garment): Promise<void>;
  deleteGarment(id: string): Promise<void>;

  pullOutfits(): Promise<Outfit[]>;
  pushOutfit(o: Outfit): Promise<void>;

  logWear(outfitId: string, garmentIds: string[]): Promise<void>;

  /** Upload a cut-out image, returns its URL. */
  uploadImage(localUri: string, kind: 'garment' | 'composite' | 'wear'): Promise<string>;

  /** Kick off async auto-tagging; results arrive via pullGarments or realtime. */
  requestTagging(garmentId: string, imageUrl: string): Promise<void>;
}

/** Offline-only implementation: everything is local; remote ops are no-ops. */
export const localRepo: Repo = {
  async pullGarments() { return []; },
  async pushGarment() {},
  async deleteGarment() {},
  async pullOutfits() { return []; },
  async pushOutfit() {},
  async logWear() {},
  async uploadImage(localUri) { return localUri; },
  async requestTagging() {},
};

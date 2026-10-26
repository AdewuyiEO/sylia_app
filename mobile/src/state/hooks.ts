/**
 * Domain hooks. Each wraps a piece of the API so screens stay presentational:
 * a screen calls a hook and renders its state. No screen contains a fetch, a
 * URL or a token — swapping the visual shell never touches data flow.
 */
import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { api, uploadPhoto, type ApiItem, type ApiLook, type Category, type BodyScanResult } from '../data/api/endpoints';
import { ApiError } from '../data/api/client';
import { coarseLocation } from '../lib/device';
import { useAsync, errorText } from './useAsync';
import { t } from '../i18n';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Poll a job until it settles (or ~90s pass). */
async function waitForJob<T>(get: () => Promise<{ status: string; result: T | null; error?: string | null }>) {
  for (let i = 0; i < 45; i++) {
    const j = await get();
    if (j.status === 'done') return j.result;
    if (j.status === 'failed') throw new Error(j.error ?? 'failed');
    await sleep(i < 5 ? 1000 : 2000);
  }
  throw new Error('timeout');
}

// ── today ───────────────────────────────────────────────────────────────────
export function useDailyLook() {
  const state = useAsync(async () => api.dailyLook.get(await coarseLocation()));
  const stats = useAsync(() => api.dailyLook.stats());

  const replaceLook = (look: ApiLook) =>
    state.setData((d) => d && { ...d, looks: d.looks.map((l) => (l.id === look.id ? look : l)) });

  /** Log a look as worn; returns this week's worn count for the toast. */
  const wear = useCallback(async (look: ApiLook) => {
    await api.dailyLook.feedback(look.id, 'worn');
    state.setData((d) => d && {
      ...d,
      looks: d.looks.map((l) => ({
        ...l,
        user_feedback: l.id === look.id ? 'worn' : l.user_feedback === 'worn' ? 'pending' : l.user_feedback,
      })),
    });
    const s = await api.dailyLook.stats();
    stats.setData(s);
    return s.weekly_worn_outfits;
  }, []);

  /** Swap: skip this look and get a new one (optionally without one piece). */
  const swap = useCallback(async (look: ApiLook, excludeItemId?: string) => {
    const fresh = await api.dailyLook.regenerate(look.id, excludeItemId);
    state.setData((d) => d && { ...d, looks: [fresh, ...d.looks.filter((l) => l.id !== look.id)] });
    return fresh;
  }, []);

  const react = useCallback(async (look: ApiLook, feedback: 'loved' | 'disliked' | 'skipped') => {
    await api.dailyLook.feedback(look.id, feedback);
    replaceLook({ ...look, user_feedback: feedback });
  }, []);

  return { ...state, stats: stats.data, refetchStats: stats.refetch, wear, swap, react };
}

// ── closet ──────────────────────────────────────────────────────────────────
export function useCloset(category?: Category) {
  return useAsync(() => api.closet.list(category), [category]);
}

export function useItem(id: string) {
  const state = useAsync(() => api.closet.get(id), [id]);
  const save = useCallback(async (patch: Parameters<typeof api.closet.correct>[1]) => {
    const it = await api.closet.correct(id, patch);
    state.setData(it);
    return it;
  }, [id]);
  const remove = useCallback(() => api.closet.remove(id), [id]);
  return { ...state, save, remove };
}

export interface CaptureProgress { phase: 'idle' | 'uploading' | 'processing' | 'done' | 'error'; done: number; total: number; items: ApiItem[]; error?: string }

/** Upload photos → register → wait for the CV job → return the new items. */
export function useCapture() {
  const [progress, setProgress] = useState<CaptureProgress>({ phase: 'idle', done: 0, total: 0, items: [] });

  const run = useCallback(async (uris: string[]) => {
    if (!uris.length) return [];
    setProgress({ phase: 'uploading', done: 0, total: uris.length, items: [] });
    try {
      const jobs: { job_id: string; item_id: string }[] = [];
      for (let i = 0; i < uris.length; i++) {
        const key = await uploadPhoto(uris[i], 'closet');
        jobs.push(await api.closet.register(key));
        setProgress((p) => ({ ...p, done: i + 1 }));
      }
      setProgress((p) => ({ ...p, phase: 'processing' }));
      await Promise.all(jobs.map((j) => waitForJob(() => api.closet.job(j.job_id)).catch(() => null)));
      const items = await Promise.all(jobs.map((j) => api.closet.get(j.item_id)));
      setProgress({ phase: 'done', done: uris.length, total: uris.length, items });
      return items;
    } catch (e) {
      setProgress((p) => ({ ...p, phase: 'error', error: e instanceof ApiError ? errorText(e) : t('capture.failed') }));
      return [];
    }
  }, []);

  const reset = useCallback(() => setProgress({ phase: 'idle', done: 0, total: 0, items: [] }), []);
  return { progress, run, reset };
}

// ── body ────────────────────────────────────────────────────────────────────
export function useBodyScan() {
  const [phase, setPhase] = useState<'idle' | 'working' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<BodyScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (frontUri: string, faceUri?: string | null) => {
    setPhase('working');
    setError(null);
    try {
      const keys = [await uploadPhoto(frontUri, 'body')];
      if (faceUri) keys.push(await uploadPhoto(faceUri, 'body'));
      const { job_id } = await api.body.scan(keys);
      const r = await waitForJob(() => api.body.job(job_id));
      setResult(r);
      setPhase('done');
      return r;
    } catch (e) {
      setError(errorText(e));
      setPhase('error');
      return null;
    }
  }, []);

  return { phase, result, error, run };
}

// ── identity onboarding ─────────────────────────────────────────────────────
export interface ChatTurn { role: 'sylia' | 'user'; text: string }

export function useOnboarding() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [complete, setComplete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await api.identity.start();
      setSessionId(s.session_id);
      setTurns([{ role: 'sylia', text: s.question }]);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const say = useCallback(async (text: string) => {
    if (!sessionId) return;
    setTurns((tt) => [...tt, { role: 'user', text }]);
    setBusy(true);
    setError(null);
    try {
      const r = await api.identity.say(sessionId, text);
      if (r.complete) {
        setComplete(true);
        setTurns((tt) => [...tt, { role: 'sylia', text: t('onboarding.done') }]);
      } else if (r.question) {
        setTurns((tt) => [...tt, { role: 'sylia', text: r.question! }]);
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, [sessionId]);

  return { turns, complete, busy, error, start, say };
}

// ── coach ───────────────────────────────────────────────────────────────────
export function useCoach() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const [needsPro, setNeedsPro] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cid = useRef<string | null>(null);

  const send = useCallback(async (text: string) => {
    setTurns((tt) => [...tt, { role: 'user', text }]);
    setBusy(true);
    setError(null);
    try {
      if (!cid.current) {
        cid.current = (await api.coach.newConversation()).conversation_id;
        setConversationId(cid.current);
      }
      const r = await api.coach.send(cid.current, text);
      setTurns((tt) => [...tt, { role: 'sylia', text: r.reply }]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) setNeedsPro(true);
      else setError(t('coach.error'));
    } finally {
      setBusy(false);
    }
  }, []);

  const reset = useCallback(() => {
    cid.current = null;
    setConversationId(null);
    setTurns([]);
    setError(null);
  }, []);

  return { conversationId, turns, busy, needsPro, error, send, reset, clearNeedsPro: () => setNeedsPro(false) };
}

// ── discover ────────────────────────────────────────────────────────────────
export function useDiscover(category?: Category) {
  return useAsync(() => api.discover.list(category), [category]);
}

// ── billing ─────────────────────────────────────────────────────────────────
export function useBilling() {
  return useAsync(() => api.billing.status());
}

/** Re-run `fn` when the screen regains focus (e.g. after closing a sheet).
 * The latest `fn` is kept in a ref so passing an inline function is safe. */
export function useOnFocus(fn: () => void) {
  const latest = useRef(fn);
  latest.current = fn;
  const first = useRef(true);
  useFocusEffect(
    useCallback(() => {
      if (first.current) {
        first.current = false;
        return;
      }
      latest.current();
    }, []),
  );
}

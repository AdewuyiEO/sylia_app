/**
 * Domain hooks. Each wraps a piece of the API so screens stay presentational.
 *
 * DESIGN NOTE: when you redesign any screen later, you keep calling these hooks
 * and just render their state differently. No screen contains a fetch, a URL, or
 * a token — that all lives here and in the api client. Swapping the visual shell
 * never touches data flow.
 */
import { useCallback, useState } from 'react';
import { api, type ApiItem } from '../data/api/endpoints';

// ── closet ────────────────────────────────────────────────────────────────────
export function useCloset(category?: string) {
  const [items, setItems] = useState<ApiItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.closet
      .list(category)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e?.message ?? 'Could not load your closet'))
      .finally(() => setLoading(false));
  }, [category]);

  const correct = useCallback(
    async (id: string, patch: Partial<ApiItem>) => {
      await api.closet.correct(id, patch);
      load();
    },
    [load],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.closet.remove(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    },
    [],
  );

  return { items, loading, error, load, correct, remove };
}

// ── identity onboarding (the text-first chat) ────────────────────────────────
export interface OnboardingTurn {
  role: 'sylia' | 'user';
  text: string;
}

export function useOnboarding() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<OnboardingTurn[]>([]);
  const [complete, setComplete] = useState(false);
  const [busy, setBusy] = useState(false);

  const start = useCallback(async () => {
    setBusy(true);
    const s = await api.identity.start();
    setSessionId(s.session_id);
    setTurns([{ role: 'sylia', text: s.question }]);
    setBusy(false);
  }, []);

  const say = useCallback(
    async (text: string) => {
      if (!sessionId) return;
      setTurns((t) => [...t, { role: 'user', text }]);
      setBusy(true);
      const r = await api.identity.say(sessionId, text);
      setBusy(false);
      if (r.complete) {
        setComplete(true);
        setTurns((t) => [...t, { role: 'sylia', text: 'Your style profile is set.' }]);
      } else if (r.question) {
        setTurns((t) => [...t, { role: 'sylia', text: r.question! }]);
      }
    },
    [sessionId],
  );

  return { turns, complete, busy, start, say };
}

// ── style coach chat ──────────────────────────────────────────────────────────
export interface CoachTurn {
  role: 'sylia' | 'user';
  text: string;
}

export function useCoach() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<CoachTurn[]>([]);
  const [busy, setBusy] = useState(false);

  const ensure = useCallback(async () => {
    if (conversationId) return conversationId;
    const c = await api.coach.newConversation();
    setConversationId(c.conversation_id);
    return c.conversation_id;
  }, [conversationId]);

  const send = useCallback(
    async (text: string) => {
      const cid = await ensure();
      setTurns((t) => [...t, { role: 'user', text }]);
      setBusy(true);
      try {
        const r = await api.coach.send(cid, text);
        setTurns((t) => [...t, { role: 'sylia', text: r.reply }]);
      } catch (e: any) {
        setTurns((t) => [...t, { role: 'sylia', text: 'I couldn’t reach the coach just now.' }]);
      } finally {
        setBusy(false);
      }
    },
    [ensure],
  );

  return { turns, busy, send };
}

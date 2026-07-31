/**
 * useAsync — the one data-fetching primitive screens use.
 *
 * It turns any `api.*` call into { data, loading, error, refetch }. This is the
 * seam that keeps SCREENS presentational: a screen says "give me the daily look"
 * and renders four states; it never touches fetch, tokens, or URLs. When you
 * redesign a screen, you re-render these same four states differently — the data
 * layer is untouched.
 */
import { useCallback, useEffect, useState } from 'react';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.message ?? 'Something went wrong'))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { data, loading, error, refetch: run };
}

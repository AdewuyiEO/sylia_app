/**
 * useAsync — the one data-fetching primitive screens use.
 *
 * Turns any `api.*` call into { data, loading, error, refetch, setData }. Screens
 * render four states (loading / error / empty / data) and never touch fetch,
 * tokens or URLs. `errorStatus` lets a screen route a 402 to the paywall.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../data/api/client';
import { t } from '../i18n';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
  refetch: () => Promise<void>;
  setData: (d: T | null | ((prev: T | null) => T | null)) => void;
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.status === 0 ? t('common.offline') : e.message;
  return t('common.offline');
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const seq = useRef(0);

  const run = useCallback(async () => {
    const mine = ++seq.current;
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    try {
      const d = await fn();
      if (mine === seq.current) setData(d);
    } catch (e) {
      if (mine === seq.current) {
        setError(errorText(e));
        setErrorStatus(e instanceof ApiError ? e.status : null);
      }
    } finally {
      if (mine === seq.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { data, loading, error, errorStatus, refetch: run, setData };
}

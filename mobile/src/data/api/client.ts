/**
 * The HTTP client: base fetch wrapper that attaches the access token, parses
 * JSON, surfaces errors, and transparently refreshes an expired token once.
 *
 * Tokens are persisted through the same MMKV-with-fallback path the store uses,
 * so they survive reloads in a dev build and degrade to in-memory in Expo Go.
 */
import { API_BASE_URL, ROUTES } from './config';
import { kv } from '../persist';

const ACCESS = 'sylia.token.access';
const REFRESH = 'sylia.token.refresh';

export const tokens = {
  get access() {
    return kv.getString(ACCESS);
  },
  get refresh() {
    return kv.getString(REFRESH);
  },
  set(access: string, refresh: string) {
    kv.set(ACCESS, access);
    kv.set(REFRESH, refresh);
  },
  clear() {
    kv.delete(ACCESS);
    kv.delete(REFRESH);
  },
  get isAuthed() {
    return !!this.access;
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

async function raw<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? safeJson(text) : undefined;

  if (!res.ok) {
    throw new ApiError(res.status, (data as any)?.detail ?? res.statusText, data);
  }
  return data as T;
}

/** Public request helper with one automatic refresh-and-retry on 401. */
export async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  try {
    return await raw<T>(path, options, auth);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && auth && tokens.refresh) {
      const refreshed = await tryRefresh();
      if (refreshed) return await raw<T>(path, options, auth);
    }
    throw e;
  }
}

async function tryRefresh(): Promise<boolean> {
  try {
    const data = await raw<{ access_token: string; refresh_token: string }>(
      ROUTES.refresh,
      { method: 'POST', body: JSON.stringify({ refresh_token: tokens.refresh }) },
      false,
    );
    tokens.set(data.access_token, data.refresh_token);
    return true;
  } catch {
    tokens.clear();
    return false;
  }
}

function safeJson(t: string): unknown {
  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

export const http = {
  get: <T>(p: string, auth = true) => request<T>(p, { method: 'GET' }, auth),
  post: <T>(p: string, body?: unknown, auth = true) =>
    request<T>(p, { method: 'POST', body: body ? JSON.stringify(body) : undefined }, auth),
  patch: <T>(p: string, body?: unknown, auth = true) =>
    request<T>(p, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }, auth),
  del: <T>(p: string, auth = true) => request<T>(p, { method: 'DELETE' }, auth),
};

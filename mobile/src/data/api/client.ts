/**
 * The HTTP client: attaches the access token, parses JSON, surfaces errors, and
 * transparently refreshes an expired token once (refresh tokens rotate server-side).
 *
 * Tokens live in the iOS Keychain / Android Keystore via SecureStore. They are
 * read once at startup (tokens.hydrate) and then served from memory, so request
 * code stays synchronous.
 */
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, ROUTES } from './config';

const ACCESS = 'sylia.token.access';
const REFRESH = 'sylia.token.refresh';

let mem: { access: string | null; refresh: string | null } = { access: null, refresh: null };
let onSignedOut: (() => void) | null = null;

export const tokens = {
  async hydrate() {
    try {
      mem = {
        access: await SecureStore.getItemAsync(ACCESS),
        refresh: await SecureStore.getItemAsync(REFRESH),
      };
    } catch {
      mem = { access: null, refresh: null };
    }
  },
  get access() {
    return mem.access;
  },
  get refresh() {
    return mem.refresh;
  },
  async set(access: string, refresh: string) {
    mem = { access, refresh };
    await SecureStore.setItemAsync(ACCESS, access);
    await SecureStore.setItemAsync(REFRESH, refresh);
  },
  async clear() {
    mem = { access: null, refresh: null };
    await SecureStore.deleteItemAsync(ACCESS).catch(() => {});
    await SecureStore.deleteItemAsync(REFRESH).catch(() => {});
  },
  get isAuthed() {
    return !!mem.access;
  },
  /** Called when refresh fails, so the app can route back to sign-in. */
  onSignedOut(fn: () => void) {
    onSignedOut = fn;
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

async function raw<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (auth && mem.access) headers.Authorization = `Bearer ${mem.access}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, 'network');
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? safeJson(text) : undefined;

  if (!res.ok) {
    const detail = (data as any)?.detail;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText, data);
  }
  return data as T;
}

let refreshing: Promise<boolean> | null = null;

/** Public request helper with one automatic refresh-and-retry on 401. */
export async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  try {
    return await raw<T>(path, options, auth);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && auth && mem.refresh) {
      // one refresh at a time: rotation makes a second concurrent refresh fail
      refreshing ??= tryRefresh().finally(() => (refreshing = null));
      if (await refreshing) return await raw<T>(path, options, auth);
    }
    throw e;
  }
}

async function tryRefresh(): Promise<boolean> {
  try {
    const data = await raw<{ access_token: string; refresh_token: string }>(
      ROUTES.refresh,
      { method: 'POST', body: JSON.stringify({ refresh_token: mem.refresh }) },
      false,
    );
    await tokens.set(data.access_token, data.refresh_token);
    return true;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      await tokens.clear();
      onSignedOut?.();
    }
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
    request<T>(p, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }, auth),
  patch: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(p: string) => request<T>(p, { method: 'DELETE' }),
};

/** PUT a local file (camera/library URI) to a signed upload URL. */
export async function putFile(url: string, localUri: string, headers: Record<string, string>) {
  const blob = await (await fetch(localUri)).blob();
  const res = await fetch(url, { method: 'PUT', headers, body: blob });
  if (!res.ok) throw new ApiError(res.status, 'upload failed');
}

/**
 * Auth store: reactive "am I signed in", the signed-in profile, and the
 * sign-in / sign-up / Apple / logout actions. Logic only — no UI.
 */
import { create } from 'zustand';
import { api, type Me } from '../data/api/endpoints';
import { ApiError, tokens } from '../data/api/client';
import * as purchases from '../data/purchases';
import { deviceRegion } from '../lib/device';
import { t } from '../i18n';
import { cancelDailyReveal } from '../lib/reminders';

interface AuthState {
  status: 'unknown' | 'authed' | 'guest';
  me: Me | null;
  busy: boolean;
  error: string | null;
  hydrate: () => Promise<void>;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string) => Promise<boolean>;
  apple: (identityToken: string, displayName: string | null) => Promise<boolean>;
  refreshMe: () => Promise<void>;
  setMe: (me: Me) => void;
  logout: () => Promise<void>;
  clear: () => void;
}

function message(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 0) return t('common.offline');
    return e.message;
  }
  return t('common.offline');
}

export const useAuth = create<AuthState>((set, get) => {
  const run = async (fn: () => Promise<void>) => {
    set({ busy: true, error: null });
    try {
      await fn();
      set({ status: 'authed', busy: false });
      get().refreshMe();
      return true;
    } catch (e) {
      set({ busy: false, error: message(e) });
      return false;
    }
  };

  tokens.onSignedOut(() => set({ status: 'guest', me: null }));

  return {
    status: 'unknown',
    me: null,
    busy: false,
    error: null,

    hydrate: async () => {
      await tokens.hydrate();
      set({ status: tokens.isAuthed ? 'authed' : 'guest' });
      if (tokens.isAuthed) get().refreshMe();
    },

    login: (email, password) => run(() => api.auth.login(email, password)),
    signup: (email, password) => run(() => api.auth.signup(email, password, deviceRegion())),
    apple: (token, name) => run(() => api.auth.apple(token, name, deviceRegion())),

    refreshMe: async () => {
      try {
        const me = await api.account.me();
        set({ me });
        await purchases.identify(me.id);
      } catch {
        /* offline: keep the cached profile */
      }
    },

    setMe: (me) => set({ me }),

    logout: async () => {
      await cancelDailyReveal();
      await purchases.forget();
      await api.auth.logout();
      set({ status: 'guest', me: null, error: null });
    },

    /** after account deletion: tokens are already dead server-side */
    clear: () => {
      cancelDailyReveal();
      tokens.clear();
      purchases.forget();
      set({ status: 'guest', me: null, error: null });
    },
  };
});

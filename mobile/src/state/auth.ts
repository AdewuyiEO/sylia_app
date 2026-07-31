/**
 * Auth store. Holds reactive login state so screens can gate on it. The tokens
 * themselves live in the api client (MMKV); this store is the React-facing view
 * of "am I logged in", plus the login/signup/logout actions.
 *
 * DESIGN NOTE: this is logic only — no UI. A login SCREEN calls these actions and
 * renders however you design it. Restyling the login page never touches this.
 */
import { create } from 'zustand';
import { api } from '../data/api/endpoints';
import { tokens } from '../data/api/client';

interface AuthState {
  status: 'unknown' | 'authed' | 'guest';
  busy: boolean;
  error: string | null;
  hydrate: () => void;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  status: 'unknown',
  busy: false,
  error: null,

  hydrate: () => set({ status: tokens.isAuthed ? 'authed' : 'guest' }),

  login: async (email, password) => {
    set({ busy: true, error: null });
    try {
      await api.auth.login(email, password);
      set({ status: 'authed', busy: false });
      return true;
    } catch (e: any) {
      set({ busy: false, error: e?.message ?? 'Login failed' });
      return false;
    }
  },

  signup: async (email, password) => {
    set({ busy: true, error: null });
    try {
      await api.auth.signup(email, password);
      set({ status: 'authed', busy: false });
      return true;
    } catch (e: any) {
      set({ busy: false, error: e?.message ?? 'Sign up failed' });
      return false;
    }
  },

  logout: () => {
    api.auth.logout();
    set({ status: 'guest', error: null });
  },
}));

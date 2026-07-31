/**
 * Typed API surface. One function per backend endpoint, grouped by domain.
 * Screens call these — they never touch fetch or URLs directly.
 */
import { http, tokens } from './client';
import { ROUTES } from './config';

// ── shapes returned by the backend (mirrors the FastAPI responses) ──────────
export interface TokenPair {
  access_token: string;
  refresh_token: string;
}
export interface ApiItem {
  id: string;
  category: string;
  subcategory: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  pattern: string | null;
  fit: string | null;
  formality_score: number | null;
  warmth_score: number | null;
  classification_confidence: number | null;
  tags: string[];
  is_active: boolean;
  s3_key_processed: string | null;
}
export interface ApiLook {
  items: { id: string; category: string; subcategory: string; primary_color: string }[];
  score_total: number;
  score_breakdown: { context: number; color: number; body: number; identity: number };
  explanation: string;
}
export interface DailyLookResponse {
  context?: { weather: any; calendar: any };
  looks: ApiLook[];
  reason?: string;
}

// ── auth ────────────────────────────────────────────────────────────────────
export const auth = {
  async signup(email: string, password: string) {
    const t = await http.post<TokenPair>(ROUTES.signup, { email, password }, false);
    tokens.set(t.access_token, t.refresh_token);
    return t;
  },
  async login(email: string, password: string) {
    const t = await http.post<TokenPair>(ROUTES.login, { email, password }, false);
    tokens.set(t.access_token, t.refresh_token);
    return t;
  },
  logout() {
    tokens.clear();
  },
  get isAuthed() {
    return tokens.isAuthed;
  },
};

// ── daily look ────────────────────────────────────────────────────────────────
export const dailyLook = {
  get(coords?: { lat: number; lon: number }) {
    const q = coords ? `?lat=${coords.lat}&lon=${coords.lon}` : '';
    return http.get<DailyLookResponse>(`${ROUTES.dailyLook}${q}`);
  },
  feedback(outfitId: string, feedback: 'worn' | 'skipped' | 'loved' | 'disliked') {
    return http.post(`${ROUTES.dailyLook}/${outfitId}/feedback`, { feedback });
  },
};

// ── closet ────────────────────────────────────────────────────────────────────
export const closet = {
  list(category?: string) {
    const q = category ? `?category=${category}` : '';
    return http.get<{ items: ApiItem[]; count: number }>(`${ROUTES.items}${q}`);
  },
  /** register an uploaded image key → returns a job handle (CV runs async) */
  upload(s3KeyOriginal: string) {
    return http.post<{ job_id: string; status: string }>(ROUTES.items, {
      s3_key_original: s3KeyOriginal,
    });
  },
  jobStatus(jobId: string) {
    return http.get<{ status: string; result: unknown }>(ROUTES.itemJob(jobId));
  },
  correct(id: string, patch: Partial<ApiItem>) {
    return http.patch<ApiItem>(ROUTES.item(id), patch);
  },
  remove(id: string) {
    return http.del(ROUTES.item(id));
  },
};

// ── body profile ──────────────────────────────────────────────────────────────
export const body = {
  scan(s3Keys: string[]) {
    return http.post<{ job_id: string; status: string }>(ROUTES.bodyScan, { s3_keys: s3Keys });
  },
  quiz(undertone: string, silhouette: string) {
    return http.post(ROUTES.quizFallback, { undertone, silhouette });
  },
  get() {
    return http.get(ROUTES.bodyProfile);
  },
};

// ── identity onboarding ───────────────────────────────────────────────────────
export const identity = {
  start() {
    return http.post<{ session_id: string; question: string; complete: boolean }>(
      ROUTES.onboardingStart,
    );
  },
  say(sessionId: string, message: string) {
    return http.post<{
      complete: boolean;
      question: string | null;
      extracted: Record<string, unknown>;
    }>(ROUTES.onboardingTurn(sessionId), { message });
  },
  profile() {
    return http.get(ROUTES.identityProfile);
  },
};

// ── style coach ───────────────────────────────────────────────────────────────
export const coach = {
  newConversation() {
    return http.post<{ conversation_id: string }>(ROUTES.coachConversations);
  },
  send(cid: string, message: string) {
    return http.post<{ reply: string }>(ROUTES.coachMessages(cid), { message });
  },
  /** SSE streaming — see streamCoach() in ./stream for token-by-token UI */
};

// ── billing ───────────────────────────────────────────────────────────────────
export const billing = {
  status() {
    return http.get<{ status: string; entitled: boolean; in_trial: boolean; price_usd: number }>(
      ROUTES.billingStatus,
    );
  },
  checkout() {
    return http.post<{ checkout_url: string }>(ROUTES.checkout);
  },
};

export const api = { auth, dailyLook, closet, body, identity, coach, billing };

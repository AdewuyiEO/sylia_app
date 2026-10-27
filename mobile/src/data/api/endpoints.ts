/**
 * Typed API surface. One function per backend endpoint, grouped by domain.
 * Screens never call these directly — they go through the hooks in src/state.
 */
import { http, tokens, putFile } from './client';
import { ROUTES } from './config';

// ── shapes (mirror the FastAPI responses) ───────────────────────────────────
export interface TokenPair { access_token: string; refresh_token: string }
export interface Region { locale?: string; country?: string | null; timezone?: string | null; units?: 'metric' | 'imperial' }

export interface Me {
  id: string; email: string; display_name: string | null; auth_provider: string;
  locale: string; country: string | null; units: 'metric' | 'imperial'; timezone: string | null;
  reveal_hour: number;
}

export type Category = 'top' | 'bottom' | 'dress' | 'outerwear' | 'shoes' | 'accessory';

export interface ApiItem {
  id: string;
  category: Category;
  subcategory: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  pattern: string | null;
  fit: string | null;
  formality_score: number | null;
  warmth_score: number | null;
  classification_confidence: number | null;
  tags: string[];
  brand: string | null;
  is_active: boolean;
  image_url: string | null;
  wear_count: number;
  last_worn_at: string | null;
  created_at: string;
}

export interface Breakdown { context: number; color: number; body: number; identity: number }

export interface ApiLook {
  id: string;
  rank: number;
  date: string;
  items: ApiItem[];
  score_total: number;
  score_breakdown: Breakdown;
  explanation: string;
  user_feedback: 'pending' | 'worn' | 'skipped' | 'loved' | 'disliked';
  worn_at: string | null;
}

export interface LookContext {
  weather?: { temp_c?: number; temp_f?: number; precipitation?: boolean; condition?: string | null };
  calendar?: { formality_category: number; driver: string | null };
  context_kind?: 'work' | 'weekend';
}

export interface DailyLookResponse {
  date: string; context?: LookContext; looks: ApiLook[]; reason?: string;
  revealed?: boolean; reveal_hour?: number; next_reveal_at?: string;
}

export interface JourneyDay { date: string; state: 'worn' | 'frozen' | 'missed' | 'today'; image_url: string | null }
export interface Badge { id: string; title: string; earned: boolean; progress: number; image_url: string | null }
export interface Journey {
  streak: number; longest: number; freezes: number; max_freezes: number; worn_today: boolean;
  days: JourneyDay[];
  level: { level: number; name: string; points: number; floor: number; next_at: number | null; next_name: string | null };
  challenge: null | { week: string; item: ApiItem; title: string; points: number; accepted: boolean; completed: boolean; days_left: number };
  badges: Badge[];
  reveal_hour: number;
}

export interface Stats {
  weekly_worn_outfits: number;
  streak_days: number;
  closet_size: number;
  closet_utilization_30d: number;
  never_worn: number;
  most_worn: { item_id: string; subcategory: string | null; primary_color: string | null; times_worn: number }[];
}

export interface BodyProfile {
  exists: boolean;
  silhouette_category?: string | null;
  skin_undertone?: string | null;
  color_palette?: { best_colors?: string[]; avoid_colors?: string[]; neutrals?: string[] };
  fit_rules?: string[];
  analysis_method?: string | null;
}

export interface Job<T = unknown> { job_id: string; status: 'queued' | 'processing' | 'done' | 'failed' | string; result: T | null; error?: string | null }

export interface BodyScanResult {
  silhouette_category: string | null; silhouette_confidence: number;
  skin_undertone: string | null; undertone_confidence: number; needs_confirmation: boolean;
}

export interface Recommendation {
  recommendation_id: string;
  product_id: string;
  title: string;
  brand: { name: string; slug: string; logo_url: string | null };
  category: Category;
  subcategory: string | null;
  primary_color: string | null;
  image_url: string | null;
  price: { country?: string; currency: string; amount_minor: number } | null;
  sizes: string[];
  fit_score: number;
  unlocks: number;
  pairs_with: string[];
  rationale: string;
}

export interface BillingStatus {
  status: string; entitled: boolean; in_trial: boolean; trial_ends_at: string | null;
  renews_or_expires_at: string | null; provider: string | null; price_usd: number;
}

export interface IdentityProfile {
  exists: boolean;
  aspirations?: { label: string; priority: number }[];
  insecurities?: { area: string }[];
  lifestyle_patterns?: { activity_level?: string; work_setting?: string | null; coverage?: 'standard' | 'modest' };
  psychological_traits?: Record<string, number>;
  completed?: boolean;
}

export type Landmark = 'head' | 'l_shoulder' | 'r_shoulder' | 'l_hip' | 'r_hip' | 'feet';
export type Landmarks = Record<Landmark, [number, number]>;
export interface Measurements {
  height_cm: number; bust_cm: number; waist_cm: number; hips_cm: number;
  shoulder_cm?: number | null; inseam_cm?: number | null;
}
export interface TryOnProfile extends Partial<Measurements> {
  exists: boolean; photo_url?: string; landmarks?: Landmarks;
  retention?: '30d' | 'keep'; expires_at?: string | null;
}
export type FitLabel = 'too_tight' | 'fitted' | 'comfortable' | 'relaxed' | 'oversized';
export interface SizeFit {
  size: string; zones: { zone: 'bust' | 'waist' | 'hips'; ease_cm: number; label: FitLabel }[];
  length_cm: number; score: number; tight: boolean; explanation: string;
}
export interface FitTable {
  category: Category; renderable: boolean; chart_source: 'brand' | 'standard' | 'measured' | 'estimated';
  recommended: string | null; sizes: SizeFit[];
}
export interface TryOnRender {
  id: string; item_id: string | null; product_id: string | null; size: string; image_url: string;
  fit: SizeFit & { chart_source: string; category: Category }; created_at: string;
}
export type TryTarget = { item_id: string } | { product_id: string };

// ── auth + account ──────────────────────────────────────────────────────────
export const auth = {
  async signup(email: string, password: string, region: Region) {
    const t = await http.post<TokenPair>(ROUTES.signup, { email, password, ...region }, false);
    await tokens.set(t.access_token, t.refresh_token);
  },
  async login(email: string, password: string) {
    const t = await http.post<TokenPair>(ROUTES.login, { email, password }, false);
    await tokens.set(t.access_token, t.refresh_token);
  },
  async apple(identityToken: string, displayName: string | null, region: Region) {
    const t = await http.post<TokenPair>(ROUTES.apple, { identity_token: identityToken, display_name: displayName, ...region }, false);
    await tokens.set(t.access_token, t.refresh_token);
  },
  async logout() {
    const refresh = tokens.refresh;
    if (refresh) await http.post(ROUTES.logout, { refresh_token: refresh }, false).catch(() => {});
    await tokens.clear();
  },
};

export const account = {
  me: () => http.get<Me>(ROUTES.me),
  update: (patch: Partial<Pick<Me, 'display_name' | 'locale' | 'country' | 'units' | 'timezone' | 'reveal_hour'>>) =>
    http.patch<Me>(ROUTES.me, patch),
  export: () => http.get<Record<string, unknown>>(ROUTES.meExport),
  delete: () => http.del<void>(ROUTES.me),
};

// ── uploads ─────────────────────────────────────────────────────────────────
export async function uploadPhoto(localUri: string, purpose: 'closet' | 'body' | 'tryon', contentType = 'image/jpeg') {
  const r = await http.post<{ key: string; upload: { url: string; method: string; headers: Record<string, string> } }>(
    ROUTES.uploads, { purpose, content_type: contentType });
  await putFile(r.upload.url, localUri, r.upload.headers);
  return r.key;
}

// ── daily look ──────────────────────────────────────────────────────────────
export const dailyLook = {
  get(coords?: { lat: number; lon: number } | null) {
    const q = coords ? `?lat=${coords.lat.toFixed(2)}&lon=${coords.lon.toFixed(2)}` : '';
    return http.get<DailyLookResponse>(`${ROUTES.dailyLook}${q}`);
  },
  feedback(id: string, feedback: ApiLook['user_feedback'], note?: string) {
    return http.post<{ user_feedback: string; worn_at: string | null }>(ROUTES.lookFeedback(id), { feedback, note });
  },
  regenerate(id: string, excludeItemId?: string) {
    return http.post<ApiLook>(ROUTES.lookRegenerate(id), excludeItemId ? { exclude_item_id: excludeItemId } : {});
  },
  history: (days = 30) => http.get<{ looks: ApiLook[] }>(`${ROUTES.lookHistory}?days=${days}`),
  reveal: (id: string) => http.post<{ revealed: boolean; streak: number; worn_today: boolean; freezes: number }>(ROUTES.lookReveal(id)),
  stats: () => http.get<Stats>(ROUTES.stats),
};

// ── style journey ───────────────────────────────────────────────────────────
export const journey = {
  get: () => http.get<Journey>(ROUTES.journey),
  acceptChallenge: () => http.post<Journey>(ROUTES.journeyAccept),
};

// ── closet ──────────────────────────────────────────────────────────────────
export const closet = {
  list: (category?: Category) =>
    http.get<{ items: ApiItem[]; count: number }>(`${ROUTES.items}${category ? `?category=${category}` : ''}`),
  get: (id: string) => http.get<ApiItem>(ROUTES.item(id)),
  register: (key: string) => http.post<{ job_id: string; status: string; item_id: string }>(ROUTES.items, { s3_key_original: key }),
  job: (jobId: string) => http.get<Job>(ROUTES.itemJob(jobId)),
  correct: (id: string, patch: Partial<Pick<ApiItem, 'category' | 'subcategory' | 'primary_color' | 'formality_score' | 'warmth_score' | 'brand' | 'tags'>>) =>
    http.patch<ApiItem>(ROUTES.item(id), patch),
  remove: (id: string) => http.del<void>(ROUTES.item(id)),
  fromProduct: (productId: string, size?: string) =>
    http.post<ApiItem>(ROUTES.itemFromProduct, { product_id: productId, size }),
};

// ── body ────────────────────────────────────────────────────────────────────
export const body = {
  scan: (keys: string[]) => http.post<{ job_id: string }>(ROUTES.bodyScan, { s3_keys: keys, consent: true }),
  job: (jobId: string) => http.get<Job<BodyScanResult>>(ROUTES.bodyScanJob(jobId)),
  quiz: (undertone: string, silhouette: string) => http.post(ROUTES.quizFallback, { undertone, silhouette }),
  get: () => http.get<BodyProfile>(ROUTES.bodyProfile),
  delete: () => http.del<void>(ROUTES.bodyProfile),
};

// ── identity ────────────────────────────────────────────────────────────────
export const identity = {
  start: () => http.post<{ session_id: string; question: string; complete: boolean }>(ROUTES.onboardingStart),
  say: (sid: string, message: string) =>
    http.post<{ complete: boolean; question: string | null; message?: string }>(ROUTES.onboardingTurn(sid), { message }),
  profile: () => http.get<IdentityProfile>(ROUTES.identityProfile),
  update: (patch: Partial<Pick<IdentityProfile, 'lifestyle_patterns'>>) => http.patch(ROUTES.identityProfile, patch),
};

// ── coach ───────────────────────────────────────────────────────────────────
export const coach = {
  newConversation: () => http.post<{ conversation_id: string }>(ROUTES.coachConversations),
  history: (cid: string) => http.get<{ messages: { role: 'user' | 'assistant'; content: string }[] }>(ROUTES.coachConversation(cid)),
  send: (cid: string, message: string) => http.post<{ reply: string }>(ROUTES.coachMessages(cid), { message }),
};

// ── discover ────────────────────────────────────────────────────────────────
export const discover = {
  list: (category?: Category) =>
    http.get<{ recommendations: Recommendation[]; disclosure: string; reason?: string }>(
      `${ROUTES.discover}${category ? `?category=${category}` : ''}`),
  click: (rid: string) => http.post<{ url: string }>(ROUTES.discoverClick(rid)),
};

// ── try-on (Sylia Pro) ──────────────────────────────────────────────────────
export const tryon = {
  profile: () => http.get<TryOnProfile>(ROUTES.tryonProfile),
  saveProfile: (b: Measurements & { photo_key?: string; landmarks: Landmarks; retention: '30d' | 'keep';
                                    consent: true; confirm_self: true }) =>
    http.put<TryOnProfile>(ROUTES.tryonProfile, b),
  deleteProfile: () => http.del<void>(ROUTES.tryonProfile),
  fit: (target: TryTarget) => {
    const q = 'item_id' in target ? `item_id=${target.item_id}` : `product_id=${target.product_id}`;
    return http.get<FitTable>(`${ROUTES.tryonFit}?${q}`);
  },
  render: (target: TryTarget, size: string) =>
    http.post<{ job_id: string; status: string }>(ROUTES.tryonRenders, { ...target, size }),
  job: (jobId: string) => http.get<Job<TryOnRender>>(ROUTES.tryonJob(jobId)),
  list: () => http.get<{ renders: TryOnRender[] }>(ROUTES.tryonRenders),
  remove: (id: string) => http.del<void>(ROUTES.tryonRender(id)),
  setItemSize: (itemId: string, size_label: string | null, measurements?: Record<string, number>) =>
    http.put(ROUTES.tryonItemSize(itemId), { size_label, measurements }),
};

// ── integrations + billing ──────────────────────────────────────────────────
export const calendar = {
  status: () => http.get<{ connected: boolean; available: boolean }>(ROUTES.calendar),
  start: () => http.get<{ auth_url: string; return_url: string }>(ROUTES.calendarStart),
  disconnect: () => http.del<void>(ROUTES.calendar),
};

export const billing = {
  status: () => http.get<BillingStatus>(ROUTES.billingStatus),
};

export const api = { auth, account, dailyLook, journey, closet, body, identity, coach, discover, calendar, billing, tryon };

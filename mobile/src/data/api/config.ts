/**
 * API configuration.
 *
 * The base URL is the ONE thing that changes between environments — you never
 * touch code to point the app at a different backend:
 *
 *   • Local dev (Expo Go on a device): your computer's LAN IP, e.g.
 *     http://192.168.1.20:8000   (NOT localhost — the phone isn't your computer)
 *   • iOS simulator:                 http://localhost:8000
 *   • Deployed / TestFlight build:   https://api.sylia.app
 *
 * It reads EXPO_PUBLIC_API_URL from the environment (set in .env or the EAS
 * build profile), falling back to localhost. Because it's read at build time via
 * Expo's public-env mechanism, the SAME codebase produces a local build or a
 * TestFlight build just by changing this one value — see SETUP.
 */
import { Platform } from 'react-native';

const FALLBACK =
  Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? FALLBACK;

/** Endpoint paths, one place, matching the FastAPI routes. */
export const ROUTES = {
  signup: '/v1/auth/signup',
  login: '/v1/auth/login',
  refresh: '/v1/auth/refresh',

  dailyLook: '/v1/daily-look',

  items: '/v1/wardrobe/items',
  item: (id: string) => `/v1/wardrobe/items/${id}`,
  itemJob: (jobId: string) => `/v1/wardrobe/items/jobs/${jobId}`,

  bodyScan: '/v1/body-scan',
  quizFallback: '/v1/body-profile/quiz-fallback',
  bodyProfile: '/v1/body-profile',

  onboardingStart: '/v1/onboarding/sessions',
  onboardingTurn: (sid: string) => `/v1/onboarding/sessions/${sid}/messages`,
  identityProfile: '/v1/identity-profile',

  coachConversations: '/v1/coach/conversations',
  coachMessages: (cid: string) => `/v1/coach/conversations/${cid}/messages`,
  coachStream: (cid: string) => `/v1/coach/conversations/${cid}/messages/stream`,

  billingStatus: '/v1/billing/status',
  checkout: '/v1/billing/checkout-session',
} as const;

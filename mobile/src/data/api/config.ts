/**
 * API configuration.
 *
 * The base URL is the ONE thing that changes between environments:
 *   • Local dev on a phone: your computer's LAN IP, e.g. http://192.168.1.20:8000
 *   • iOS simulator:        http://localhost:8000
 *   • TestFlight / App Store: the deployed HTTPS API
 * It comes from EXPO_PUBLIC_API_URL (mobile/.env locally, eas.json per build profile).
 */
import { Platform } from 'react-native';

const FALLBACK = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? FALLBACK).replace(/\/$/, '');

/** RevenueCat public SDK keys (safe to ship in the app). Empty → purchases disabled. */
export const REVENUECAT_IOS_KEY = process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY ?? '';
export const REVENUECAT_ANDROID_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY ?? '';

export const LEGAL = {
  terms: process.env.EXPO_PUBLIC_TERMS_URL ?? 'https://sylia.app/terms',
  privacy: process.env.EXPO_PUBLIC_PRIVACY_URL ?? 'https://sylia.app/privacy',
};

/** Endpoint paths, one place, matching the FastAPI routes. */
export const ROUTES = {
  signup: '/v1/auth/signup',
  login: '/v1/auth/login',
  apple: '/v1/auth/apple',
  refresh: '/v1/auth/refresh',
  logout: '/v1/auth/logout',

  me: '/v1/me',
  meExport: '/v1/me/export',

  uploads: '/v1/uploads',

  dailyLook: '/v1/daily-look',
  lookFeedback: (id: string) => `/v1/daily-look/${id}/feedback`,
  lookRegenerate: (id: string) => `/v1/daily-look/${id}/regenerate`,
  lookHistory: '/v1/daily-look/history',
  stats: '/v1/daily-look/stats',
  lookReveal: (id: string) => `/v1/daily-look/${id}/reveal`,

  journey: '/v1/journey',
  journeyAccept: '/v1/journey/challenge/accept',

  items: '/v1/wardrobe/items',
  item: (id: string) => `/v1/wardrobe/items/${id}`,
  itemJob: (jobId: string) => `/v1/wardrobe/items/jobs/${jobId}`,
  itemFromProduct: '/v1/wardrobe/items/from-product',

  bodyScan: '/v1/body-scan',
  bodyScanJob: (jobId: string) => `/v1/body-scan/jobs/${jobId}`,
  quizFallback: '/v1/body-profile/quiz-fallback',
  bodyProfile: '/v1/body-profile',

  tryonProfile: '/v1/tryon/profile',
  tryonFit: '/v1/tryon/fit',
  tryonRenders: '/v1/tryon/renders',
  tryonRender: (id: string) => `/v1/tryon/renders/${id}`,
  tryonJob: (jobId: string) => `/v1/tryon/renders/jobs/${jobId}`,
  tryonItemSize: (id: string) => `/v1/tryon/items/${id}/size`,

  onboardingStart: '/v1/onboarding/sessions',
  onboardingTurn: (sid: string) => `/v1/onboarding/sessions/${sid}/messages`,
  identityProfile: '/v1/identity-profile',

  coachConversations: '/v1/coach/conversations',
  coachConversation: (cid: string) => `/v1/coach/conversations/${cid}`,
  coachMessages: (cid: string) => `/v1/coach/conversations/${cid}/messages`,

  discover: '/v1/discover',
  discoverClick: (rid: string) => `/v1/discover/${rid}/click`,

  calendar: '/v1/integrations/calendar',
  calendarStart: '/v1/integrations/calendar/oauth/start',

  billingStatus: '/v1/billing/status',
} as const;

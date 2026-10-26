/**
 * Tiny i18n: the device language picks a dictionary, English fills any gap.
 * Add a language by adding a file next to en.ts and one line to DICTS.
 */
import { getLocales } from 'expo-localization';
import { en, type StringKey } from './en';
import { fr } from './fr';
import { es } from './es';

const DICTS: Record<string, Partial<Record<StringKey, string>>> = { en, fr, es };

function deviceLocale() {
  try {
    const l = getLocales()[0];
    return { tag: l?.languageTag ?? 'en', lang: l?.languageCode ?? 'en', region: l?.regionCode ?? null };
  } catch {
    return { tag: 'en', lang: 'en', region: null };
  }
}

export const locale = deviceLocale();
const dict = DICTS[locale.lang] ?? en;

export function t(key: StringKey, vars?: Record<string, string | number>): string {
  let s = dict[key] ?? en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}

export type { StringKey };

/** Locale-aware formatting: temperature by the user's units, prices in the
 * product's currency, dates in the device language. */
import { locale } from '../i18n';

export type Units = 'metric' | 'imperial';

export function temperature(weather: { temp_c?: number; temp_f?: number } | undefined, units: Units): string | null {
  if (!weather) return null;
  if (units === 'imperial' && weather.temp_f != null) return `${Math.round(weather.temp_f)}°F`;
  if (weather.temp_c != null) return `${Math.round(weather.temp_c)}°C`;
  if (weather.temp_f != null) return `${Math.round(((weather.temp_f - 32) * 5) / 9)}°C`;
  return null;
}

export function price(p: { currency: string; amount_minor: number } | null | undefined): string | null {
  if (!p) return null;
  try {
    const fmt = new Intl.NumberFormat(locale.tag, { style: 'currency', currency: p.currency });
    const digits = fmt.resolvedOptions().maximumFractionDigits ?? 2;
    return fmt.format(p.amount_minor / 10 ** digits);
  } catch {
    return `${(p.amount_minor / 100).toFixed(2)} ${p.currency}`;
  }
}

export function longDate(d: Date = new Date()): string {
  try {
    return d.toLocaleDateString(locale.tag, { weekday: 'long', day: 'numeric', month: 'long' });
  } catch {
    return d.toDateString();
  }
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale.tag, { day: 'numeric', month: 'short' });
  } catch {
    return iso.slice(0, 10);
  }
}

/** Countries where Fahrenheit is the default. */
export function defaultUnits(region: string | null): Units {
  return region && ['US', 'LR', 'MM'].includes(region.toUpperCase()) ? 'imperial' : 'metric';
}

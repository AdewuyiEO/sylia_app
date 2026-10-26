/** Device helpers: coarse location for weather, photo capture, region hints. */
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { getCalendars } from 'expo-localization';
import { locale } from '../i18n';
import { defaultUnits } from './format';
import type { Region } from '../data/api/endpoints';

let cachedCoords: { lat: number; lon: number } | null | undefined;

/** City-level location for weather. Never blocks: denied → null (default weather). */
export async function coarseLocation(): Promise<{ lat: number; lon: number } | null> {
  if (cachedCoords !== undefined) return cachedCoords;
  try {
    const perm = await Location.requestForegroundPermissionsAsync();
    if (perm.status !== 'granted') return (cachedCoords = null);
    const last = await Location.getLastKnownPositionAsync({ maxAge: 6 * 3600 * 1000 });
    const pos = last ?? (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Lowest }));
    cachedCoords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
  } catch {
    cachedCoords = null;
  }
  return cachedCoords;
}

/** Region hints sent at signup so units, catalog and copy are right immediately. */
export function deviceRegion(): Region {
  let timezone: string | null = null;
  try {
    timezone = getCalendars()[0]?.timeZone ?? null;
  } catch {}
  return { locale: locale.tag, country: locale.region, timezone, units: defaultUnits(locale.region) };
}

export type PhotoSource = 'camera' | 'library';

/** Pick photos and shrink them for upload (long edge 1600px, JPEG ~0.8). */
export async function pickPhotos(source: PhotoSource, multiple: boolean): Promise<string[] | 'denied'> {
  const perm = source === 'camera'
    ? await ImagePicker.requestCameraPermissionsAsync()
    : await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!perm.granted) return 'denied';

  const opts: ImagePicker.ImagePickerOptions = {
    mediaTypes: ['images'],
    quality: 1,
    allowsMultipleSelection: source === 'library' && multiple,
    selectionLimit: multiple ? 10 : 1,
    exif: false,
  };
  const res = source === 'camera'
    ? await ImagePicker.launchCameraAsync(opts)
    : await ImagePicker.launchImageLibraryAsync(opts);
  if (res.canceled) return [];

  const out: string[] = [];
  for (const a of res.assets) {
    const longEdge = Math.max(a.width ?? 0, a.height ?? 0);
    const resize = longEdge > 1600
      ? [{ resize: (a.width ?? 0) >= (a.height ?? 0) ? { width: 1600 } : { height: 1600 } }]
      : [];
    const r = await ImageManipulator.manipulateAsync(a.uri, resize, {
      compress: 0.8, format: ImageManipulator.SaveFormat.JPEG,
    });
    out.push(r.uri);
  }
  return out;
}

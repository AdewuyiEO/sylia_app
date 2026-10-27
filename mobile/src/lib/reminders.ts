/**
 * The daily reveal reminder: a local notification at the user's reveal hour,
 * scheduled on the device (no push server needed). Re-scheduled whenever the
 * app opens so the copy carries the current streak. Tapping it opens /reveal.
 */
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { t } from '../i18n';

const ID = 'sylia-daily-reveal';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false,
  }),
});

/** Ask once, in context (after the first reveal) — never on launch. */
export async function askPermission(): Promise<boolean> {
  try {
    const current = await Notifications.getPermissionsAsync();
    if (current.granted) return true;
    if (!current.canAskAgain) return false;
    const r = await Notifications.requestPermissionsAsync({ ios: { allowAlert: true, allowSound: false, allowBadge: false } });
    return r.granted;
  } catch {
    return false;
  }
}

async function granted(): Promise<boolean> {
  try {
    return (await Notifications.getPermissionsAsync()).granted;
  } catch {
    return false;
  }
}

/** (Re)schedule the daily reminder. No-op without permission. */
export async function scheduleDailyReveal(hour: number, streak: number) {
  if (!(await granted())) return;
  try {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('daily-reveal', {
        name: 'Daily look', importance: Notifications.AndroidImportance.DEFAULT,
      });
    }
    await Notifications.cancelScheduledNotificationAsync(ID).catch(() => {});
    await Notifications.scheduleNotificationAsync({
      identifier: ID,
      content: {
        title: t('notif.title'),
        body: streak > 0 ? t('notif.body', { count: streak + 1 }) : t('notif.bodyNew'),
        data: { url: '/reveal' },
      },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour, minute: 0, channelId: 'daily-reveal' },
    });
  } catch {
    /* scheduling is best-effort */
  }
}

export async function cancelDailyReveal() {
  await Notifications.cancelScheduledNotificationAsync(ID).catch(() => {});
}

/** Route taps on the reminder (including the one that launched the app). */
export function onReminderTap(go: (url: string) => void) {
  const handle = (r: Notifications.NotificationResponse | null) => {
    const url = r?.notification.request.content.data?.url;
    if (typeof url === 'string') go(url);
  };
  Notifications.getLastNotificationResponseAsync().then(handle).catch(() => {});
  const sub = Notifications.addNotificationResponseReceivedListener(handle);
  return () => sub.remove();
}

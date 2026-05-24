import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

const DAILY_REMINDER_ID = 'redlight-daily-streak';

export async function ensureNotificationPermission(): Promise<boolean> {
  const settings = await Notifications.getPermissionsAsync();
  if (settings.granted) return true;
  const req = await Notifications.requestPermissionsAsync({
    ios: {
      allowAlert: true,
      allowBadge: true,
      allowSound: true,
    },
  });
  return req.granted;
}

export async function scheduleDailyStreakReminder(): Promise<void> {
  const ok = await ensureNotificationPermission();
  if (!ok) return;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Daily reminder',
      importance: Notifications.AndroidImportance.DEFAULT,
      lightColor: '#ff6b35',
    });
  }

  await Notifications.cancelScheduledNotificationAsync(DAILY_REMINDER_ID).catch(() => {});

  await Notifications.scheduleNotificationAsync({
    identifier: DAILY_REMINDER_ID,
    content: {
      title: 'Redlight',
      body: 'Your streak is on the line. Drive attentively today.',
    },
    trigger: {
      hour: 8,
      minute: 0,
      repeats: true,
      channelId: Platform.OS === 'android' ? 'default' : undefined,
    },
  });
}

export async function cancelStreakReminder(): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(DAILY_REMINDER_ID).catch(() => {});
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

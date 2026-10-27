import React, { useState } from 'react';
import { View, Alert, Linking, Platform } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as Sharing from 'expo-sharing';
import { File, Paths } from 'expo-file-system';
import { Text } from '../src/design/components/Text';
import { Header, Body, Card, Row, Segmented } from '../src/design/components/Screen';
import { Field } from '../src/design/components/Field';
import { Button } from '../src/design/components/Button';
import { useToast } from '../src/ui/toast';
import { useAuth } from '../src/state/auth';
import { useAsync, errorText } from '../src/state/useAsync';
import { api } from '../src/data/api/endpoints';
import * as purchases from '../src/data/purchases';
import { LEGAL } from '../src/data/api/config';
import { scheduleDailyReveal } from '../src/lib/reminders';
import { t } from '../src/i18n';

/** Settings: units, region, coverage, calendar, privacy (export, delete), purchases. */
export default function SettingsScreen() {
  const toast = useToast();
  const me = useAuth((s) => s.me);
  const setMe = useAuth((s) => s.setMe);
  const clearAuth = useAuth((s) => s.clear);
  const identity = useAsync(() => api.identity.profile());
  const cal = useAsync(() => api.calendar.status());
  const [country, setCountry] = useState(me?.country ?? '');
  const [busy, setBusy] = useState<string | null>(null);

  const update = async (patch: Parameters<typeof api.account.update>[0]) => {
    try {
      setMe(await api.account.update(patch));
    } catch (e) {
      toast({ message: errorText(e) });
    }
  };

  const coverage = identity.data?.lifestyle_patterns?.coverage ?? 'standard';
  const setCoverage = async (v: 'standard' | 'modest') => {
    try {
      await api.identity.update({ lifestyle_patterns: { ...(identity.data?.lifestyle_patterns ?? {}), coverage: v } });
      identity.refetch();
    } catch (e) {
      toast({ message: errorText(e) });
    }
  };

  const connectCalendar = async () => {
    setBusy('cal');
    try {
      const { auth_url, return_url } = await api.calendar.start();
      await WebBrowser.openAuthSessionAsync(auth_url, return_url);
      cal.refetch();
    } catch (e) {
      toast({ message: t('settings.calendarUnavailable') });
    } finally {
      setBusy(null);
    }
  };

  const exportData = async () => {
    setBusy('export');
    try {
      const data = await api.account.export();
      const file = new File(Paths.cache, 'sylia-data.json');
      file.write(JSON.stringify(data, null, 2));
      await Sharing.shareAsync(file.uri, { mimeType: 'application/json', UTI: 'public.json' });
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  const deleteAccount = () => Alert.alert(t('settings.deleteAccount'), t('settings.deleteConfirm'), [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('common.delete'), style: 'destructive', onPress: async () => {
      try {
        await api.account.delete();
        clearAuth();
        toast({ message: t('settings.deleted') });
      } catch (e) {
        toast({ message: errorText(e) });
      }
    } },
  ]);

  return (
    <View style={{ flex: 1 }}>
      <Header back title={t('settings.title')} />
      <Body>
        <Text variant="label" tone="ink60">{t('settings.units')}</Text>
        <Segmented value={me?.units ?? 'metric'} onChange={(v) => update({ units: v })}
                   options={[{ value: 'metric', label: t('settings.metric') }, { value: 'imperial', label: t('settings.imperial') }]} />

        <Text variant="label" tone="ink60">{t('settings.reveal')}</Text>
        <Segmented value={String(me?.reveal_hour ?? 7) as '6' | '7' | '8' | '9'}
                   onChange={async (v) => {
                     await update({ reveal_hour: Number(v) });
                     try { scheduleDailyReveal(Number(v), (await api.dailyLook.stats()).streak_days); } catch {}
                   }}
                   options={(['6', '7', '8', '9'] as const).map((h) => ({ value: h, label: `${h}:00` }))} />
        <Text variant="small" tone="ink60">{t('settings.revealHint')}</Text>

        <Field label={t('settings.country')} value={country} autoCapitalize="characters" maxLength={2}
               onChangeText={(v) => setCountry(v.toUpperCase())}
               onEndEditing={() => country.length === 2 && country !== me?.country && update({ country })} />

        <Text variant="label" tone="ink60">{t('settings.coverage')}</Text>
        <Segmented value={coverage} onChange={setCoverage}
                   options={[{ value: 'standard', label: t('settings.coverage.standard') },
                             { value: 'modest', label: t('settings.coverage.modest') }]} />
        <Text variant="small" tone="ink60">{t('settings.coverageHint')}</Text>

        <Card>
          <Text variant="h3">{t('settings.calendar')}</Text>
          <Text variant="small" tone="ink60">{t('settings.calendarHint')}</Text>
          {cal.data?.connected ? (
            <Button label={t('settings.disconnect')} variant="secondary"
                    onPress={async () => { await api.calendar.disconnect(); cal.refetch(); }} />
          ) : (
            <Button label={cal.data?.available === false ? t('settings.calendarUnavailable') : t('settings.connect')}
                    variant="tertiary" onPress={connectCalendar} loading={busy === 'cal'} disabled={cal.data?.available === false} />
          )}
        </Card>

        <Text variant="label" tone="ink60">{t('you.subscription')}</Text>
        <View style={{ gap: 8 }}>
          {purchases.purchasesAvailable() ? (
            <Row label={t('settings.restore')} onPress={async () => {
              try { await purchases.restore(); toast({ message: t('common.done') }); } catch (e) { toast({ message: errorText(e) }); }
            }} />
          ) : null}
          <Row label={t('settings.manage')} onPress={() => Linking.openURL(Platform.OS === 'ios'
            ? 'https://apps.apple.com/account/subscriptions'
            : 'https://play.google.com/store/account/subscriptions')} />
        </View>

        <Text variant="label" tone="ink60">{t('settings.privacy')}</Text>
        <View style={{ gap: 8 }}>
          <Row label={t('auth.privacy')} onPress={() => WebBrowser.openBrowserAsync(LEGAL.privacy)} />
          <Row label={t('auth.terms')} onPress={() => WebBrowser.openBrowserAsync(LEGAL.terms)} />
          <Row label={t('settings.export')} value={busy === 'export' ? '…' : undefined} onPress={exportData} />
          <Row label={t('settings.deleteAccount')} danger onPress={deleteAccount} />
        </View>
      </Body>
    </View>
  );
}

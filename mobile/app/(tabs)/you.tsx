import React from 'react';
import { View } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Header, Body, Card, Row } from '../../src/design/components/Screen';
import { useAuth } from '../../src/state/auth';
import { useBilling, useOnFocus } from '../../src/state/hooks';
import { useAsync } from '../../src/state/useAsync';
import { api } from '../../src/data/api/endpoints';
import { shortDate } from '../../src/lib/format';
import { t } from '../../src/i18n';

/** You: the north-star numbers, subscription, and the way into every profile. */
export default function YouScreen() {
  const router = useRouter();
  const me = useAuth((s) => s.me);
  const logout = useAuth((s) => s.logout);
  const billing = useBilling();
  const stats = useAsync(() => api.dailyLook.stats());
  useOnFocus(() => { billing.refetch(); stats.refetch(); });

  const b = billing.data;
  const plan = !b ? '' : b.status === 'active' || (b.entitled && !b.in_trial) ? t('you.pro')
    : b.in_trial ? t('you.trial', { date: shortDate(b.trial_ends_at) }) : t('you.inactive');

  return (
    <View style={{ flex: 1 }}>
      <Header title={me?.display_name || t('you.title')} subtitle={me?.email?.endsWith('.invalid') ? undefined : me?.email} />
      <Body onRefresh={() => { billing.refetch(); stats.refetch(); }} refreshing={billing.loading || stats.loading}>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Stat value={stats.data?.weekly_worn_outfits} label={t('you.wwo')} />
          <Stat value={stats.data?.streak_days} label={t('you.streak')} />
          <Stat value={stats.data ? `${Math.round(stats.data.closet_utilization_30d * 100)}%` : undefined} label={t('you.utilisation')} />
        </View>

        <Card>
          <Text variant="label" tone="ink60">{t('you.subscription')}</Text>
          <Text variant="h2">{plan}</Text>
          {b && b.status !== 'active' ? <Button label={t('you.upgrade')} onPress={() => router.push('/paywall')} /> : null}
        </Card>

        <View style={{ gap: 8 }}>
          <Row label={t('you.journey')} onPress={() => router.push('/journey')} />
          <Row label={t('you.styleProfile')} onPress={() => router.push('/onboarding')} />
          <Row label={t('you.bodyProfile')} onPress={() => router.push('/body')} />
          <Row label={t('you.settings')} onPress={() => router.push('/settings')} />
          <Row label={t('you.logout')} onPress={logout} />
        </View>
      </Body>
    </View>
  );
}

function Stat({ value, label }: { value: number | string | undefined; label: string }) {
  const { c, radius } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: c.surface, borderRadius: radius.card, borderWidth: 1, borderColor: c.hair,
                   padding: 12, gap: 4 }} accessible accessibilityLabel={`${label}: ${value ?? ''}`}>
      <Text variant="h1" style={{ fontVariant: ['tabular-nums'] }}>{value ?? '–'}</Text>
      <Text variant="small" tone="ink60">{label}</Text>
    </View>
  );
}

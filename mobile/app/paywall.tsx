import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Header, Body, Card, Loading } from '../src/design/components/Screen';
import { useToast } from '../src/ui/toast';
import { errorText } from '../src/state/useAsync';
import { api } from '../src/data/api/endpoints';
import * as purchases from '../src/data/purchases';
import { t } from '../src/i18n';

/**
 * Paywall. The store shows the price in the buyer's currency; the server
 * decides entitlement from RevenueCat's webhook, so after buying we poll status.
 */
export default function PaywallScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const { reason } = useLocalSearchParams<{ reason?: string }>();
  const [offer, setOffer] = useState<purchases.Offer | null | undefined>(undefined);
  const [busy, setBusy] = useState<'buy' | 'restore' | null>(null);

  useEffect(() => {
    purchases.currentOffer().then(setOffer).catch(() => setOffer(null));
  }, []);

  const waitForEntitlement = async () => {
    for (let i = 0; i < 10; i++) {
      const s = await api.billing.status();
      if (s.status === 'active') return true;
      await new Promise((r) => setTimeout(r, 1500));
    }
    return false;
  };

  const buy = async () => {
    if (!offer) return;
    setBusy('buy');
    try {
      if (await purchases.buy(offer)) {
        await waitForEntitlement();
        toast({ message: t('paywall.welcome') });
        router.back();
      }
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  const restore = async () => {
    setBusy('restore');
    try {
      await purchases.restore();
      if (await waitForEntitlement()) { toast({ message: t('paywall.welcome') }); router.back(); }
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <Header eyebrow={reason ? t('paywall.required') : undefined} title={t('paywall.title')} />
      <Body>
        <Text variant="h2">{t('paywall.lead')}</Text>
        <Card>
          {(['paywall.f4', 'paywall.f1', 'paywall.f2', 'paywall.f3'] as const).map((k) => (
            <View key={k} style={{ flexDirection: 'row', gap: 10 }}>
              <Text tone="brand">✓</Text>
              <Text style={{ flex: 1 }}>{t(k)}</Text>
            </View>
          ))}
        </Card>

        {offer === undefined ? <Loading /> : offer ? (
          <>
            <Button label={`${t('paywall.subscribe')} · ${offer.price}`} onPress={buy} loading={busy === 'buy'} />
            <Button label={t('paywall.restore')} variant="ghost" onPress={restore} loading={busy === 'restore'} />
            <Text variant="small" tone="ink60">{t('paywall.terms')}</Text>
          </>
        ) : (
          <Card inset><Text>{t('paywall.unavailable')}</Text></Card>
        )}
        <Button label={t('common.close')} variant="secondary" onPress={() => router.back()} />
      </Body>
    </View>
  );
}

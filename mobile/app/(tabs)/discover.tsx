import React, { useState } from 'react';
import { View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Chip } from '../../src/design/components/Chip';
import { Header, Body, Card, Loading, EmptyState } from '../../src/design/components/Screen';
import { ItemImage } from '../../src/design/components/ItemImage';
import { useToast } from '../../src/ui/toast';
import { useDiscover, useOnFocus } from '../../src/state/hooks';
import { errorText } from '../../src/state/useAsync';
import { api, type Recommendation } from '../../src/data/api/endpoints';
import { price } from '../../src/lib/format';
import { t } from '../../src/i18n';

/**
 * Discover: only products that clear the fit gate for THIS closet, ranked by
 * fit (never by commission), each with the reason it earned its place, plus the
 * commission disclosure.
 */
export default function DiscoverScreen() {
  const toast = useToast();
  const { data, loading, error, refetch, setData } = useDiscover();
  useOnFocus(refetch);

  const recs = data?.recommendations ?? [];
  const header = <Header title={t('discover.title')} subtitle={t('discover.sub')} />;

  if (loading && !data) return <View style={{ flex: 1 }}>{header}<Loading /></View>;
  if (error && !data) {
    return <View style={{ flex: 1 }}>{header}<Body><EmptyState title={error} primary={{ label: t('common.tryAgain'), onPress: refetch }} /></Body></View>;
  }

  const bought = async (r: Recommendation) => {
    try {
      await api.closet.fromProduct(r.product_id);
      setData((d) => d && { ...d, recommendations: d.recommendations.filter((x) => x.product_id !== r.product_id) });
      toast({ message: t('discover.addedToCloset') });
    } catch (e) {
      toast({ message: errorText(e) });
    }
  };

  return (
    <View style={{ flex: 1 }}>
      {header}
      <Body onRefresh={refetch} refreshing={loading}>
        {recs.length === 0 ? (
          <EmptyState title={t('discover.emptyTitle')} body={data?.reason ?? t('discover.emptyBody')} />
        ) : recs.map((r) => <ProductCard key={r.recommendation_id} rec={r} onBought={() => bought(r)} />)}
        {data?.disclosure ? <Text variant="small" tone="ink60" style={{ textAlign: 'center' }}>{data.disclosure}</Text> : null}
      </Body>
    </View>
  );
}

function ProductCard({ rec, onBought }: { rec: Recommendation; onBought: () => void }) {
  const { c } = useTheme();
  const toast = useToast();
  const [opening, setOpening] = useState(false);

  const open = async () => {
    setOpening(true);
    try {
      const { url } = await api.discover.click(rec.recommendation_id);
      await WebBrowser.openBrowserAsync(url, { controlsColor: c.action });
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setOpening(false);
    }
  };

  return (
    <Card style={{ padding: 0, overflow: 'hidden', gap: 0 }}>
      <ItemImage uri={rec.image_url} color={rec.primary_color} label={rec.title} style={{ aspectRatio: 4 / 3, borderRadius: 0 }} />
      <View style={{ padding: 16, gap: 10 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="label" tone="ink60">{rec.brand.name}</Text>
            <Text variant="h3">{rec.title}</Text>
          </View>
          {rec.price ? <Text variant="number">{price(rec.price)}</Text> : null}
        </View>
        <Text>{rec.rationale}</Text>
        <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
          <Chip label={t('discover.newLooks', { count: rec.unlocks })} attention />
        </View>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          {/* one ember element per screen: cards repeat, so their actions stay quiet */}
          <Button label={t('discover.shop')} variant="secondary" onPress={open} loading={opening} style={{ flex: 1 }} />
          <Button label={t('discover.bought')} variant="tertiary" onPress={onBought} style={{ flex: 1 }} />
        </View>
      </View>
    </Card>
  );
}

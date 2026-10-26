import React, { useState } from 'react';
import { View, Pressable, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Chip } from '../../src/design/components/Chip';
import { Header, Body, Loading, EmptyState } from '../../src/design/components/Screen';
import { ItemImage } from '../../src/design/components/ItemImage';
import { useCloset, useOnFocus } from '../../src/state/hooks';
import type { ApiItem, Category } from '../../src/data/api/endpoints';
import { t, type StringKey } from '../../src/i18n';

const FILTERS: (Category | undefined)[] = [undefined, 'top', 'bottom', 'dress', 'outerwear', 'shoes', 'accessory'];

/** Closet grid with category filters. Tap a piece to check or fix its tags. */
export default function ClosetScreen() {
  const router = useRouter();
  const { layout } = useTheme();
  const [category, setCategory] = useState<Category | undefined>();
  const { data, loading, error, refetch } = useCloset(category);
  useOnFocus(refetch);

  const items = data?.items ?? [];
  const add = <Button label="+" variant="tertiary" onPress={() => router.push('/capture')}
                      accessibilityHint={t('closet.add')} style={{ width: 44, paddingHorizontal: 0, alignSelf: 'auto' }} />;

  return (
    <View style={{ flex: 1 }}>
      <Header title={t('closet.title')} subtitle={data ? t('closet.count', { count: data.count }) : undefined} right={add} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }}
                  contentContainerStyle={{ paddingHorizontal: layout.gutter, gap: 8, paddingBottom: 12 }}>
        {FILTERS.map((f) => (
          <Chip key={f ?? 'all'} label={f ? t(`cat.${f}` as StringKey) : t('closet.all')}
                selected={category === f} onPress={() => setCategory(f)} />
        ))}
      </ScrollView>

      {loading && !data ? <Loading /> : error && !data ? (
        <Body><EmptyState title={error} primary={{ label: t('common.tryAgain'), onPress: refetch }} /></Body>
      ) : items.length === 0 ? (
        <Body>
          <EmptyState title={t('closet.emptyTitle')} body={t('closet.emptyBody')}
                      primary={{ label: t('closet.add'), onPress: () => router.push('/capture') }} />
        </Body>
      ) : (
        <Body onRefresh={refetch} refreshing={loading}
              contentStyle={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
          {items.map((it) => <Tile key={it.id} item={it} onPress={() => router.push(`/item/${it.id}`)} />)}
        </Body>
      )}
    </View>
  );
}

function Tile({ item, onPress }: { item: ApiItem; onPress: () => void }) {
  const processing = item.classification_confidence == null;
  const review = !processing && (item.classification_confidence ?? 1) < 0.5;
  const name = [item.primary_color, item.subcategory ?? t(`cat.${item.category}` as StringKey)].filter(Boolean).join(' ');
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={name}
               style={{ width: '31.5%', gap: 4 }}>
      <ItemImage uri={item.image_url} color={item.primary_color} style={{ aspectRatio: 0.8 }} />
      <Text variant="small" numberOfLines={1}>{name}</Text>
      {processing ? <Chip label={t('closet.processing')} /> : review ? <Chip label={t('closet.review')} attention /> : (
        <Text variant="small" tone="ink60">
          {item.wear_count ? t('closet.wornTimes', { count: item.wear_count }) : t('closet.neverWorn')}
        </Text>
      )}
    </Pressable>
  );
}

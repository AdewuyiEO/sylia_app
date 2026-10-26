import React, { useEffect, useState } from 'react';
import { View, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Chip } from '../../src/design/components/Chip';
import { Field } from '../../src/design/components/Field';
import { Header, Body, Card, Loading, EmptyState, Segmented } from '../../src/design/components/Screen';
import { ItemImage, SWATCH } from '../../src/design/components/ItemImage';
import { useToast } from '../../src/ui/toast';
import { useItem } from '../../src/state/hooks';
import { errorText } from '../../src/state/useAsync';
import type { Category } from '../../src/data/api/endpoints';
import { shortDate } from '../../src/lib/format';
import { t, type StringKey } from '../../src/i18n';

const CATEGORIES: Category[] = ['top', 'bottom', 'dress', 'outerwear', 'shoes', 'accessory'];
const COLORS = Object.keys(SWATCH);
const LEVELS = ['1', '2', '3', '4', '5'] as const;

/** Item detail + tag confirm. Every correction is ground truth for the classifier. */
export default function ItemScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { data: item, loading, error, refetch, save, remove } = useItem(id);
  const [draft, setDraft] = useState({ category: 'top' as Category, subcategory: '', primary_color: '', brand: '',
                                       formality_score: 3, warmth_score: 3 });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (item) setDraft({
      category: item.category, subcategory: item.subcategory ?? '', primary_color: item.primary_color ?? '',
      brand: item.brand ?? '', formality_score: item.formality_score ?? 3, warmth_score: item.warmth_score ?? 3,
    });
  }, [item]);

  if (loading && !item) return <View style={{ flex: 1 }}><Header back title={t('item.title')} /><Loading /></View>;
  if (!item) {
    return <View style={{ flex: 1 }}><Header back title={t('item.title')} />
      <Body><EmptyState title={error ?? ''} primary={{ label: t('common.tryAgain'), onPress: refetch }} /></Body></View>;
  }

  const onSave = async () => {
    setSaving(true);
    try {
      await save({ ...draft, subcategory: draft.subcategory.trim().toLowerCase() || null,
                   brand: draft.brand.trim() || null, primary_color: draft.primary_color || null });
      toast({ message: t('item.saved') });
      router.back();
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setSaving(false);
    }
  };

  const onDelete = () => Alert.alert(t('item.delete'), undefined, [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('common.delete'), style: 'destructive', onPress: async () => {
      try { await remove(); toast({ message: t('item.deleted') }); router.back(); }
      catch (e) { toast({ message: errorText(e) }); }
    } },
  ]);

  const unsure = (item.classification_confidence ?? 0) < 0.5;

  return (
    <View style={{ flex: 1 }}>
      <Header back title={t('item.title')}
              subtitle={item.wear_count ? `${t('closet.wornTimes', { count: item.wear_count })} · ${shortDate(item.last_worn_at)}` : t('closet.neverWorn')} />
      <Body>
        <ItemImage uri={item.image_url} color={draft.primary_color} style={{ aspectRatio: 1 }} />
        {unsure ? <Card inset><Text variant="small">{t('item.reviewHint')}</Text></Card> : null}

        <Text variant="label" tone="ink60">{t('item.category')}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {CATEGORIES.map((cat) => (
            <Chip key={cat} label={t(`cat.${cat}` as StringKey)} selected={draft.category === cat}
                  onPress={() => setDraft({ ...draft, category: cat })} />
          ))}
        </View>

        <Field label={t('item.type')} value={draft.subcategory} onChangeText={(v) => setDraft({ ...draft, subcategory: v })}
               placeholder="blouse, jeans, loafers…" autoCapitalize="none" />

        <Text variant="label" tone="ink60">{t('item.color')}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {COLORS.map((name) => (
            <Chip key={name} label={name} selected={draft.primary_color === name}
                  onPress={() => setDraft({ ...draft, primary_color: name })} />
          ))}
        </View>

        <Field label={t('item.brand')} value={draft.brand} onChangeText={(v) => setDraft({ ...draft, brand: v })} />

        <Text variant="label" tone="ink60">{t('item.formality')}</Text>
        <Segmented options={LEVELS.map((l) => ({ value: l, label: l }))} value={String(draft.formality_score) as typeof LEVELS[number]}
                   onChange={(v) => setDraft({ ...draft, formality_score: Number(v) })} />
        <Text variant="label" tone="ink60">{t('item.warmth')}</Text>
        <Segmented options={LEVELS.map((l) => ({ value: l, label: l }))} value={String(draft.warmth_score) as typeof LEVELS[number]}
                   onChange={(v) => setDraft({ ...draft, warmth_score: Number(v) })} />

        <Button label={t('common.save')} onPress={onSave} loading={saving} />
        <Button label={t('item.delete')} variant="danger" onPress={onDelete} />
      </Body>
    </View>
  );
}

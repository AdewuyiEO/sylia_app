import React from 'react';
import { View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Header, Body, Card, Loading } from '../src/design/components/Screen';
import { ItemImage } from '../src/design/components/ItemImage';
import { Chip } from '../src/design/components/Chip';
import { useToast } from '../src/ui/toast';
import { useCapture } from '../src/state/hooks';
import { pickPhotos, type PhotoSource } from '../src/lib/device';
import { t } from '../src/i18n';

/**
 * Step 3 / Closet: photograph pieces → upload → Sylia tags them → review.
 * Tag review ships with capture (not after): corrections are how the model learns.
 */
export default function CaptureScreen() {
  const router = useRouter();
  const toast = useToast();
  const { onboarding } = useLocalSearchParams<{ onboarding?: string }>();
  const { progress, run, reset } = useCapture();

  const start = async (source: PhotoSource) => {
    const uris = await pickPhotos(source, true);
    if (uris === 'denied') return toast({ message: t('capture.permission') });
    if (uris.length) {
      const items = await run(uris);
      if (items.length) toast({ message: t('capture.done', { count: items.length }) });
    }
  };

  const busy = progress.phase === 'uploading' || progress.phase === 'processing';

  return (
    <View style={{ flex: 1 }}>
      <Header eyebrow={onboarding ? t('capture.eyebrow') : undefined} title={t('capture.title')} />
      <Body>
        {busy ? (
          <Loading label={progress.phase === 'uploading'
            ? t('capture.uploading', { done: progress.done, total: progress.total })
            : t('capture.processing')} />
        ) : progress.phase === 'done' ? (
          <>
            <Text tone="ink60">{t('capture.done', { count: progress.items.length })}</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
              {progress.items.map((it) => {
                const unsure = (it.classification_confidence ?? 0) < 0.5;
                return (
                  <View key={it.id} style={{ width: '31.5%', gap: 4 }}>
                    <ItemImage uri={it.image_url} color={it.primary_color} style={{ aspectRatio: 0.8 }} />
                    <Text variant="small" numberOfLines={1}>{[it.primary_color, it.subcategory ?? it.category].filter(Boolean).join(' ')}</Text>
                    {unsure ? <Chip label={t('closet.review')} attention onPress={() => router.push(`/item/${it.id}`)} /> : null}
                  </View>
                );
              })}
            </View>
            <Button label={t('closet.add')} variant="secondary" onPress={reset} />
            <Button label={t('common.done')} onPress={() => (onboarding ? router.replace('/today') : router.back())} />
          </>
        ) : (
          <>
            <Card inset><Text>{t('capture.body')}</Text></Card>
            {progress.phase === 'error' ? <Text variant="small" tone="action">{progress.error}</Text> : null}
            <Button label={t('capture.camera')} onPress={() => start('camera')} />
            <Button label={t('capture.library')} variant="secondary" onPress={() => start('library')} />
            <Button label={onboarding ? t('body.skip') : t('common.cancel')} variant="ghost"
                    onPress={() => (onboarding ? router.replace('/today') : router.back())} />
          </>
        )}
      </Body>
    </View>
  );
}

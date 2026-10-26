import React, { useState } from 'react';
import { View, Pressable, Switch } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Header, Body, Card, Loading, Row } from '../src/design/components/Screen';
import { ItemImage, SWATCH } from '../src/design/components/ItemImage';
import { useToast } from '../src/ui/toast';
import { useBodyScan } from '../src/state/hooks';
import { useAsync, errorText } from '../src/state/useAsync';
import { api } from '../src/data/api/endpoints';
import { pickPhotos } from '../src/lib/device';
import { t, type StringKey } from '../src/i18n';

const UNDERTONES = ['warm', 'cool', 'neutral'] as const;
const SHAPES = ['hourglass', 'rectangle', 'triangle', 'inverted_triangle', 'oval'] as const;

/**
 * Step 2: colours and shape. Two paths that are treated as equals: a photo scan
 * (explicit consent, photos deleted after analysis) or two self-report
 * questions. A low-confidence scan sends the user to the questions instead of
 * committing to a guess.
 */
export default function BodyScreen() {
  const { onboarding } = useLocalSearchParams<{ onboarding?: string }>();
  const inOnboarding = onboarding === '1';
  const router = useRouter();
  const toast = useToast();
  const profile = useAsync(() => api.body.get());
  const scan = useBodyScan();
  const [mode, setMode] = useState<'intro' | 'scan' | 'quiz'>('intro');
  const [front, setFront] = useState<string | null>(null);
  const [face, setFace] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [undertone, setUndertone] = useState<string | null>(null);
  const [shape, setShape] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const finish = () => (inOnboarding ? router.replace('/capture?onboarding=1') : router.back());

  const pick = async (which: 'front' | 'face') => {
    const r = await pickPhotos('camera', false);
    if (r === 'denied') return toast({ message: t('capture.permission') });
    if (r[0]) (which === 'front' ? setFront : setFace)(r[0]);
  };

  const runScan = async () => {
    if (!front || !consent) return;
    const r = await scan.run(front, face);
    if (r && r.needs_confirmation) setMode('quiz');
    else if (r) { toast({ message: t('body.saved') }); profile.refetch(); }
  };

  const saveQuiz = async () => {
    if (!undertone || !shape) return;
    setSaving(true);
    try {
      await api.body.quiz(undertone, shape);
      toast({ message: t('body.saved') });
      finish();
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setSaving(false);
    }
  };

  const best = profile.data?.color_palette?.best_colors ?? [];

  return (
    <View style={{ flex: 1 }}>
      <Header back={!inOnboarding} eyebrow={inOnboarding ? t('body.eyebrow') : undefined} title={t('body.title')} />
      <Body>
        {mode === 'intro' ? (
          <>
            <Text tone="ink60">{t('body.lead')}</Text>
            {profile.loading ? <Loading /> : profile.data?.exists ? (
              <Card>
                <Text variant="label" tone="ink60">{t('body.best')}</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {best.map((name) => (
                    <View key={name} accessible accessibilityLabel={name} style={{ alignItems: 'center', gap: 4 }}>
                      <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: SWATCH[name] ?? '#ccc' }} />
                      <Text variant="small" tone="ink60">{name}</Text>
                    </View>
                  ))}
                </View>
              </Card>
            ) : null}
            <Button label={t('body.scan')} onPress={() => setMode('scan')} />
            <Button label={t('body.quiz')} variant="secondary" onPress={() => setMode('quiz')} />
            {inOnboarding ? <Button label={t('body.skip')} variant="ghost" onPress={finish} /> : null}
            {!inOnboarding && profile.data?.exists ? (
              <Row label={t('body.delete')} danger onPress={async () => { await api.body.delete(); profile.refetch(); }} />
            ) : null}
          </>
        ) : null}

        {mode === 'scan' ? (
          scan.phase === 'working' ? <Loading label={t('body.analysing')} /> : (
            <>
              <Text tone="ink60">{t('body.scanNote')}</Text>
              <View style={{ flexDirection: 'row', gap: 12 }}>
                <PhotoSlot label={t('body.front')} uri={front} onPress={() => pick('front')} />
                <PhotoSlot label={t('body.face')} uri={face} onPress={() => pick('face')} />
              </View>
              <Pressable onPress={() => setConsent(!consent)} accessibilityRole="switch" accessibilityState={{ checked: consent }}
                         style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
                <Switch value={consent} onValueChange={setConsent} />
                <Text variant="small" style={{ flex: 1 }}>{t('body.consent')}</Text>
              </Pressable>
              {scan.error ? <Text variant="small" tone="action">{scan.error}</Text> : null}
              {scan.phase === 'done' && scan.result && !scan.result.needs_confirmation ? (
                <Button label={t('common.continue')} onPress={finish} />
              ) : (
                <Button label={t('body.analyse')} onPress={runScan} disabled={!front || !consent} />
              )}
              <Button label={t('body.quiz')} variant="ghost" onPress={() => setMode('quiz')} />
            </>
          )
        ) : null}

        {mode === 'quiz' ? (
          <>
            {scan.result?.needs_confirmation ? <Card inset><Text variant="small">{t('body.lowConfidence')}</Text></Card> : null}
            <Text variant="h3">{t('body.undertoneQ')}</Text>
            <View style={{ gap: 8 }}>
              {UNDERTONES.map((u) => (
                <Choice key={u} label={t(`body.undertone.${u}` as StringKey)} selected={undertone === u} onPress={() => setUndertone(u)} />
              ))}
            </View>
            <Text variant="h3">{t('body.shapeQ')}</Text>
            <View style={{ gap: 8 }}>
              {SHAPES.map((s) => (
                <Choice key={s} label={t(`body.shape.${s}` as StringKey)} selected={shape === s} onPress={() => setShape(s)} />
              ))}
            </View>
            <Button label={t('common.save')} onPress={saveQuiz} loading={saving} disabled={!undertone || !shape} />
          </>
        ) : null}
      </Body>
    </View>
  );
}

function PhotoSlot({ label, uri, onPress }: { label: string; uri: string | null; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} style={{ flex: 1, gap: 6 }}>
      <ItemImage uri={uri} style={{ aspectRatio: 3 / 4 }} />
      <Text variant="small" tone="ink60" style={{ textAlign: 'center' }}>{label}</Text>
    </Pressable>
  );
}

function Choice({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const { c, radius } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="radio" accessibilityState={{ selected }}
               style={{ minHeight: 48, justifyContent: 'center', paddingHorizontal: 16, borderRadius: radius.card,
                        borderWidth: selected ? 2 : 1, borderColor: selected ? c.brand : c.hair,
                        backgroundColor: selected ? c.brandTint : c.surface }}>
      <Text>{label}</Text>
    </Pressable>
  );
}

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Pressable, Image as RNImage, PanResponder, type LayoutChangeEvent } from 'react-native';
import { Image } from 'expo-image';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Field } from '../src/design/components/Field';
import { Header, Body, Card, Loading, Row, Segmented } from '../src/design/components/Screen';
import { useToast } from '../src/ui/toast';
import { useAsync, errorText } from '../src/state/useAsync';
import { api, uploadPhoto, type Landmark, type Landmarks } from '../src/data/api/endpoints';
import { pickPhotos } from '../src/lib/device';
import { t, type StringKey } from '../src/i18n';

const POINTS: Landmark[] = ['head', 'l_shoulder', 'r_shoulder', 'l_hip', 'r_hip', 'feet'];
const START: Landmarks = {
  head: [0.5, 0.06], l_shoulder: [0.39, 0.2], r_shoulder: [0.61, 0.2],
  l_hip: [0.42, 0.48], r_hip: [0.58, 0.48], feet: [0.5, 0.95],
};
const IN = 2.54;
type Step = 'photo' | 'points' | 'measure' | 'privacy';
type Unit = 'cm' | 'in';
const FIELDS = ['height_cm', 'bust_cm', 'waist_cm', 'hips_cm', 'inseam_cm'] as const;
type FieldKey = (typeof FIELDS)[number];

/**
 * The fitting room: one full-length photo of the user, six points they drag onto
 * their body, and their measurements. Private, consented, deletable. Try-on uses
 * these to draw clothes on them at the size they pick.
 */
export default function TryOnSetup() {
  const { next } = useLocalSearchParams<{ next?: string }>();
  const router = useRouter();
  const toast = useToast();
  const { c, radius } = useTheme();
  const existing = useAsync(() => api.tryon.profile());
  const me = useAsync(() => api.account.me());
  const [step, setStep] = useState<Step>('photo');
  const [uri, setUri] = useState<string | null>(null);
  const [aspect, setAspect] = useState(0.66);
  const [points, setPoints] = useState<Landmarks>(START);
  const [unit, setUnit] = useState<Unit>('cm');
  const [vals, setVals] = useState<Partial<Record<FieldKey, string>>>({});
  const [retention, setRetention] = useState<'30d' | 'keep'>('30d');
  const [agree, setAgree] = useState(false);
  const [saving, setSaving] = useState(false);

  const prof = existing.data;
  const photo = uri ?? (prof?.exists ? prof.photo_url ?? null : null);

  useEffect(() => { if (me.data?.units === 'imperial') setUnit('in'); }, [me.data?.units]);
  useEffect(() => {
    if (!prof?.exists) return;
    if (prof.landmarks) setPoints(prof.landmarks);
    if (prof.retention) setRetention(prof.retention);
    const v: Partial<Record<FieldKey, string>> = {};
    for (const k of FIELDS) { const n = prof[k]; if (typeof n === 'number') v[k] = String(Math.round(n)); }
    setVals(v);
  }, [prof]);
  useEffect(() => {
    if (photo) RNImage.getSize(photo, (w, h) => setAspect(w / h), () => {});
  }, [photo]);

  const toCm = (s?: string) => {
    const n = parseFloat((s ?? '').replace(',', '.'));
    return Number.isFinite(n) ? (unit === 'in' ? n * IN : n) : NaN;
  };
  const showUnit = (k: FieldKey, newUnit: Unit) => {
    // keep what's typed meaning the same thing when the unit flips
    const out: Partial<Record<FieldKey, string>> = {};
    for (const f of FIELDS) {
      const n = parseFloat((vals[f] ?? '').replace(',', '.'));
      out[f] = Number.isFinite(n) ? String(Math.round(newUnit === 'in' ? n / IN : n * IN)) : vals[f];
    }
    setVals(out); setUnit(newUnit); void k;
  };
  const required: FieldKey[] = ['height_cm', 'bust_cm', 'waist_cm', 'hips_cm'];
  const measuresOk = required.every((k) => Number.isFinite(toCm(vals[k])));

  const pick = async (src: 'camera' | 'library') => {
    const r = await pickPhotos(src, false);
    if (r === 'denied') return toast({ message: t('capture.permission') });
    if (r[0]) { setUri(r[0]); setPoints(START); setStep('points'); }
  };

  const save = async () => {
    if (!agree || !measuresOk) return;
    setSaving(true);
    try {
      const photo_key = uri ? await uploadPhoto(uri, 'tryon') : undefined;
      const num = (k: FieldKey) => { const n = toCm(vals[k]); return Number.isFinite(n) ? Math.round(n * 10) / 10 : null; };
      await api.tryon.saveProfile({
        photo_key, landmarks: points, retention, consent: true, confirm_self: true,
        height_cm: num('height_cm')!, bust_cm: num('bust_cm')!, waist_cm: num('waist_cm')!, hips_cm: num('hips_cm')!,
        inseam_cm: num('inseam_cm'),
      });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      toast({ message: t('tryon.setup.saved') });
      if (next) router.replace(next as never); else router.back();
    } catch (e) {
      toast({ message: errorText(e) });
    } finally {
      setSaving(false);
    }
  };

  const wipe = async () => {
    await api.tryon.deleteProfile();
    toast({ message: t('tryon.setup.deleted') });
    setUri(null); setPoints(START); setVals({}); existing.refetch();
  };

  if (existing.loading && !existing.data) return <View style={{ flex: 1 }}><Header back title={t('tryon.setup.title')} /><Loading /></View>;

  return (
    <View style={{ flex: 1 }}>
      <Header back eyebrow={t(`tryon.setup.step.${step}` as StringKey)} title={t('tryon.setup.title')} />
      <Body>
        {step === 'photo' ? (
          <>
            <Text tone="ink60">{t('tryon.setup.lead')}</Text>
            <Card>
              {(['tryon.setup.tip1', 'tryon.setup.tip2', 'tryon.setup.tip3', 'tryon.setup.tip4'] as StringKey[]).map((k) => (
                <View key={k} style={{ flexDirection: 'row', gap: 10 }}>
                  <Text tone="brand">✓</Text><Text style={{ flex: 1 }}>{t(k)}</Text>
                </View>
              ))}
            </Card>
            {prof?.exists && photo ? (
              <Image source={{ uri: photo }} style={{ width: '100%', aspectRatio: aspect, borderRadius: radius.card }} contentFit="cover" />
            ) : null}
            <Button label={t('tryon.setup.camera')} onPress={() => pick('camera')} />
            <Button label={t('tryon.setup.library')} variant="secondary" onPress={() => pick('library')} />
            {prof?.exists ? (
              <>
                <Button label={t('tryon.setup.keepPhoto')} variant="ghost" onPress={() => setStep('points')} />
                <Row label={t('tryon.setup.delete')} danger onPress={wipe} />
              </>
            ) : null}
          </>
        ) : null}

        {step === 'points' && photo ? (
          <>
            <Text tone="ink60">{t('tryon.setup.pointsLead')}</Text>
            <PointEditor uri={photo} aspect={aspect} points={points} onChange={setPoints} />
            <Button label={t('common.continue')} onPress={() => setStep('measure')} />
          </>
        ) : null}

        {step === 'measure' ? (
          <>
            <Text tone="ink60">{t('tryon.setup.measureLead')}</Text>
            <Segmented options={[{ value: 'cm', label: 'cm' }, { value: 'in', label: 'in' }]} value={unit}
                       onChange={(u) => showUnit('height_cm', u as Unit)} />
            {FIELDS.map((k) => (
              <Field key={k} label={`${t(`tryon.m.${k}` as StringKey)}${k === 'inseam_cm' ? ` · ${t('common.optional')}` : ''} (${unit})`}
                     keyboardType="decimal-pad" value={vals[k] ?? ''} hint={t(`tryon.m.${k}.hint` as StringKey)}
                     onChangeText={(s) => setVals({ ...vals, [k]: s })} />
            ))}
            <Button label={t('common.continue')} onPress={() => setStep('privacy')} disabled={!measuresOk} />
          </>
        ) : null}

        {step === 'privacy' ? (
          <>
            <Card>
              {(['tryon.setup.p1', 'tryon.setup.p2', 'tryon.setup.p3'] as StringKey[]).map((k) => (
                <Text key={k}>{t(k)}</Text>
              ))}
            </Card>
            <Text variant="label" tone="ink60">{t('tryon.setup.keep')}</Text>
            <Segmented options={[{ value: '30d', label: t('tryon.setup.keep30') }, { value: 'keep', label: t('tryon.setup.keepAlways') }]}
                       value={retention} onChange={(v) => setRetention(v as '30d' | 'keep')} />
            <Pressable onPress={() => setAgree(!agree)} accessibilityRole="checkbox" accessibilityState={{ checked: agree }}
                       style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start' }}>
              <View style={{ width: 24, height: 24, borderRadius: 7, alignItems: 'center', justifyContent: 'center',
                             backgroundColor: agree ? c.action : 'transparent', borderWidth: agree ? 0 : 2, borderColor: c.inactive }}>
                {agree ? <Text style={{ color: c.onAction }}>✓</Text> : null}
              </View>
              <Text variant="small" style={{ flex: 1 }}>{t('tryon.setup.consent')}</Text>
            </Pressable>
            <Button label={t('tryon.setup.save')} onPress={save} loading={saving} disabled={!agree || !measuresOk} />
            <Text variant="small" tone="ink60">{t('tryon.setup.honest')}</Text>
          </>
        ) : null}
      </Body>
    </View>
  );
}

/** The photo with six draggable points (head, shoulders, hips, feet). */
function PointEditor({ uri, aspect, points, onChange }: {
  uri: string; aspect: number; points: Landmarks; onChange: (p: Landmarks) => void;
}) {
  const { c, radius } = useTheme();
  const [box, setBox] = useState({ w: 0, h: 0 });
  const ref = useRef(points);
  ref.current = points;
  const onLayout = (e: LayoutChangeEvent) => setBox({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height });

  const responders = useMemo(() => Object.fromEntries(POINTS.map((name) => {
    let start: [number, number] = [0, 0];
    return [name, PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderGrant: () => { start = ref.current[name]; Haptics.selectionAsync().catch(() => {}); },
      onPanResponderMove: (_, g) => {
        if (!box.w) return;
        const x = Math.min(1, Math.max(0, start[0] + g.dx / box.w));
        const y = Math.min(1, Math.max(0, start[1] + g.dy / box.h));
        onChange({ ...ref.current, [name]: [x, y] });
      },
    })];
  })) as Record<Landmark, ReturnType<typeof PanResponder.create>>, [box.w, box.h, onChange]);

  const sh = points.l_shoulder, sh2 = points.r_shoulder, hp = points.l_hip, hp2 = points.r_hip;
  return (
    <View onLayout={onLayout} style={{ width: '100%', aspectRatio: aspect, borderRadius: radius.card, overflow: 'hidden', backgroundColor: c.mat }}>
      <Image source={{ uri }} style={{ flex: 1 }} contentFit="fill" accessibilityLabel={t('tryon.setup.photoA11y')} />
      {box.w ? (
        <>
          {[[sh, sh2], [hp, hp2]].map(([a, b], i) => (
            <View key={i} pointerEvents="none" style={{ position: 'absolute', left: Math.min(a[0], b[0]) * box.w, top: ((a[1] + b[1]) / 2) * box.h - 1,
                                                        width: Math.abs(b[0] - a[0]) * box.w, height: 2, backgroundColor: c.action, opacity: 0.7 }} />
          ))}
          {POINTS.map((name) => (
            <View key={name} {...responders[name].panHandlers}
                  accessible accessibilityLabel={t(`tryon.pt.${name}` as StringKey)} accessibilityHint={t('tryon.setup.dragHint')}
                  style={{ position: 'absolute', left: points[name][0] * box.w - 22, top: points[name][1] * box.h - 22,
                           width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: c.action, borderWidth: 3, borderColor: '#FFFFFF' }} />
              <Text variant="small" style={{ position: 'absolute', top: 40, color: '#FFFFFF', textShadowColor: '#000', textShadowRadius: 3,
                                              width: 90, textAlign: 'center' }}>
                {t(`tryon.pt.${name}` as StringKey)}
              </Text>
            </View>
          ))}
        </>
      ) : null}
    </View>
  );
}

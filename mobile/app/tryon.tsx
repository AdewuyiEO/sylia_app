import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Pressable, Linking } from 'react-native';
import { Image } from 'expo-image';
import { useLocalSearchParams, useRouter, usePathname } from 'expo-router';
import * as Haptics from 'expo-haptics';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, cancelAnimation, Easing, FadeInDown } from 'react-native-reanimated';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Header, Body, Card, Loading, EmptyState } from '../src/design/components/Screen';
import { useToast } from '../src/ui/toast';
import { errorText } from '../src/state/useAsync';
import { ApiError } from '../src/data/api/client';
import { api, type FitTable, type SizeFit, type TryOnProfile, type TryOnRender, type TryTarget, type FitLabel } from '../src/data/api/endpoints';
import { t, type StringKey } from '../src/i18n';

const POLL_MS = 700;
const POLL_LIMIT = 60;

/**
 * Try-on (Sylia Pro): the user, in this piece, in the size they pick. Sylia
 * suggests a size from their measurements and says why; the user decides.
 * Opened from Discover (product_id) or a closet piece (item_id).
 */
export default function TryOnScreen() {
  const params = useLocalSearchParams<{ item_id?: string; product_id?: string; title?: string; rid?: string }>();
  const target: TryTarget | null = params.item_id ? { item_id: params.item_id }
    : params.product_id ? { product_id: params.product_id } : null;
  const router = useRouter();
  const path = usePathname();
  const toast = useToast();
  const { c, radius } = useTheme();
  const [profile, setProfile] = useState<TryOnProfile | null>(null);
  const [fit, setFit] = useState<FitTable | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState<string | null>(null);
  const [renders, setRenders] = useState<Record<string, TryOnRender>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [view, setView] = useState<'after' | 'before'>('after');
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const load = useCallback(async () => {
    if (!target) return;
    setError(null);
    try {
      const p = await api.tryon.profile();
      setProfile(p);
      if (!p.exists) return;
      const f = await api.tryon.fit(target);
      setFit(f);
      setSize((s) => s ?? f.recommended ?? f.sizes[0]?.size ?? null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) { router.replace('/paywall?reason=tryon'); return; }
      setError(errorText(e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.item_id, params.product_id]);
  useEffect(() => { load(); }, [load]);

  const tryOn = useCallback(async (s: string) => {
    if (!target || renders[s] || busy) return;
    setBusy(s); setView('after');
    try {
      const { job_id } = await api.tryon.render(target, s);
      for (let i = 0; i < POLL_LIMIT && alive.current; i++) {
        const j = await api.tryon.job(job_id);
        if (j.status === 'done' && j.result) {
          setRenders((r) => ({ ...r, [s]: j.result as TryOnRender }));
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
          return;
        }
        if (j.status === 'failed') throw new Error(j.error ?? t('tryon.failed'));
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) { router.replace('/paywall?reason=tryon'); return; }
      toast({ message: errorText(e) });
    } finally {
      if (alive.current) setBusy(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renders, busy, params.item_id, params.product_id]);

  useEffect(() => { if (size && fit?.renderable) tryOn(size); }, [size, fit?.renderable]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!target) return <View style={{ flex: 1 }}><Header back title={t('tryon.title')} /><Body><EmptyState title={t('tryon.nothing')} /></Body></View>;
  if (error) return <View style={{ flex: 1 }}><Header back title={t('tryon.title')} /><Body><EmptyState title={error} primary={{ label: t('common.tryAgain'), onPress: load }} /></Body></View>;
  if (!profile) return <View style={{ flex: 1 }}><Header back title={t('tryon.title')} /><Loading /></View>;

  if (!profile.exists) {
    return (
      <View style={{ flex: 1 }}>
        <Header back title={t('tryon.title')} />
        <Body>
          <EmptyState title={t('tryon.needSetup.title')} body={t('tryon.needSetup.body')}
                      primary={{ label: t('tryon.needSetup.cta'), onPress: () => router.push({ pathname: '/tryon-setup', params: { next: path + paramsQuery(params) } }) }} />
        </Body>
      </View>
    );
  }
  if (!fit) return <View style={{ flex: 1 }}><Header back title={t('tryon.title')} /><Loading label={t('tryon.reading')} /></View>;

  const sel = fit.sizes.find((s) => s.size === size) ?? null;
  const shot = size ? renders[size] : undefined;
  const showAfter = view === 'after' && !!shot;

  const shop = async () => {
    if (!params.rid) return;
    try { const { url } = await api.discover.click(params.rid); await Linking.openURL(url); }
    catch (e) { toast({ message: errorText(e) }); }
  };

  return (
    <View style={{ flex: 1 }}>
      <Header back eyebrow={t('tryon.eyebrow')} title={params.title ?? t('tryon.title')} />
      <Body>
        <View style={{ width: '100%', aspectRatio: 0.72, borderRadius: radius.card, overflow: 'hidden', backgroundColor: c.mat }}>
          <Image source={{ uri: showAfter ? shot!.image_url : profile.photo_url }} style={{ flex: 1 }} contentFit="cover"
                 transition={{ duration: 450, effect: 'cross-dissolve' }}
                 accessibilityLabel={showAfter ? t('tryon.a11y.after', { size: size ?? '' }) : t('tryon.a11y.before')} />
          {busy ? <Scan /> : null}
          {busy ? (
            <View style={{ position: 'absolute', alignSelf: 'center', top: '45%', paddingHorizontal: 16, height: 40, borderRadius: 20,
                           backgroundColor: 'rgba(36,28,20,0.82)', justifyContent: 'center' }} accessibilityLiveRegion="polite">
              <Text variant="bodyStrong" style={{ color: '#F2EAE0' }}>{t('tryon.draping', { size: busy })}</Text>
            </View>
          ) : null}
          <View style={{ position: 'absolute', left: 12, top: 12, height: 26, paddingHorizontal: 10, borderRadius: 13,
                         backgroundColor: 'rgba(36,28,20,0.72)', justifyContent: 'center' }}>
            <Text variant="small" style={{ color: '#F2EAE0', fontFamily: 'Inter_600SemiBold' }}>{t('tryon.badge')}</Text>
          </View>
          {shot ? (
            <View style={{ position: 'absolute', bottom: 12, alignSelf: 'center', flexDirection: 'row', padding: 3, borderRadius: 20,
                           backgroundColor: 'rgba(36,28,20,0.8)' }} accessibilityRole="radiogroup">
              {(['before', 'after'] as const).map((v) => (
                <Pressable key={v} onPress={() => setView(v)} accessibilityRole="radio" accessibilityState={{ checked: view === v }}
                           style={{ height: 34, paddingHorizontal: 14, borderRadius: 17, justifyContent: 'center',
                                    backgroundColor: view === v ? '#F2EAE0' : 'transparent' }}>
                  <Text variant="small" style={{ fontFamily: 'Inter_600SemiBold', color: view === v ? '#241C14' : '#B8A794' }}>
                    {t(v === 'before' ? 'tryon.before' : 'tryon.onYou')}
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : null}
        </View>

        {!fit.renderable ? <Text variant="small" tone="ink60">{t('tryon.notRenderable')}</Text> : null}

        <Text variant="label" tone="ink60">{t('tryon.pickSize')}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {fit.sizes.map((s) => (
            <SizeChip key={s.size} fit={s} selected={s.size === size} pick={s.size === fit.recommended}
                      onPress={() => { Haptics.selectionAsync().catch(() => {}); setSize(s.size); }} />
          ))}
        </View>

        {sel ? (
          <Animated.View key={sel.size} entering={FadeInDown.duration(300)}>
            <Card>
              <Text variant="h3">{sel.size === fit.recommended ? t('tryon.pickHeadline', { size: sel.size }) : t('tryon.sizeHeadline', { size: sel.size })}</Text>
              {sel.zones.map((z) => (
                <View key={z.zone} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <Text variant="small" tone="ink60" style={{ width: 64 }}>{t(`tryon.zone.${z.zone}` as StringKey)}</Text>
                  <View style={{ flex: 1, height: 6, borderRadius: 3, backgroundColor: c.inset, overflow: 'hidden' }}>
                    <View style={{ height: 6, borderRadius: 3, width: `${barWidth(z.ease_cm)}%`, backgroundColor: labelColor(z.label, c) }} />
                  </View>
                  <Text variant="small" style={{ width: 96, textAlign: 'right' }}>{t(`tryon.fit.${z.label}` as StringKey)}</Text>
                </View>
              ))}
              <Text variant="small" tone="ink60">{sel.explanation}</Text>
              <Text variant="small" tone="ink40">{t(`tryon.source.${fit.chart_source}` as StringKey)}</Text>
            </Card>
          </Animated.View>
        ) : null}

        {params.rid && size ? <Button label={t('tryon.shop', { size })} onPress={shop} /> : null}
        <Text variant="small" tone="ink60">{t('tryon.disclaimer')}</Text>
      </Body>
    </View>
  );
}

function paramsQuery(p: Record<string, string | undefined>) {
  const q = Object.entries(p).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`).join('&');
  return q ? `?${q}` : '';
}

function barWidth(ease: number) {
  return Math.max(6, Math.min(100, ((ease + 6) / 30) * 100));
}

function labelColor(l: FitLabel, c: ReturnType<typeof useTheme>['c']) {
  return l === 'too_tight' ? c.critical : l === 'fitted' ? c.occasion : l === 'comfortable' ? c.brand : c.weather;
}

function SizeChip({ fit, selected, pick, onPress }: { fit: SizeFit; selected: boolean; pick: boolean; onPress: () => void }) {
  const { c } = useTheme();
  const worst = fit.tight ? 'too_tight' : fit.zones.some((z) => z.label === 'fitted') ? 'fitted' : fit.zones[0]?.label ?? 'comfortable';
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected }}
               accessibilityLabel={`${fit.size}${pick ? `, ${t('tryon.syliaPick')}` : ''}, ${t(`tryon.fit.${worst}` as StringKey)}`}
               style={{ minWidth: 56, minHeight: 48, paddingHorizontal: 12, borderRadius: 12, alignItems: 'center', justifyContent: 'center', gap: 4,
                        backgroundColor: selected ? c.ink : c.surface, borderWidth: 1, borderColor: selected ? c.ink : c.hair }}>
      <Text variant="bodyStrong" style={{ color: selected ? c.bg : c.ink }}>{fit.size}</Text>
      <View style={{ flexDirection: 'row', gap: 4, alignItems: 'center' }}>
        <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: labelColor(worst as FitLabel, c) }} />
        {pick ? <Text variant="small" style={{ fontSize: 10, color: selected ? c.bg : c.action }}>{t('tryon.syliaPick')}</Text> : null}
      </View>
    </Pressable>
  );
}

/** The scan line that sweeps while a size drapes. */
function Scan() {
  const y = useSharedValue(0);
  useEffect(() => {
    y.value = withRepeat(withTiming(1, { duration: 1200, easing: Easing.inOut(Easing.quad) }), -1, true);
    return () => cancelAnimation(y);
  }, [y]);
  const style = useAnimatedStyle(() => ({ top: `${y.value * 100}%` }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: 'absolute', left: 0, right: 0, height: 2, backgroundColor: '#E2703F',
                                                 shadowColor: '#E2703F', shadowOpacity: 0.9, shadowRadius: 10 }, style]} />
  );
}

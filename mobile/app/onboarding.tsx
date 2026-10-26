import React, { useEffect, useRef, useState } from 'react';
import { View, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Field } from '../src/design/components/Field';
import { Header } from '../src/design/components/Screen';
import { useOnboarding } from '../src/state/hooks';
import { t } from '../src/i18n';

/** Step 1: the text-first identity chat. Extraction and progressive unlock are server-side. */
export default function OnboardingScreen() {
  const { c, layout, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { turns, complete, busy, error, start, say } = useOnboarding();
  const [draft, setDraft] = useState('');
  const scroll = useRef<ScrollView>(null);

  useEffect(() => { start(); }, [start]);

  const submit = () => {
    const text = draft.trim();
    if (!text || busy || complete) return;
    setDraft('');
    say(text);
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Header eyebrow={t('onboarding.eyebrow')} title={t('onboarding.title')} />
      <ScrollView ref={scroll} style={{ flex: 1 }} onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}
                  contentContainerStyle={{ padding: layout.gutter, gap: 12 }}>
        {turns.map((turn, i) => {
          const mine = turn.role === 'user';
          return (
            <View key={i} style={{ maxWidth: '84%', alignSelf: mine ? 'flex-end' : 'flex-start',
              backgroundColor: mine ? c.brand : c.surface, borderRadius: radius.card,
              borderWidth: mine ? 0 : 1, borderColor: c.hair, paddingHorizontal: 14, paddingVertical: 10 }}>
              <Text style={{ color: mine ? c.surface : c.ink }}>{turn.text}</Text>
            </View>
          );
        })}
        {busy ? <Text variant="small" tone="ink60">…</Text> : null}
        {error ? <Text variant="small" tone="action">{error}</Text> : null}
      </ScrollView>

      <View style={{ paddingHorizontal: layout.gutter, paddingTop: 8, paddingBottom: insets.bottom + 8,
                     borderTopWidth: 1, borderTopColor: c.hair, gap: 8 }}>
        {complete ? (
          <Button label={t('onboarding.next')} onPress={() => router.replace('/body?onboarding=1')} />
        ) : (
          <View style={{ flexDirection: 'row', gap: 8, alignItems: 'flex-end' }}>
            <View style={{ flex: 1 }}>
              <Field placeholder={t('onboarding.placeholder')} value={draft} onChangeText={setDraft}
                     multiline style={{ maxHeight: 120 }} accessibilityLabel={t('onboarding.placeholder')} />
            </View>
            <Button label={t('onboarding.send')} onPress={submit} variant="tertiary" disabled={!draft.trim() || busy}
                    style={{ alignSelf: 'auto', width: 84 }} />
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

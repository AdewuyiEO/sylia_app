import React, { useEffect, useRef, useState } from 'react';
import { View, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../../src/design/theme';
import { Text } from '../../src/design/components/Text';
import { Button } from '../../src/design/components/Button';
import { Field } from '../../src/design/components/Field';
import { Header } from '../../src/design/components/Screen';
import { useCoach } from '../../src/state/hooks';
import { t } from '../../src/i18n';

/** Style coach chat. Retrieval, persona and guardrails all live server-side. */
export default function CoachScreen() {
  const { c, layout, radius } = useTheme();
  const router = useRouter();
  const { turns, busy, needsPro, error, send, reset, clearNeedsPro } = useCoach();
  const [draft, setDraft] = useState('');
  const scroll = useRef<ScrollView>(null);

  useEffect(() => {
    if (needsPro) {
      clearNeedsPro();
      router.push('/paywall?reason=coach');
    }
  }, [needsPro]);

  const submit = () => {
    const text = draft.trim();
    if (!text || busy) return;
    setDraft('');
    send(text);
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Header title={t('coach.title')} subtitle={t('coach.sub')}
              right={turns.length ? <Button label={t('coach.new')} variant="ghost" onPress={reset} style={{ alignSelf: 'auto' }} /> : undefined} />
      <ScrollView ref={scroll} style={{ flex: 1 }} onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}
                  contentContainerStyle={{ padding: layout.gutter, gap: 10 }} keyboardShouldPersistTaps="handled">
        {turns.length === 0 ? <Text tone="ink60">{t('coach.empty')}</Text> : null}
        {turns.map((turn, i) => {
          const mine = turn.role === 'user';
          return (
            <View key={i} style={{ maxWidth: '86%', alignSelf: mine ? 'flex-end' : 'flex-start',
              backgroundColor: mine ? c.brand : c.surface, borderRadius: radius.card,
              borderWidth: mine ? 0 : 1, borderColor: c.hair, paddingHorizontal: 14, paddingVertical: 10 }}>
              <Text selectable style={{ color: mine ? c.surface : c.ink }}>{turn.text}</Text>
            </View>
          );
        })}
        {busy ? <Text variant="small" tone="ink60">{t('coach.thinking')}</Text> : null}
        {error ? <Text variant="small" tone="action">{error}</Text> : null}
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 8, alignItems: 'flex-end', paddingHorizontal: layout.gutter,
                     paddingVertical: 8, borderTopWidth: 1, borderTopColor: c.hair }}>
        <View style={{ flex: 1 }}>
          <Field placeholder={t('coach.placeholder')} value={draft} onChangeText={setDraft} multiline
                 style={{ maxHeight: 120 }} accessibilityLabel={t('coach.placeholder')} />
        </View>
        <Button label={t('onboarding.send')} variant="tertiary" onPress={submit} disabled={!draft.trim() || busy}
                style={{ alignSelf: 'auto', width: 84 }} />
      </View>
    </KeyboardAvoidingView>
  );
}

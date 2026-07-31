import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TextInput, Pressable, KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../src/design/theme';
import { useOnboarding } from '../src/state/hooks';

/**
 * Identity onboarding — the text-first chat that builds the style profile.
 * Renders useOnboarding()'s turns; on completion, routes into the app. The
 * extraction/progressive-unlock logic is all server-side.
 */
export default function OnboardingScreen() {
  const { c, type, layout, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { turns, complete, busy, start, say } = useOnboarding();
  const [draft, setDraft] = useState('');

  useEffect(() => { start(); }, [start]);
  useEffect(() => { if (complete) { const t = setTimeout(() => router.replace('/(tabs)/today'), 1200); return () => clearTimeout(t); } }, [complete, router]);

  const submit = () => {
    const t = draft.trim();
    if (!t || busy || complete) return;
    setDraft('');
    say(t);
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.paper }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={{ paddingTop: insets.top + 12, paddingHorizontal: layout.gutter, paddingBottom: 8 }}>
        <Text style={{ ...type.micro, color: c.slate }}>GETTING TO KNOW YOU</Text>
        <Text style={{ ...type.displayL, color: c.ink }}>A few questions</Text>
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: layout.gutter, gap: 12 }}>
        {turns.map((t, i) => (
          <View key={i} style={[
            styles.bubble,
            { borderRadius: radius.control,
              alignSelf: t.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: t.role === 'user' ? c.ink : c.chalk }]}>
            <Text style={{ ...type.body, color: t.role === 'user' ? c.paper : c.ink }}>{t.text}</Text>
          </View>
        ))}
        {busy ? <Text style={{ ...type.caption, color: c.slate }}>…</Text> : null}
      </ScrollView>

      {!complete ? (
        <View style={[styles.inputRow, { paddingHorizontal: layout.gutter, paddingBottom: insets.bottom + 8, borderTopColor: c.mist }]}>
          <TextInput
            style={[styles.input, { color: c.ink, backgroundColor: c.chalk, borderRadius: radius.control }]}
            placeholder="Type your answer" placeholderTextColor={c.slate}
            value={draft} onChangeText={setDraft} onSubmitEditing={submit} returnKeyType="send" multiline />
          <Pressable onPress={submit} style={[styles.send, { backgroundColor: c.ink, borderRadius: radius.control }]}>
            <Text style={{ ...type.body, color: c.paper, fontWeight: '600' }}>Send</Text>
          </Pressable>
        </View>
      ) : null}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  bubble: { maxWidth: '82%', paddingHorizontal: 14, paddingVertical: 10 },
  inputRow: { flexDirection: 'row', gap: 8, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth },
  input: { flex: 1, paddingHorizontal: 14, paddingVertical: 10, minHeight: 44, maxHeight: 120 },
  send: { paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center' },
});

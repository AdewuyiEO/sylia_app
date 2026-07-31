import React, { useState } from 'react';
import { View, Text, ScrollView, TextInput, Pressable, KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../src/design/theme';
import { useCoach } from '../src/state/hooks';

/**
 * Style Coach — chat over useCoach(). Pure presentation: a message list + input.
 * The RAG/streaming all happens server-side; this screen just sends text and
 * renders turns. Redesign the bubbles freely; useCoach() stays.
 */
export default function CoachScreen() {
  const { c, type, layout, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const { turns, busy, send } = useCoach();
  const [draft, setDraft] = useState('');

  const submit = () => {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft('');
    send(t);
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.paper }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={{ paddingTop: insets.top + 8, paddingHorizontal: layout.gutter, paddingBottom: 8 }}>
        <Text style={{ ...type.displayL, color: c.ink }}>Coach</Text>
        <Text style={{ ...type.caption, color: c.slate }}>Packing, feedback, what-to-wear</Text>
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: layout.gutter, gap: 10 }}>
        {turns.length === 0 ? (
          <Text style={{ ...type.body, color: c.slate }}>
            Ask me anything — “what works for a client dinner?”, “help me pack for 3 days”.
          </Text>
        ) : null}
        {turns.map((t, i) => (
          <View key={i} style={[
            styles.bubble,
            { borderRadius: radius.control,
              alignSelf: t.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: t.role === 'user' ? c.ink : c.chalk }]}>
            <Text style={{ ...type.body, color: t.role === 'user' ? c.paper : c.ink }}>{t.text}</Text>
          </View>
        ))}
        {busy ? <Text style={{ ...type.caption, color: c.slate }}>Sylia is thinking…</Text> : null}
      </ScrollView>

      <View style={[styles.inputRow, { paddingHorizontal: layout.gutter, paddingBottom: insets.bottom + 8, borderTopColor: c.mist }]}>
        <TextInput
          style={[styles.input, { color: c.ink, backgroundColor: c.chalk, borderRadius: radius.control }]}
          placeholder="Message Sylia" placeholderTextColor={c.slate}
          value={draft} onChangeText={setDraft} onSubmitEditing={submit} returnKeyType="send" />
        <Pressable onPress={submit} style={[styles.send, { backgroundColor: c.ink, borderRadius: radius.control }]}>
          <Text style={{ ...type.body, color: c.paper, fontWeight: '600' }}>Send</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  bubble: { maxWidth: '82%', paddingHorizontal: 14, paddingVertical: 10 },
  inputRow: { flexDirection: 'row', gap: 8, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth },
  input: { flex: 1, paddingHorizontal: 14, paddingVertical: 10, minHeight: 44 },
  send: { paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center' },
});

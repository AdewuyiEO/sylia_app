import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../src/design/theme';
import { Button } from '../src/design/components/Button';
import { useAuth } from '../src/state/auth';

/**
 * Auth screen. Purely presentational — it collects email/password and calls the
 * auth store. Restyle freely: the only contract is calling login()/signup().
 */
export default function AuthScreen() {
  const { c, type, space, radius, layout } = useTheme();
  const insets = useSafeAreaInsets();
  const { login, signup, busy, error } = useAuth();

  const [mode, setMode] = useState<'login' | 'signup'>('signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const submit = () => {
    if (mode === 'login') login(email.trim(), password);
    else signup(email.trim(), password);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: c.paper }}
    >
      <View style={[styles.wrap, { paddingTop: insets.top + 60, paddingHorizontal: layout.gutter }]}>
        <Text style={{ ...type.displayL, color: c.ink }}>Sylia</Text>
        <Text style={{ ...type.body, color: c.slate, marginTop: space.s2, marginBottom: space.s7 }}>
          {mode === 'signup' ? 'Create your account to get styled.' : 'Welcome back.'}
        </Text>

        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="Email"
          placeholderTextColor={c.slate}
          autoCapitalize="none"
          keyboardType="email-address"
          style={[styles.input, { color: c.ink, backgroundColor: c.chalk, borderRadius: radius.control }]}
        />
        <TextInput
          value={password}
          onChangeText={setPassword}
          placeholder="Password"
          placeholderTextColor={c.slate}
          secureTextEntry
          style={[styles.input, { color: c.ink, backgroundColor: c.chalk, borderRadius: radius.control, marginTop: space.s3 }]}
        />

        {error ? (
          <Text style={{ ...type.caption, color: c.signal, marginTop: space.s3 }}>{error}</Text>
        ) : null}

        <Button
          label={busy ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Log in'}
          onPress={submit}
          variant="signal"
          fill
          style={{ marginTop: space.s5 }}
        />
        <Button
          label={mode === 'signup' ? 'I already have an account' : 'Create a new account'}
          onPress={() => setMode(mode === 'signup' ? 'login' : 'signup')}
          variant="ghost"
          fill
          style={{ marginTop: space.s2 }}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  input: { height: 52, paddingHorizontal: 16, fontSize: 16 },
});

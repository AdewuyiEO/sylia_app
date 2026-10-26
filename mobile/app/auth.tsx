import React, { useEffect, useState } from 'react';
import { View, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import * as AppleAuthentication from 'expo-apple-authentication';
import * as WebBrowser from 'expo-web-browser';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../src/design/theme';
import { Text } from '../src/design/components/Text';
import { Button } from '../src/design/components/Button';
import { Field } from '../src/design/components/Field';
import { Body } from '../src/design/components/Screen';
import { useAuth } from '../src/state/auth';
import { LEGAL } from '../src/data/api/config';
import { t } from '../src/i18n';

/** Sign up / log in. Sign in with Apple first on iOS; email below it. */
export default function AuthScreen() {
  const { c, scheme, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { login, signup, apple, busy, error } = useAuth();
  const [mode, setMode] = useState<'signup' | 'login'>('signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [appleOk, setAppleOk] = useState(false);

  useEffect(() => {
    AppleAuthentication.isAvailableAsync().then(setAppleOk).catch(() => setAppleOk(false));
  }, []);

  const afterAuth = (isNew: boolean) => router.replace(isNew ? '/onboarding' : '/today');

  const submit = async () => {
    const ok = mode === 'login' ? await login(email.trim(), password) : await signup(email.trim(), password);
    if (ok) afterAuth(mode === 'signup');
  };

  const withApple = async () => {
    try {
      const cred = await AppleAuthentication.signInAsync({
        requestedScopes: [AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
                          AppleAuthentication.AppleAuthenticationScope.EMAIL],
      });
      if (!cred.identityToken) return;
      const name = [cred.fullName?.givenName, cred.fullName?.familyName].filter(Boolean).join(' ') || null;
      // Apple only shares the name on the very first sign-in, so a name means a new account
      if (await apple(cred.identityToken, name)) afterAuth(!!name);
    } catch (e: any) {
      if (e?.code !== 'ERR_REQUEST_CANCELED') useAuth.setState({ error: t('common.offline') });
    }
  };

  const tooShort = mode === 'signup' && password.length > 0 && password.length < 8;

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: c.bg }}>
      <Body contentStyle={{ paddingTop: insets.top + 56, gap: 20 }}>
        <View style={{ gap: 8 }}>
          <Text variant="display" accessibilityRole="header">Sylia</Text>
          <Text variant="h2" tone="ink60">{t('auth.tagline')}</Text>
        </View>
        <Text tone="ink60">{mode === 'signup' ? t('auth.signupLead') : t('auth.loginLead')}</Text>

        {appleOk ? (
          <>
            <AppleAuthentication.AppleAuthenticationButton
              buttonType={mode === 'signup' ? AppleAuthentication.AppleAuthenticationButtonType.SIGN_UP
                                            : AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
              buttonStyle={scheme === 'dark' ? AppleAuthentication.AppleAuthenticationButtonStyle.WHITE
                                             : AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
              cornerRadius={radius.btn}
              style={{ height: 48 }}
              onPress={withApple}
            />
            <Text variant="small" tone="ink40" style={{ textAlign: 'center' }}>{t('auth.or')}</Text>
          </>
        ) : null}

        <Field label={t('auth.email')} value={email} onChangeText={setEmail} autoCapitalize="none"
               autoComplete="email" keyboardType="email-address" textContentType="emailAddress" />
        <Field label={t('auth.password')} value={password} onChangeText={setPassword} secureTextEntry
               textContentType={mode === 'signup' ? 'newPassword' : 'password'}
               autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
               hint={mode === 'signup' ? t('auth.passwordHint') : undefined}
               error={tooShort ? t('auth.passwordHint') : error} onSubmitEditing={submit} returnKeyType="go" />

        <Button label={busy ? t('auth.wait') : mode === 'signup' ? t('auth.create') : t('auth.login')}
                onPress={submit} loading={busy} disabled={!email || password.length < (mode === 'signup' ? 8 : 1)} />
        <Button variant="ghost" label={mode === 'signup' ? t('auth.haveAccount') : t('auth.newAccount')}
                onPress={() => { useAuth.setState({ error: null }); setMode(mode === 'signup' ? 'login' : 'signup'); }} />

        <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 16 }}>
          <Text variant="small" tone="ink60" style={{ textAlign: 'center', width: '100%' }}>{t('auth.legal')}</Text>
          <Text variant="small" tone="brand" accessibilityRole="link" onPress={() => WebBrowser.openBrowserAsync(LEGAL.terms)}>
            {t('auth.terms')}
          </Text>
          <Text variant="small" tone="brand" accessibilityRole="link" onPress={() => WebBrowser.openBrowserAsync(LEGAL.privacy)}>
            {t('auth.privacy')}
          </Text>
        </View>
      </Body>
    </KeyboardAvoidingView>
  );
}

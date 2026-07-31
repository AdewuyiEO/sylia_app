import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider } from '../src/design/theme';
import { ToastProvider } from '../src/ui/toast';
import { useAuth } from '../src/state/auth';

/**
 * Root layout. Wraps the whole app in the providers every screen relies on, and
 * gates on auth: an unauthenticated user is sent to /auth; an authenticated one
 * into the tabs. The gate is logic — the /auth SCREEN is where design lives.
 */
function AuthGate() {
  const status = useAuth((s) => s.status);
  const hydrate = useAuth((s) => s.hydrate);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    if (status === 'unknown') return;
    const onAuthScreen = segments[0] === 'auth';
    if (status === 'guest' && !onAuthScreen) router.replace('/auth');
    else if (status === 'authed' && onAuthScreen) router.replace('/today');
  }, [status, segments]);

  return <Stack screenOptions={{ headerShown: false }} />;
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <ToastProvider>
            <StatusBar style="auto" />
            <AuthGate />
          </ToastProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

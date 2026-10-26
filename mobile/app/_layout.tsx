import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts, Fraunces_600SemiBold } from '@expo-google-fonts/fraunces';
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from '@expo-google-fonts/inter';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, useTheme } from '../src/design/theme';
import { ToastProvider } from '../src/ui/toast';
import { useAuth } from '../src/state/auth';

SplashScreen.preventAutoHideAsync().catch(() => {});

/**
 * Root layout: providers every screen relies on, plus the auth gate — signed-out
 * users go to /auth, signed-in users never see it.
 */
function AuthGate() {
  const status = useAuth((s) => s.status);
  const hydrate = useAuth((s) => s.hydrate);
  const router = useRouter();
  const segments = useSegments();
  const { c, scheme } = useTheme();

  useEffect(() => {
    hydrate();
  }, []);

  const prev = React.useRef(status);
  useEffect(() => {
    const was = prev.current;
    prev.current = status;
    if (status === 'unknown') return;
    SplashScreen.hideAsync().catch(() => {});
    const onAuth = segments[0] === 'auth';
    if (status === 'guest' && !onAuth) router.replace('/auth');
    // only on launch: a fresh sign-in routes itself (new accounts go to onboarding)
    else if (status === 'authed' && onAuth && was === 'unknown') router.replace('/today');
  }, [status, segments]);

  return (
    <>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }}>
        <Stack.Screen name="capture" options={{ presentation: 'modal' }} />
        <Stack.Screen name="paywall" options={{ presentation: 'modal' }} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({ Fraunces_600SemiBold, Inter_400Regular, Inter_500Medium, Inter_600SemiBold });
  if (!fontsLoaded && !fontError) return null;   // splash stays up until fonts are ready

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <ToastProvider>
            <AuthGate />
          </ToastProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

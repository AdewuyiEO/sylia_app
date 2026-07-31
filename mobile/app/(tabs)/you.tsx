import React from 'react';
import { View, Text, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../../src/design/theme';
import { useAuth } from '../../src/state/auth';
import { useAsync } from '../../src/state/useAsync';
import { api } from '../../src/data/api/endpoints';

/**
 * You — profile hub: subscription status + entry points to coach/onboarding.
 * Reads billing via useAsync; actions are navigation + logout. Pure presentation.
 */
export default function YouScreen() {
  const { c, type, layout, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const logout = useAuth((s) => s.logout);
  const { data: billing, loading } = useAsync(() => api.billing.status());

  const Row = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable onPress={onPress}
      style={[styles.row, { backgroundColor: c.chalk, borderRadius: radius.control }]}>
      <Text style={{ ...type.body, color: c.ink }}>{label}</Text>
      <Text style={{ ...type.body, color: c.slate }}>›</Text>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: c.paper, paddingTop: insets.top + 8, paddingHorizontal: layout.gutter }}>
      <Text style={{ ...type.displayL, color: c.ink, marginBottom: 4 }}>You</Text>

      <View style={[styles.card, { backgroundColor: c.ink, borderRadius: radius.content }]}>
        {loading ? <ActivityIndicator color={c.paper} /> : (
          <>
            <Text style={{ ...type.caption, color: c.paper, opacity: 0.7 }}>SUBSCRIPTION</Text>
            <Text style={{ ...type.title, color: c.paper }}>
              {billing?.entitled ? (billing.in_trial ? 'Free trial' : 'Sylia Pro') : 'Inactive'}
            </Text>
            {!billing?.entitled ? (
              <Pressable onPress={() => api.billing.checkout().then((r) => console.log(r.checkout_url))}
                style={[styles.cta, { backgroundColor: c.paper, borderRadius: radius.control }]}>
                <Text style={{ ...type.body, color: c.ink, fontWeight: '600' }}>
                  Subscribe · ${billing?.price_usd ?? 19}/mo
                </Text>
              </Pressable>
            ) : null}
          </>
        )}
      </View>

      <View style={{ gap: 8, marginTop: 20 }}>
        <Row label="Style coach" onPress={() => router.push('/coach')} />
        <Row label="Redo style profile" onPress={() => router.push('/onboarding')} />
        <Row label="Log out" onPress={logout} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { padding: 20, marginTop: 16, gap: 6 },
  cta: { alignSelf: 'flex-start', marginTop: 12, paddingHorizontal: 16, paddingVertical: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
});

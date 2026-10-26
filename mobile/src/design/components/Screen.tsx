import React from 'react';
import { View, ScrollView, ActivityIndicator, Pressable, type ScrollViewProps, type ViewStyle, RefreshControl } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useTheme } from '../theme';
import { Text } from './Text';
import { Button } from './Button';

/** Screen title block: optional eyebrow, Fraunces H1, optional subtitle and back. */
export function Header({ eyebrow, title, subtitle, back, right }: {
  eyebrow?: string; title: string; subtitle?: string; back?: boolean; right?: React.ReactNode;
}) {
  const { layout } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  return (
    <View style={{ paddingTop: insets.top + 8, paddingHorizontal: layout.gutter, paddingBottom: 12, gap: 4 }}>
      {back ? (
        <Pressable accessibilityRole="button" accessibilityLabel="Back" hitSlop={12}
                   onPress={() => router.back()} style={{ minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start' }}>
          <Text variant="h3" tone="brand">‹</Text>
        </Pressable>
      ) : null}
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
        <View style={{ flex: 1, gap: 4 }}>
          {eyebrow ? <Text variant="label" tone="ink60">{eyebrow}</Text> : null}
          <Text variant="h1" accessibilityRole="header">{title}</Text>
        </View>
        {right}
      </View>
      {subtitle ? <Text variant="small" tone="ink60">{subtitle}</Text> : null}
    </View>
  );
}

/** Scrolling screen body on bone, with pull-to-refresh when given onRefresh. */
export function Body({ children, onRefresh, refreshing, contentStyle, ...rest }: ScrollViewProps & {
  onRefresh?: () => void; refreshing?: boolean; contentStyle?: ViewStyle;
}) {
  const { c, layout } = useTheme();
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={[{ paddingHorizontal: layout.gutter, paddingBottom: 40, gap: 16 }, contentStyle]}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={c.brand} /> : undefined}
      {...rest}
    >
      {children}
    </ScrollView>
  );
}

export function Card({ children, style, inset }: { children: React.ReactNode; style?: ViewStyle; inset?: boolean }) {
  const { c, radius } = useTheme();
  return (
    <View style={[{ backgroundColor: inset ? c.inset : c.surface, borderRadius: radius.card, padding: 16,
                    borderWidth: inset ? 0 : 1, borderColor: c.hair, gap: 12 }, style]}>
      {children}
    </View>
  );
}

export function Loading({ label }: { label?: string }) {
  const { c } = useTheme();
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 32, minHeight: 240 }}>
      <ActivityIndicator color={c.brand} />
      {label ? <Text variant="small" tone="ink60">{label}</Text> : null}
    </View>
  );
}

/** Every empty/error state routes through this so none is a dead end. */
export function EmptyState({ title, body, primary, secondary }: {
  title: string; body?: string;
  primary?: { label: string; onPress: () => void };
  secondary?: { label: string; onPress: () => void };
}) {
  return (
    <View style={{ alignItems: 'center', justifyContent: 'center', paddingVertical: 48, paddingHorizontal: 12, gap: 8 }}>
      <Text variant="h2" style={{ textAlign: 'center' }}>{title}</Text>
      {body ? <Text tone="ink60" style={{ textAlign: 'center', maxWidth: 320 }}>{body}</Text> : null}
      <View style={{ alignSelf: 'stretch', gap: 8, marginTop: 16 }}>
        {primary ? <Button label={primary.label} onPress={primary.onPress} /> : null}
        {secondary ? <Button label={secondary.label} onPress={secondary.onPress} variant="secondary" /> : null}
      </View>
    </View>
  );
}

export function Row({ label, value, onPress, danger }: { label: string; value?: string; onPress?: () => void; danger?: boolean }) {
  const { c, radius } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : 'text'}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
        minHeight: 52, paddingHorizontal: 16, backgroundColor: pressed ? c.inset : c.surface,
        borderRadius: radius.card, borderWidth: 1, borderColor: c.hair })}
    >
      <Text tone={danger ? 'critical' : 'ink'}>{label}</Text>
      <Text tone="ink60">{value ?? (onPress ? '›' : '')}</Text>
    </Pressable>
  );
}

/** Segmented choice (units, coverage…) — selected goes olive. */
export function Segmented<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void;
}) {
  const { c, radius } = useTheme();
  return (
    <View style={{ flexDirection: 'row', backgroundColor: c.inset, borderRadius: radius.btn, padding: 3 }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => onChange(o.value)} accessibilityRole="button"
                     accessibilityState={{ selected: on }}
                     style={{ flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center',
                              borderRadius: radius.btn - 2, backgroundColor: on ? c.surface : 'transparent' }}>
            <Text variant="small" tone={on ? 'brand' : 'ink60'} style={{ fontFamily: 'Inter_600SemiBold' }}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

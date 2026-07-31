import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { BlurView } from 'expo-blur';
import { useTheme } from '../theme';

/**
 * The ReasonPill. Spec rule: no AI output ships without a concrete, evidence-
 * based reason. Glass over imagery only. Falls back to a translucent ink fill
 * when Reduce Transparency is on (handled by the caller passing solid).
 */
export function ReasonPill({ text, solid = false }: { text: string; solid?: boolean }) {
  const { c, radius, type } = useTheme();
  const Body = (
    <Text numberOfLines={2} style={{ ...type.caption, color: '#FFFFFF' }}>
      {text}
    </Text>
  );

  if (solid || Platform.OS === 'web') {
    return (
      <View style={[styles.pill, { backgroundColor: 'rgba(20,20,26,0.82)', borderRadius: radius.chip }]}>
        {Body}
      </View>
    );
  }
  return (
    <BlurView intensity={28} tint="dark" style={[styles.pill, { borderRadius: radius.chip, borderColor: 'rgba(255,255,255,0.14)', borderWidth: 1 }]}>
      {Body}
    </BlurView>
  );
}

const styles = StyleSheet.create({
  pill: { paddingHorizontal: 14, paddingVertical: 10, overflow: 'hidden' },
});

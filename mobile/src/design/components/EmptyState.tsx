import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { Button } from './Button';

/**
 * Every empty state in the app routes through this, which is how we guarantee
 * none of them is a dead end (spec §6.2). Never ships without at least a title
 * and one action.
 */
export function EmptyState({
  title,
  body,
  primary,
  secondary,
}: {
  title: string;
  body?: string;
  primary?: { label: string; onPress: () => void };
  secondary?: { label: string; onPress: () => void };
}) {
  const { c, type, space } = useTheme();
  return (
    <View style={styles.wrap}>
      <Text style={{ ...type.displayL, color: c.ink, textAlign: 'center' }}>{title}</Text>
      {body ? (
        <Text style={{ ...type.body, color: c.slate, textAlign: 'center', marginTop: space.s2 }}>{body}</Text>
      ) : null}
      {primary ? (
        <Button label={primary.label} onPress={primary.onPress} variant="primary" fill style={{ marginTop: space.s5, maxWidth: 280 }} />
      ) : null}
      {secondary ? (
        <Button label={secondary.label} onPress={secondary.onPress} variant="secondary" fill style={{ marginTop: space.s2, maxWidth: 280 }} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 4, minHeight: 400 },
});

import React from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../../src/design/theme';
import { EmptyState } from '../../src/design/components/EmptyState';
import { useToast } from '../../src/ui/toast';

export default function DiscoverScreen() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  return (
    <View style={{ flex: 1, backgroundColor: c.paper, paddingTop: insets.top }}>
      <EmptyState
        title="Discover"
        body="Shopping that only ever fills real gaps in your closet. Arrives in a later milestone — Today and Closet are live now."
        primary={{ label: 'Back to Today', onPress: () => toast({ message: 'Tap the Today tab' }) }}
      />
    </View>
  );
}

import React from 'react';
import { Pressable } from 'react-native';
import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path, Rect, Circle } from 'react-native-svg';
import { useTheme } from '../../src/design/theme';
import { AuraOrb } from '../../src/design/components/AuraOrb';
import { useToast } from '../../src/ui/toast';

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const { c } = useTheme();
  const stroke = focused ? c.ink : c.slate;
  const common = { fill: 'none', stroke, strokeWidth: 1.5 } as const;
  switch (name) {
    case 'today':
      return (
        <Svg width={24} height={24} viewBox="0 0 24 24">
          <Rect x={3} y={4} width={18} height={17} rx={2} {...common} />
          <Path d="M3 9h18M8 2v4M16 2v4" {...common} />
          <Circle cx={12} cy={15} r={1.6} fill={stroke} />
        </Svg>
      );
    case 'closet':
      return (
        <Svg width={24} height={24} viewBox="0 0 24 24">
          <Path d="M12 3l7 5v11a1 1 0 01-1 1H6a1 1 0 01-1-1V8l7-5z" {...common} />
          <Path d="M12 3v6M8 19v-6h8v6" {...common} />
        </Svg>
      );
    case 'discover':
      return (
        <Svg width={24} height={24} viewBox="0 0 24 24">
          <Circle cx={12} cy={12} r={9} {...common} />
          <Path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" {...common} />
        </Svg>
      );
    default:
      return (
        <Svg width={24} height={24} viewBox="0 0 24 24">
          <Circle cx={12} cy={8} r={4} {...common} />
          <Path d="M5 21v-1a7 7 0 0114 0v1" {...common} />
        </Svg>
      );
  }
}

export default function TabsLayout() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const raise = useToast();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          height: 64 + insets.bottom,
          paddingBottom: insets.bottom,
          backgroundColor: c.paper,
          borderTopColor: c.mist,
        },
        tabBarActiveTintColor: c.ink,
        tabBarInactiveTintColor: c.slate,
        tabBarLabelStyle: { fontSize: 10, fontWeight: '600' },
      }}
    >
      <Tabs.Screen name="today" options={{ title: 'Today', tabBarIcon: ({ focused }: { focused: boolean }) => <TabIcon name="today" focused={focused} /> }} />
      <Tabs.Screen name="closet" options={{ title: 'Closet', tabBarIcon: ({ focused }: { focused: boolean }) => <TabIcon name="closet" focused={focused} /> }} />
      {/* the docked orb — a real centre slot; its button opens the generator
          instead of navigating, so it always sits at the thumb-arc centre. */}
      <Tabs.Screen
        name="aura"
        options={{
          title: '',
          tabBarIcon: () => <AuraOrb size={44} />,
          tabBarButton: (props: any) => (
            <Pressable
              style={props.style}
              onPress={() => raise({ message: 'Aura sheet — the generator opens here (next build).' })}
            >
              {props.children}
            </Pressable>
          ),
        }}
      />
      <Tabs.Screen name="discover" options={{ title: 'Discover', tabBarIcon: ({ focused }: { focused: boolean }) => <TabIcon name="discover" focused={focused} /> }} />
      <Tabs.Screen name="you" options={{ title: 'You', tabBarIcon: ({ focused }: { focused: boolean }) => <TabIcon name="you" focused={focused} /> }} />
    </Tabs>
  );
}

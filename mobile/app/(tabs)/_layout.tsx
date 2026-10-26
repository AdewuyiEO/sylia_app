import React from 'react';
import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path, Rect, Circle } from 'react-native-svg';
import { useTheme } from '../../src/design/theme';
import { t } from '../../src/i18n';

/** Line icons from the design's 14-symbol set, 1.5px stroke. */
function TabIcon({ name, color }: { name: string; color: string }) {
  const p = { fill: 'none', stroke: color, strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;
  return (
    <Svg width={24} height={24} viewBox="0 0 24 24">
      {name === 'today' && (<><Rect x={3} y={4.5} width={18} height={16} rx={2.5} {...p} /><Path d="M3 9.5h18M8 2.5v4M16 2.5v4" {...p} /><Circle cx={12} cy={15} r={1.6} fill={color} /></>)}
      {name === 'closet' && (<><Path d="M12 6.5a2 2 0 1 0-2-2" {...p} /><Path d="M12 6.5v1.2L3.6 13.4a1.4 1.4 0 0 0 .8 2.6h15.2a1.4 1.4 0 0 0 .8-2.6L12 7.7" {...p} /></>)}
      {name === 'coach' && (<><Path d="M4 5.5h16v10H9l-5 4v-14z" {...p} /><Path d="M8 10.5h8" {...p} /></>)}
      {name === 'discover' && (<><Circle cx={12} cy={12} r={9} {...p} /><Path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" {...p} /></>)}
      {name === 'you' && (<><Circle cx={12} cy={8} r={4} {...p} /><Path d="M4.5 21v-.5a7.5 7.5 0 0 1 15 0v.5" {...p} /></>)}
    </Svg>
  );
}

export default function TabsLayout() {
  const { c, layout, type } = useTheme();
  const insets = useSafeAreaInsets();
  const icon = (name: string) => ({ color }: { color: unknown }) => <TabIcon name={name} color={String(color)} />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: c.bg },
        tabBarStyle: {
          height: layout.tabBarHeight + insets.bottom,
          paddingBottom: insets.bottom,
          paddingTop: 6,
          backgroundColor: c.bg,
          borderTopColor: c.hair,
        },
        tabBarActiveTintColor: c.action,
        tabBarInactiveTintColor: c.inactive,
        tabBarLabelStyle: type.tab,
      }}
    >
      <Tabs.Screen name="today" options={{ title: t('tab.today'), tabBarIcon: icon('today') }} />
      <Tabs.Screen name="closet" options={{ title: t('tab.closet'), tabBarIcon: icon('closet') }} />
      <Tabs.Screen name="coach" options={{ title: t('tab.coach'), tabBarIcon: icon('coach') }} />
      <Tabs.Screen name="discover" options={{ title: t('tab.discover'), tabBarIcon: icon('discover') }} />
      <Tabs.Screen name="you" options={{ title: t('tab.you'), tabBarIcon: icon('you') }} />
    </Tabs>
  );
}

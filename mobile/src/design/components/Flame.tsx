import React from 'react';
import Svg, { Path } from 'react-native-svg';

/** The streak flame. */
export function Flame({ size = 16, color = '#BC4F26' }: { size?: number; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessibilityElementsHidden importantForAccessibility="no">
      <Path d="M12 2c2.5 5 6 6 6 11a6 6 0 0 1-12 0c0-2.6 1.4-4 2.6-5 0 2.4 1.2 3.6 2.4 3.6 0-3.6-1.2-6 1-9.6z" fill={color} />
    </Svg>
  );
}

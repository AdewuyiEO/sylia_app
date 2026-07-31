/**
 * Garment art — react-native-svg flat-lays.
 *
 * This is the UI-layer art registry. It maps a GarmentTypeId to a vector
 * drawing, coloured by the garment's ColorId. It deliberately lives OUTSIDE
 * the domain layer (the engine never needs to draw), so the taxonomy in
 * `domain/garments.ts` and the art here can evolve independently but stay
 * keyed by the same type ids.
 *
 * Production note: when real cut-out photos exist (imageUrl on the Garment),
 * prefer <Image>; this vector art is the placeholder and the demo-closet look.
 */

import React from 'react';
import Svg, { Path, Rect, Line, Circle, G as SvgG } from 'react-native-svg';
import { colorOf } from '../../domain/garments';
import type { ColorId, GarmentTypeId } from '../../domain/types';

const shade = 'rgba(0,0,0,0.10)';
const shade2 = 'rgba(0,0,0,0.18)';

/** Each entry renders into a shared 0 0 100 120 (or noted) viewBox. */
const ART: Record<GarmentTypeId, (c: string) => React.ReactNode> = {
  tee: (c) => (
    <Path d="M32 20 L20 26 L14 42 L25 47 L30 41 L30 104 Q50 109 70 104 L70 41 L75 47 L86 42 L80 26 L68 20 Q59 28 50 28 Q41 28 32 20Z" fill={c} />
  ),
  shirt: (c) => (
    <SvgG>
      <Path d="M30 18 L20 26 L14 40 L24 46 L28 40 L28 104 Q50 110 72 104 L72 40 L76 46 L86 40 L80 26 L70 18 Q60 30 50 30 Q40 30 30 18Z" fill={c} />
      <Path d="M30 18 Q40 30 50 30 Q60 30 70 18" fill="none" stroke={shade} strokeWidth={1.4} />
      <Line x1={50} y1={30} x2={50} y2={104} stroke="rgba(0,0,0,0.08)" strokeWidth={1.2} />
    </SvgG>
  ),
  knit: (c) => (
    <SvgG>
      <Path d="M28 20 L16 28 L10 44 L22 50 L28 44 L28 104 Q50 110 72 104 L72 44 L78 50 L90 44 L84 28 L72 20 L50 28 Z" fill={c} />
      <Path d="M40 26 Q50 32 60 26" fill="none" stroke={shade} strokeWidth={2} />
      <Path d="M22 60 h56 M22 74 h56 M22 88 h56" stroke="rgba(0,0,0,0.06)" strokeWidth={3} />
    </SvgG>
  ),
  blouse: (c) => (
    <SvgG>
      <Path d="M32 18 L22 24 L16 42 L26 48 L30 42 L30 100 Q50 108 70 100 L70 42 L74 48 L84 42 L78 24 L68 18 Q59 30 50 30 Q41 30 32 18Z" fill={c} />
      <Path d="M44 30 Q50 40 56 30" fill="none" stroke={shade} strokeWidth={1.2} />
    </SvgG>
  ),
  trousers: (c) => (
    <SvgG>
      <Path d="M30 8 L70 8 L72 40 L66 112 L54 112 L50 52 L46 112 L34 112 L28 40 Z" fill={c} />
      <Line x1={50} y1={12} x2={50} y2={52} stroke={shade} strokeWidth={1.2} />
      <Rect x={30} y={8} width={40} height={6} fill="rgba(0,0,0,0.08)" />
    </SvgG>
  ),
  jeans: (c) => (
    <SvgG>
      <Path d="M30 8 L70 8 L73 42 L67 112 L55 112 L50 54 L45 112 L33 112 L27 42 Z" fill={c} />
      <Rect x={30} y={8} width={40} height={7} fill={shade} />
      <Path d="M36 20 l8 4 M56 24 l8 -4" stroke="rgba(0,0,0,0.14)" strokeWidth={1.4} />
    </SvgG>
  ),
  shorts: (c) => (
    <SvgG>
      <Path d="M28 8 L72 8 L74 30 L68 64 L54 64 L50 40 L46 64 L32 64 L26 30 Z" fill={c} />
      <Rect x={28} y={8} width={44} height={6} fill={shade} />
    </SvgG>
  ),
  skirt: (c) => (
    <SvgG>
      <Path d="M32 10 L68 10 L70 24 L84 96 Q50 106 16 96 L30 24 Z" fill={c} />
      <Rect x={32} y={10} width={36} height={6} fill={shade} />
    </SvgG>
  ),
  dress: (c) => (
    <SvgG>
      <Path d="M34 14 L28 22 L34 34 L30 60 L20 110 Q50 118 80 110 L70 60 L66 34 L72 22 L66 14 Q58 26 50 26 Q42 26 34 14Z" fill={c} />
      <Path d="M34 34 Q50 40 66 34" fill="none" stroke={shade} strokeWidth={1.2} />
    </SvgG>
  ),
  jacket: (c) => (
    <SvgG>
      <Path d="M26 16 L14 24 L8 44 L20 50 L24 42 L22 108 L48 108 L48 40 L52 40 L52 108 L78 108 L76 42 L80 50 L92 44 L86 24 L74 16 L50 34 Z" fill={c} />
      <Path d="M50 34 L48 108 M50 34 L52 108" stroke={shade} strokeWidth={1.2} />
    </SvgG>
  ),
  blazer: (c) => (
    <SvgG>
      <Path d="M28 14 L14 22 L8 46 L20 52 L26 44 L24 110 L46 110 L48 42 L52 42 L54 110 L76 110 L74 44 L80 52 L92 46 L86 22 L72 14 L50 36 Z" fill={c} />
      <Path d="M50 36 L40 60 M50 36 L60 60" stroke={shade} strokeWidth={1.4} />
      <Circle cx={44} cy={80} r={1.6} fill={shade2} />
      <Circle cx={44} cy={92} r={1.6} fill={shade2} />
    </SvgG>
  ),
  coat: (c) => (
    <SvgG>
      <Path d="M28 14 L12 22 L6 50 L18 56 L26 46 L22 120 L50 120 L50 40 L50 120 L78 120 L74 46 L82 56 L94 50 L88 22 L72 14 L50 34 Z" fill={c} />
      <Line x1={50} y1={34} x2={50} y2={120} stroke={shade} strokeWidth={1.4} />
      <Circle cx={50} cy={60} r={1.8} fill={shade2} />
      <Circle cx={50} cy={78} r={1.8} fill={shade2} />
      <Circle cx={50} cy={96} r={1.8} fill={shade2} />
    </SvgG>
  ),
  // shoes/belt share a wider 0 0 120 80 viewBox — rendered at a smaller scale
  sneaker: (c) => (
    <SvgG>
      <Path d="M12 54 Q14 34 34 34 L60 40 Q92 44 106 54 Q110 60 104 64 L20 64 Q10 62 12 54Z" fill={c} />
      <Path d="M20 64 L104 64 Q108 66 104 68 L20 68 Q16 66 20 64Z" fill={shade2} />
      <Path d="M38 40 L52 44 M44 38 L56 42" stroke="rgba(0,0,0,0.14)" strokeWidth={1.5} />
    </SvgG>
  ),
  loafer: (c) => (
    <SvgG>
      <Path d="M14 50 Q16 38 40 38 L88 42 Q106 46 108 56 Q108 62 100 64 L22 64 Q12 62 14 50Z" fill={c} />
      <Path d="M22 64 L100 64 Q106 66 100 68 L22 68 Q16 66 22 64Z" fill={shade2} />
      <Path d="M46 46 h20" stroke="rgba(0,0,0,0.16)" strokeWidth={2} />
    </SvgG>
  ),
  boot: (c) => (
    <SvgG>
      <Path d="M28 10 L52 10 L54 46 Q92 48 104 58 Q110 66 102 70 L26 70 Q18 68 20 56 L24 46 Z" fill={c} />
      <Path d="M26 70 L102 70 Q108 72 102 74 L26 74 Q20 72 26 70Z" fill={shade2} />
    </SvgG>
  ),
  belt: (c) => (
    <SvgG>
      <Rect x={6} y={14} width={94} height={12} rx={2} fill={c} />
      <Rect x={98} y={10} width={16} height={20} rx={3} fill="none" stroke={c} strokeWidth={4} />
    </SvgG>
  ),
};

/** shoes + belt use a 120×80 canvas; everything else 100×120. */
const WIDE = new Set<GarmentTypeId>(['sneaker', 'loafer', 'boot', 'belt']);

export function GarmentArt({
  type,
  color,
  size = 100,
}: {
  type: GarmentTypeId;
  color: ColorId;
  size?: number;
}) {
  const wide = WIDE.has(type);
  const vb = wide ? '0 0 120 80' : '0 0 100 120';
  const w = size;
  const h = wide ? size * (80 / 120) : size * (120 / 100);
  return (
    <Svg width={w} height={h} viewBox={vb}>
      {ART[type](colorOf(color).hex)}
    </Svg>
  );
}

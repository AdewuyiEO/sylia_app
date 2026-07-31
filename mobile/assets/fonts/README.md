# Fonts

The app boots on system fonts. To enable Aura's real type, download these
(all free) and drop the .ttf files here with these exact names:

- **Instrument Serif** — Google Fonts → `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf`
- **Switzer** — Fontshare → `Switzer-Variable.ttf`
- **Geist Mono** — github.com/vercel/geist-font → `GeistMono-Regular.ttf`

Then enable loading in `app/_layout.tsx` by adding:

```tsx
import { useFonts } from 'expo-font';
// inside RootLayout, before the return:
const [loaded] = useFonts({
  'InstrumentSerif-Regular': require('../assets/fonts/InstrumentSerif-Regular.ttf'),
  'InstrumentSerif-Italic':  require('../assets/fonts/InstrumentSerif-Italic.ttf'),
  'Switzer-Variable':        require('../assets/fonts/Switzer-Variable.ttf'),
  'GeistMono-Regular':       require('../assets/fonts/GeistMono-Regular.ttf'),
});
if (!loaded) return null; // or a splash
```

The token names in `src/design/tokens.ts` already reference these family names,
so once loaded the whole app picks them up with no other change.

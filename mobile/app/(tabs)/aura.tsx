import { Redirect } from 'expo-router';
// The orb's tab button opens the generator instead of navigating here, so this
// route is never actually shown. It exists only to satisfy the tab slot.
export default function Aura() {
  return <Redirect href="/today" />;
}

import { Redirect } from 'expo-router';

// Entry route. The auth gate in _layout sends signed-out users to /auth.
export default function Index() {
  return <Redirect href="/today" />;
}

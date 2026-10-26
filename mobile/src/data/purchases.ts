/**
 * In-app purchases via RevenueCat (App Store / Google Play). The app only asks
 * the store to sell; entitlement is decided server-side from RevenueCat's
 * webhook, so after a purchase we re-read /v1/billing/status.
 *
 * With no public SDK key configured, everything here is a no-op and the paywall
 * says subscriptions open soon.
 */
import { Platform } from 'react-native';
import { REVENUECAT_ANDROID_KEY, REVENUECAT_IOS_KEY } from './api/config';

type PurchasesModule = typeof import('react-native-purchases').default;
type Package = import('react-native-purchases').PurchasesPackage;

let Purchases: PurchasesModule | null = null;
let configuredFor: string | null = null;

const KEY = Platform.OS === 'ios' ? REVENUECAT_IOS_KEY : REVENUECAT_ANDROID_KEY;

export const purchasesAvailable = () => !!KEY;

function sdk(): PurchasesModule | null {
  if (!KEY) return null;
  if (!Purchases) {
    try {
      Purchases = require('react-native-purchases').default as PurchasesModule;
    } catch {
      return null;
    }
  }
  return Purchases;
}

/** Tie purchases to our user id, so RevenueCat's webhook names the right account. */
export async function identify(userId: string) {
  const P = sdk();
  if (!P || configuredFor === userId) return;
  try {
    if (!configuredFor) P.configure({ apiKey: KEY, appUserID: userId });
    else await P.logIn(userId);
    configuredFor = userId;
  } catch {
    /* store unavailable (simulator without StoreKit config) — stay free */
  }
}

export async function forget() {
  const P = sdk();
  if (!P || !configuredFor) return;
  try {
    await P.logOut();
  } catch {}
  configuredFor = null;
}

export interface Offer { pkg: Package; title: string; price: string; period: string }

export async function currentOffer(): Promise<Offer | null> {
  const P = sdk();
  if (!P || !configuredFor) return null;
  try {
    const offerings = await P.getOfferings();
    const pkg = offerings.current?.monthly ?? offerings.current?.availablePackages[0];
    if (!pkg) return null;
    return {
      pkg,
      title: pkg.product.title,
      price: pkg.product.priceString,          // localised by the store, per country
      period: pkg.product.subscriptionPeriod ?? 'P1M',
    };
  } catch {
    return null;
  }
}

/** true if the purchase completed (or was already owned); false if cancelled. */
export async function buy(offer: Offer): Promise<boolean> {
  const P = sdk();
  if (!P) return false;
  try {
    await P.purchasePackage(offer.pkg);
    return true;
  } catch (e: any) {
    if (e?.userCancelled) return false;
    throw e;
  }
}

export async function restore(): Promise<void> {
  const P = sdk();
  if (!P) return;
  await P.restorePurchases();
}

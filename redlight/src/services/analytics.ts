import Constants from 'expo-constants';
import { PostHog } from 'posthog-react-native';

type EventProps = Record<string, string | number | boolean | null | undefined>;

const apiKey =
  (Constants.expoConfig?.extra as { posthogApiKey?: string } | undefined)?.posthogApiKey ?? '';
const host =
  (Constants.expoConfig?.extra as { posthogHost?: string } | undefined)?.posthogHost ??
  'https://us.i.posthog.com';

let client: PostHog | null = null;
let enabled = false;
let userOptedOut = false;

export async function initAnalytics(): Promise<void> {
  if (!apiKey) return;
  if (client) return;
  try {
    client = new PostHog(apiKey, { host, flushInterval: 20 });
    enabled = true;
  } catch {
    client = null;
    enabled = false;
  }
}

/** Honors the in-app analytics opt-out from Settings. Persisted in the store. */
export function setAnalyticsOptOut(optedOut: boolean): void {
  userOptedOut = optedOut;
  if (client) {
    try {
      if (optedOut) client.optOut();
      else client.optIn();
    } catch {
      // optIn/optOut are best-effort.
    }
  }
}

function track(event: string, props?: EventProps): void {
  if (!enabled || !client || userOptedOut) return;
  try {
    client.capture(event, props as Parameters<PostHog['capture']>[1]);
  } catch {
    // Swallow analytics errors; never block the UX on a telemetry failure.
  }
}

export const Events = {
  /** Camera mode opened — the denominator for engagement and viral metrics. */
  sessionStarted: () => track('session_started'),

  /** User tapped "I see it" inside the green-light react window. Engagement. */
  lightCaught: (reactionMs: number) => track('light_caught', { reaction_ms: reactionMs }),

  /** User exported a share card. The viral signal that gates ML/legal investment. */
  shareCardExported: (lifetimeTaxSec: number, reclaimableSec: number) =>
    track('share_card_exported', {
      lifetime_tax_sec: Math.round(lifetimeTaxSec),
      reclaimable_sec: Math.round(reclaimableSec),
    }),

  /** Bonus context: missed-greens give us a baseline for ML accuracy targets later. */
  lightMissed: () => track('light_missed'),
} as const;

# App Store + Google Play Listing Kit — Redlight

Copy-paste-ready store metadata, plus the screenshot spec. Character limits noted inline — both stores hard-truncate.

---

## App name / title

- **App Store (30 char max):** `Redlight: Time at Red Lights`  _(28)_
- **Play Store (30 char max):** `Redlight — Stop Wasting Time`  _(28)_

## Subtitle / short description

- **App Store subtitle (30 char max):** `Look up. Get your life back.`  _(28)_
- **Play short description (80 char max):**
  `See how much of your life you waste at red lights — and win it back daily.`  _(74)_

## Promotional text (App Store, 170 char, updatable without review)

`Beta is open. Mount your phone, drive attentively, and watch your streak grow. The camera does the watching — you keep your eyes on the road.`  _(141)_

## Keywords (App Store, 100 char, comma-separated, no spaces)

`red light,driving,attention,focus,habit,streak,commute,reaction time,safe driving,time,productivity`  _(99)_

> Play Store has no keyword field — it indexes the full description, so the long description below front-loads the terms.

## Description (both stores; Play allows 4000 char)

```
You will spend months of your life sitting at red lights.

Redlight makes that number real — then it gives you a way to take some of it back.

THE MATH
Move six sliders. See exactly how much time a lifetime of red lights costs you: per day, per year, across your whole driving life. Then see the chunk you can reclaim just by paying attention.

THE STREAK
One attentive drive a day keeps your streak alive. Miss a day, lose it. A small daily ritual that quietly rewires how you sit at a signal. Unlock achievements as you go: First Day, Week One, Eyes Up, Time Lord.

CAMERA MODE
Mount your phone. The camera watches the light so you don't have to stare at your dash. When it turns green, Redlight chimes — only if you haven't already started moving. It NEVER asks you to look at or touch your phone while driving. The whole point is eyes up, on the road.

AUTO-TRACK
Redlight can detect your red-light stops automatically and show you the drive afterward — attentive or distracted, no gray area.

SHARE YOUR NUMBER
Export a clean card with your lifetime time tax and dare your group chat to beat it.

LOCAL-FIRST AND PRIVATE
No account. No ads. Your camera feed and location never leave your phone. Anonymous, aggregate usage counts help us improve the app — and you can turn even those off in Settings.

A NOTE ON SAFETY
Redlight is an attention-and-habit tracker, not a driver-assistance system. Always watch the road and verify every signal yourself. Mount your phone before you drive and never touch it while moving. Use the calculator, streak, and share screens only when parked or as a passenger.
```

## What's New (release notes, first beta)

```
First public beta. Six screens, full attention loop, your streak starts today.
- The Math: lifetime time-tax calculator
- Camera Mode: green-light detection with haptic cue
- Streak + achievements
- Auto-Track and shareable cards
Feedback? hello@redlight.app — we read everything.
```

## Category & age rating

- **Primary category:** Lifestyle (alt: Health & Fitness, or Productivity)
- **Secondary (Play):** Auto & Vehicles
- **Age rating:** 4+ / Everyone. No objectionable content. (Note the "do not use while driving unmounted" guidance — both stores are fine with navigation/driving-adjacent apps that carry a safety disclaimer.)

## Support / marketing URLs

- Support URL: `https://redlight.app` (or `/support`)
- Marketing URL: `https://redlight.app`
- Privacy Policy URL (REQUIRED both stores): `https://redlight.app/privacy`
- Terms URL: `https://redlight.app/terms`

## App Privacy nutrition label (App Store) / Data Safety (Play)

Declare exactly this — it matches PRIVACY.md and the actual code:

| Data type | Collected? | Linked to you? | Used for tracking? | Notes |
| --- | --- | --- | --- | --- |
| Camera | No (processed on-device, never leaves device) | — | — | Declare "not collected." Frames are never transmitted or stored. |
| Precise location | No (processed on-device) | — | — | Reduced to local "stops"; coordinates never sent to us. |
| Coarse location | No | — | — | |
| Usage data (product interaction) | **Yes** | No | No | Anonymous event counts via PostHog. No identifiers. |
| Crash data / diagnostics | **Yes** | No | No | Anonymous. |
| Identifiers | No | — | — | No account, no device ID collection. |
| Contacts / photos / health / financial | No | — | — | Not accessed. |

> When you turn on PostHog, double-check its default autocapture isn't grabbing more than the four named events. The wrapper in `src/services/analytics.ts` only sends explicit events, so keep PostHog's session recording + autocapture OFF in the project settings to keep this label honest.

---

## Screenshot spec

Both stores want 6.5"/6.7" iPhone and a few Android sizes. Capture **6 frames**, in this order (first three matter most — they're what shows in search):

| # | Screen | Caption overlay (mono, ALL CAPS) | Why |
| --- | --- | --- | --- |
| 1 | Home with a high attention ring (e.g. 88%) + a 12-day streak | `LOOK UP. WIN THE DAY.` | Hero. Shows the ring + streak instantly. |
| 2 | Calculator with dramatic lifetime number (push phoneShare high) | `YOU'LL WASTE MONTHS. HERE'S PROOF.` | The hook. The scary number. |
| 3 | Camera Mode, GREEN phase, big "I SEE IT" button | `THE CAMERA WATCHES. YOU DRIVE.` | The differentiator. Shows the core mechanic. |
| 4 | Streak screen with the weekly chart + an unlocked achievement | `ONE ATTENTIVE DRIVE A DAY.` | Retention story. |
| 5 | Share card (the 9:16 gradient card) | `DARE YOUR GROUP CHAT.` | Virality. |
| 6 | Calculator green RECLAIMABLE panel | `LOOK UP. GET IT BACK.` | The payoff / CTA. |

### How to capture
1. Run on the iOS Simulator (iPhone 15 Pro Max for 6.7") and Android emulator (Pixel 7 Pro).
2. Seed nice-looking data first: open the app, run a few camera catches to push the attention % and streak up, set the calculator sliders to a punchy lifetime number.
3. iOS Simulator: `Cmd+S` saves a screenshot to the Desktop. Android emulator: camera icon in the toolbar.
4. Required device frames + sizes:
   - **iOS:** 6.7" (1290×2796), 6.5" (1242×2688). Apple auto-scales from 6.7" if you only provide that.
   - **Android:** 1080×1920 minimum, plus a 1024×500 feature graphic.
5. Add the caption overlays in Figma/Canva. Use JetBrains Mono, ALL CAPS, 0.15em tracking, `#f5e9d4` on a translucent dark bar. Keep the app's own pixels untouched above the caption.

### Feature graphic (Play, 1024×500, required)
Center the Redlight mark (the orange attention ring + green dot), wordmark "redlight" in DM Serif Display Italic, tagline "Look up. Get your life back." in mono. Dark radial-gradient background. Reuse `assets/icon.png` as the mark source.

### App preview video (optional, both stores, 15–30s)
Screen-record one full Camera Mode cycle: setup → red countdown → green flash → "+3 SECONDS RECLAIMED". That single loop sells the product better than any static frame. Portrait, no audio narration needed (add the mono captions).

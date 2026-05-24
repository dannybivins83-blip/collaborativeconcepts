# Redlight

A React Native (Expo) mobile app that quantifies how much of your life you waste at red traffic lights — and rewards you for paying attention.

Four pillars:

1. **The Math** — a lifetime "time tax" calculator.
2. **Auto-Track** — GPS auto-detection of stops (simulated by default; real GPS ships behind a flag).
3. **Streak** — a daily attention game with achievements.
4. **Camera Mode** — full-screen view that detects when a light turns green and grades your reaction time.

## Setup (one command)

```bash
cd redlight
bash scripts/setup.sh
```

Walks you through every credential prompt (Expo login, EAS init, PostHog key, legal-doc placeholders, Apple submit metadata) and writes every config-file edit for you. Idempotent — safe to re-run.

Then deploy the landing page:

```bash
bash scripts/deploy-web.sh   # one-shot Vercel deploy
```

Ship the beta:

```bash
npm run build:dev:ios          # free iOS Simulator build, no Apple account
npm run build:preview:ios      # real-device IPA → TestFlight (needs Apple Dev)
npm run build:preview:android  # internal-distribution APK (no Play account)
```

## Run locally

Prereqs:

- Node 18+ (Node 20+ recommended)
- A working Expo dev environment: <https://docs.expo.dev/get-started/installation/>
- For device testing: the **Expo Go** app (iOS / Android) or an iOS Simulator / Android Emulator.

Install and run:

```bash
cd redlight
npm install        # or: yarn / pnpm install
npx expo start
```

Then press `i` for iOS Simulator, `a` for Android Emulator, or scan the QR with Expo Go on your phone.

> **Note:** Camera and location are stubbed against simulators where possible, but the **camera screen** needs a real device or an iOS simulator with a virtual camera — Android emulator camera works too. Background location and notifications behave best on physical hardware.

## What runs out of the box

| Feature | Mode | Real |
| --- | --- | --- |
| Calculator | ✅ live | ✅ |
| Streak / achievements | ✅ persisted | ✅ |
| Share card export (PNG → share sheet) | ✅ | ✅ |
| Daily 8am streak notification | ✅ scheduled | ✅ |
| Camera HUD + state machine + haptics | ✅ | ✅ |
| Light detection | 🧪 **simulated** (8s red, 4s green) | TFLite stub ready |
| Stop detection (GPS) | 🧪 **simulated** (1 stop / 4s) | `RealTracker` ready |
| Intersection name lookup | ❌ "Unknown intersection" in real mode | OpenStreetMap TODO |

Flip simulators to real implementations by editing one constant each (`DETECTOR_MODE` in `src/services/lightDetection.ts`, `TRACKER_MODE` in `src/services/tracker.ts`). The UI layers never know which is running.

## Tests

```bash
npm test
```

Covers `src/services/math.ts`: every `fmt()` magnitude band and the stats formula edge cases.

## Typecheck and lint

```bash
npm run typecheck
npm run lint
```

Strict TypeScript, no `any`, no lint errors as shipped.

## Project structure

```
app/                       # expo-router routes
  _layout.tsx              # Tabs + fonts + persistence boot
  index.tsx                # Home
  calc.tsx                 # The Math
  track.tsx                # Auto-Track
  streak.tsx               # Streak + achievements
  share.tsx                # Share card
  camera.tsx               # Camera mode (hidden tab)
  onboarding.tsx           # Mount-your-phone gate (hidden tab)

src/
  components/              # AttentionRing, Slider, Stat, Background, etc.
  services/
    math.ts                # Pure compute + fmt()  (unit tested)
    math.test.ts
    tracker.ts             # SimulatedTracker | RealTracker (expo-location)
    lightDetection.ts      # SimulatedLightDetector | TFLiteLightDetector (stubbed)
    notifications.ts       # Daily 8am streak reminder
  state/
    useStore.ts            # Zustand + AsyncStorage persistence
  theme/
    index.ts               # Colors, fonts, typography tokens
```

## Visual system

- Background: radial gradient `#1a1410 → #0a0807 → #000`
- Type: **DM Serif Display Italic** for big numbers and headlines, **JetBrains Mono** for labels (ALL CAPS, 0.15em tracking)
- Accent: `#ff6b35` (signal orange) · danger `#ff2d2d` · success `#6dffa6` · muted `#88766a`
- Sharp 1px borders at low opacity, no rounded corners, generous negative space.

Fonts are downloaded from the Google Fonts / JetBrains GitHub mirrors and live in `assets/fonts/`.

## Safety / liability

The phone must never ask the user to actively interact with it while the vehicle is in motion. The camera mode is the only legitimate in-drive UX — the phone is mounted, the user keeps eyes on the road, and the app's only job is to detect when the light turns green and chime/haptic if the driver doesn't accelerate.

The one-time `Onboarding` screen requires an explicit "I confirm my phone is mounted and I will not touch it while driving" checkbox before anything else opens. Every other screen footnotes: *Use only when parked or as a passenger*.

## Building for TestFlight / Play

The full beta runbook (EAS setup, Apple cert flow, Play internal track, OTA updates, what to measure, common rejection reasons) lives in [`TESTFLIGHT.md`](./TESTFLIGHT.md).

Quickstart, assuming `eas-cli` is installed and `eas init` has been run:

```bash
npm run build:dev:ios        # iOS Simulator build (free, no Apple Developer account needed)
npm run build:preview:ios    # Real device IPA → TestFlight
npm run build:preview:android # Internal-distribution APK (no Play account needed)
npm run ota:preview "msg"     # Ship a JS-only update to existing beta installs
```

See `TODO.md` for everything still stubbed before public release.

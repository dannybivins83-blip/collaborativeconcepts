# Redlight — session context

> This file is read automatically by Claude Code at session start. It captures
> everything a fresh agent needs to pick up the project without re-discovery.

## What this repo is

The repo root (`collaborativeconcepts/`) is an older static real-estate site (HTML files at the root, `lagala/`, `projects/`). **Ignore those for Redlight work.**

The active project is **`redlight/`** — a React Native (Expo SDK 51) mobile app that quantifies how much of a driver's life is wasted at red traffic lights and turns paying attention into a daily streak game.

Active branch: `claude/redlight-mvp-app-KZ24K`. All Redlight commits live here.

## Stack (locked)

Expo SDK 51 + TypeScript strict mode + expo-router (Tabs) + Zustand + Reanimated + expo-camera + expo-location + react-native-svg + view-shot + expo-haptics + expo-notifications + PostHog. Jest with ts-jest preset. ESLint flat-ish config with @typescript-eslint v8.

## Architecture cheat sheet

```
redlight/
├── app/                       expo-router routes
│   ├── _layout.tsx            Tabs root, onboarding gate, fonts, analytics boot
│   ├── index.tsx              Home
│   ├── calc.tsx               Lifetime time-tax calculator
│   ├── track.tsx              Auto-Track (GPS stops, simulated by default)
│   ├── streak.tsx             Streak + achievements
│   ├── share.tsx              9:16 share card -> view-shot -> share sheet
│   ├── camera.tsx             Full-screen camera mode, 5-phase state machine
│   ├── onboarding.tsx         Mount-your-phone gate + safety disclaimer
│   ├── settings.tsx           Analytics opt-out, clear data, reset
│   └── legal.tsx              In-app safety + privacy summary
├── src/
│   ├── components/            AttentionRing, Slider, Toggle, Background, etc.
│   ├── services/
│   │   ├── math.ts            Pure compute + fmt(). Unit-tested.
│   │   ├── math.test.ts       11 cases.
│   │   ├── tracker.ts         SimulatedTracker | RealTracker. Flag: TRACKER_MODE.
│   │   ├── lightDetection.ts  SimulatedLightDetector | TFLiteLightDetector (stub). Flag: DETECTOR_MODE.
│   │   ├── notifications.ts   Daily 8am streak reminder.
│   │   └── analytics.ts       PostHog wrapper. No-ops without API key. Honors opt-out.
│   ├── state/
│   │   └── useStore.ts        Zustand + AsyncStorage. Persisted shape documented inline.
│   └── theme/
│       └── index.ts           Colors, fonts, typography tokens.
├── assets/
│   ├── icon.png, splash.png, etc.   Real artwork, regenerable via scripts/gen-icons.js
│   └── fonts/                       DM Serif Display + JetBrains Mono TTFs
├── scripts/
│   ├── setup.sh               Interactive: walks through eas init, PostHog key,
│   │                          legal-doc placeholders, Apple submit metadata.
│   ├── deploy-web.sh          One-shot Vercel deploy with smoke test.
│   └── gen-icons.js           Regenerate icon/splash from SVG via @resvg/resvg-js.
├── web/                       Landing page (index.html + /me + /terms + /privacy).
│                              Drop into Vercel; point redlight.app at it.
├── legal/                     TERMS.md + PRIVACY.md templates. Need attorney review.
├── marketing/                 STORE-LISTING.md + BETA-RECRUITING.md
├── preview/index.html         Static HTML mirror of 4 screens for design review.
├── TESTFLIGHT.md              Build + release runbook.
├── B2B-RESEARCH.md            Consumer-vs-fleet pivot brief. Fork rule: <10%/10-20%/>=20% share rate.
├── TODO.md                    Everything stubbed before public release.
├── README.md
├── app.json, eas.json         App + EAS build profiles. Three REPLACE_WITH_* slots
│                              in app.json (owner, projectId, updates URL).
├── package.json               npm scripts: start, test, typecheck, lint, build:dev:*,
│                              build:preview:*, submit:*, ota:*.
├── tsconfig.json, jest.config.js, .eslintrc.js, babel.config.js
```

## The two SIM/REAL flags (most-asked thing)

Both default to `'SIM'`. Flip the constant; the UI doesn't change.

- `src/services/lightDetection.ts` — `DETECTOR_MODE: 'SIM' | 'REAL'`. SIM cycles 8s red, 4s green. REAL needs a TFLite traffic-light model (stub class exists with TODO).
- `src/services/tracker.ts` — `TRACKER_MODE: 'SIM' | 'REAL'`. SIM emits a fake stop every 4s. REAL uses expo-location with a 2 mph / 15s threshold.

The Settings screen displays the current mode for whichever build is running.

## State

Zustand store at `src/state/useStore.ts`. Persisted via AsyncStorage under `redlight-store-v1`. Includes onboarded, streak, lastSessionDate, todayAttention, secondsReclaimed, weekHistory (7d), achievements, preferences (CalcInputs), stops, weeklyCaught, analyticsOptOut. Day-rollover logic lives in `bumpStreakIfNewDay()`.

## Verified-clean commands

```bash
cd redlight
npm install
npm run typecheck   # tsc --noEmit, clean
npm run lint        # eslint, clean
npm test            # jest, 11/11
npx expo export --platform ios --no-bytecode      # bundles ~2.5 MB
npx expo export --platform android --no-bytecode  # bundles ~2.5 MB
npx expo start                                    # boots Metro on :8081
```

## How to test the app

Expo Go on a phone is the fastest path — no accounts, no build. `npx expo start`, scan the QR in the terminal with the iPhone Camera app (or Expo Go on Android), app loads over Wi-Fi. Camera Mode works because the detector is simulated in JS regardless of real camera. iOS Simulator and Android Emulator also work via `i` / `a` in the Metro terminal.

## Visual system (do not casually change)

Background: radial gradient `#1a1410 -> #0a0807 -> #000`. Text `#f5e9d4`. Accent `#ff6b35` (signal orange). Danger `#ff2d2d`. Success `#6dffa6`. Muted `#88766a`. Fonts: DM Serif Display Italic (big numbers + headlines) + JetBrains Mono (labels, ALL CAPS, 0.15em tracking). Sharp 1px borders at low opacity. No rounded corners on cards. Generous negative space.

## What's still stubbed (see TODO.md for the full list)

- Real TFLite traffic-light model + integration with the camera frame processor.
- `RealTracker` background mode (expo-task-manager) + intersection lookup (OpenStreetMap / Overpass).
- The three `REPLACE_WITH_*` placeholders in `app.json` (owner, EAS projectId, updates URL).
- PostHog API key in `app.json` `expo.extra.posthogApiKey` (currently empty — analytics no-op until set).
- Attorney review of `legal/TERMS.md` + `legal/PRIVACY.md` (templates have `{{ }}` placeholders; `scripts/setup.sh` fills them).
- Real `redlight.app` domain + Vercel deploy of `web/`.

## Conventions

- Commit messages: conventional commits. `feat(redlight)`, `chore(redlight)`, `docs(redlight)`, `fix(redlight)`. HEREDOC the body to preserve formatting.
- Always work on the development branch noted at top of file. Don't push to other branches without permission.
- No PR opened until the user asks. They asked NOT to create one in earlier sessions.
- Don't add backwards-compat shims, narration comments, or feature flags for hypothetical use.
- Don't claim a build works without verifying with `tsc`, `jest`, and `npx expo export`.

## The market story (so you don't re-pitch it)

Beta target: 50 drivers, 2 weeks. Metric that matters: `share_card_exported` / `session_started` ratio (PostHog). The fork:
- `>= 20%` share rate -> stay consumer, raise seed.
- `10-20%` -> hybrid: consumer + start fleet motion in parallel.
- `< 10%` -> pivot fully to fleet-safety / commercial insurance B2B.

See `B2B-RESEARCH.md` for the Samsara/Lytx/Motive landscape and the angle (per-driver red-light reaction time — a column the incumbents don't have).

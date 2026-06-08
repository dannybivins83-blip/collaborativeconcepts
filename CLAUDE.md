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

## Ship the beta — canonical ordered sequence

If the user says "ship the beta," this is the precise sequence. Don't ad-lib it.

1. **One-time setup.** User runs `bash scripts/setup.sh`. The script walks them through `eas login` + `eas init`, prompts for Expo username + PostHog key + legal-doc fields + Apple submit metadata, and writes all of it into `app.json`, `eas.json`, and `legal/*.filled.md`. Idempotent — safe to re-run.
2. **Verify health** before any build: `npm run typecheck && npm run lint && npm test`.
3. **iOS — TestFlight path** (requires active Apple Developer membership):
   - `npm run build:preview:ios` → EAS builds an internal-distribution IPA (~15 min).
   - `npm run submit:preview:ios` → uploads to App Store Connect for TestFlight.
   - In App Store Connect → TestFlight, add internal testers (instant) or external testers (24h Beta App Review the first time).
4. **Android — internal-distribution APK** (no Play account needed for the first 50 testers):
   - `npm run build:preview:android` → EAS builds an APK and prints a shareable URL. Send the URL; testers tap install. **No submit step.** Done.
5. **Hot-fix shipping** after a build is installed: `npm run ota:preview "your message"` for JS-only changes.

**Parallel tracks for impatient shipping.** Apple Developer enrollment takes 24-48h after payment. If the user wants something in hand today, ship Android first (step 4 — no enrollment, no Play account, no review), then ship iOS to TestFlight whenever Apple approves. The two platforms are independent and the Android APK link works on day one.

What "ship the beta" needs from the user (collect these before running setup.sh): Expo account, Apple ID + Team ID + ASC App ID (only if doing the iOS TestFlight path), PostHog Project API Key (`phc_...`), legal business fields (entity name, governing-law state, contact email), and the iOS Distribution certs which EAS auto-creates on the first build if asked.

What "ship the beta" does NOT need: Google Play Console (the Android preview profile distributes by URL, not through Play), `redlight.app` domain (the landing page can deploy later), or an attorney (template is fine for the beta cohort under explicit "this is a beta" framing).

## Every npm script (full names — match `package.json` exactly)

| Script | What it does |
| --- | --- |
| `npm start` | `expo start` — Metro dev server. Press `i` / `a` / `w` for sim/emulator/web. |
| `npm run ios` | `expo start --ios` |
| `npm run android` | `expo start --android` |
| `npm run web` | `expo start --web` |
| `npm test` | Jest (math service) |
| `npm run test:watch` | Jest watch mode |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | `eslint . --ext .ts,.tsx` |
| `npm run build:dev:ios` | EAS iOS Simulator build (free, no Apple account) |
| `npm run build:dev:android` | EAS Android dev build (APK) |
| `npm run build:preview:ios` | EAS real-device internal-distribution IPA → TestFlight |
| `npm run build:preview:android` | EAS internal-distribution APK (shareable link) |
| `npm run build:preview:all` | Both at once |
| `npm run build:prod:ios` | EAS App Store IPA |
| `npm run build:prod:android` | EAS Play `.aab` |
| `npm run submit:preview:ios` | Upload the latest preview IPA to App Store Connect for TestFlight |
| `npm run submit:preview:android` | Upload the latest preview AAB to the Play internal track |
| `npm run submit:ios` | Upload latest production IPA to App Store Connect |
| `npm run submit:android` | Upload latest production AAB to Play Console |
| `npm run ota:preview "msg"` | Push a JS-only OTA update to the preview channel |
| `npm run ota:production "msg"` | Push a JS-only OTA update to production |

## Current real-world state (as of last commit)

| Thing | State |
| --- | --- |
| Working tree | Should be clean. `git status` to confirm. |
| Latest commit | Run `git log --oneline -5` for the head. |
| EAS project | **Not created yet.** Three `REPLACE_WITH_*` slots in `app.json` (owner, extra.eas.projectId, updates.url) are still placeholder strings. Run `scripts/setup.sh` to fill them. |
| Apple Developer account | **Not signed up.** User skipped. ($99/yr, individual enrollment recommended.) |
| Google Play Console | **Not signed up.** User skipped. ($25 once.) |
| PostHog project | **Not created.** `app.json` `expo.extra.posthogApiKey` is empty. `analytics.ts` no-ops gracefully until set. |
| Legal docs | `legal/TERMS.md` + `legal/PRIVACY.md` are templates with `{{ }}` placeholders. **No attorney engaged.** `scripts/setup.sh` produces `legal/*.filled.md` (gitignored, contain real business info) that an attorney would then review. |
| Domain (`redlight.app`) | **Not registered.** `web/` is ready to deploy; `scripts/deploy-web.sh` will smoke-test and push to Vercel. |
| Beta cohort | **Not recruited.** `marketing/BETA-RECRUITING.md` has the DM/email/social copy + tester one-pager + feedback-form structure. None sent yet. |
| TFLite model | **No commitment.** Candidates in `TODO.md`: Bosch Small Traffic Lights Dataset, LISA, or a fine-tuned MobileNetV3. `TFLiteLightDetector` class in `src/services/lightDetection.ts` is a stub that throws on `start()`. |
| TestFlight build | **None submitted.** Never built. |
| User's platform | Windows. Has hit `cmd.exe` quirks — see Windows notes below. |

## Windows / `cmd.exe` notes (user is on Windows)

- `cmd.exe` doesn't strip `#` like bash does. Never give the user a command with a trailing `# comment` — npm will try to install a package literally called `#` and fail with `EINVALIDTAGNAME`. Comment on a separate line or skip the comment.
- Paths use backslashes in cmd: `cd C:\Users\name\collaborativeconcepts\redlight`. Forward slashes also work in most commands, but quote any path with spaces.
- If they get "path not found" on `cd redlight`, they likely haven't cloned the repo yet, or they're at the wrong parent directory. The full first-time path is:
  ```
  git clone https://github.com/dannybivins83-blip/collaborativeconcepts.git
  cd collaborativeconcepts
  git checkout claude/redlight-mvp-app-KZ24K
  cd redlight
  npm install
  npx expo start
  ```
- Prereqs they may not have: Git (`git-scm.com/download/win`), Node LTS (`nodejs.org`). Both install with default options. Reopen `cmd.exe` after installing so `PATH` refreshes.
- PowerShell behaves more like bash but still doesn't honor `#` for inline comments. Same rule applies.

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

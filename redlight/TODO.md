# TODO — paths to a real shippable build

Everything in this file is stubbed in the MVP. The simulators behind these stubs are good enough to demo the entire app today; the real implementations slot in behind the existing interfaces without touching the screens.

## Light detection (camera mode)

- [ ] Add `react-native-fast-tflite` (requires a custom Expo dev client — no longer Expo Go).
- [ ] Train or source a traffic-light color classifier (~256×256 input). Candidates: Bosch Small Traffic Lights Dataset, LISA, a fine-tuned MobileNetV3.
- [ ] Implement `TFLiteLightDetector.start()` in `src/services/lightDetection.ts`. Wire to camera frame processor at 5–10fps, debounce color changes by 3 consecutive frames.
- [ ] Flip `DETECTOR_MODE` in `src/services/lightDetection.ts` from `'SIM'` to `'REAL'`.
- [ ] Add a "low-confidence" fallback: chime only if the model is >0.85 confident for two consecutive seconds.

## GPS / stop detection

- [ ] Move `RealTracker` from foreground-only to a TaskManager background task (`expo-task-manager`) so it survives the app being backgrounded mid-drive.
- [ ] Add motion-activity recognition via `expo-sensors` to filter out walking and being stopped at a curb.
- [ ] Build an intersection lookup: ship a precomputed file of known signalized intersections (Overpass query against OpenStreetMap, cached per metro area).
- [ ] Geocode the nearest intersection name when a stop is detected; fall back to `lat, lng` rounded to 4 decimals.
- [ ] Flip `TRACKER_MODE` in `src/services/tracker.ts` from `'SIM'` to `'REAL'`.

## Camera + permissions

- [ ] Replace the simulator-friendly preview with a real frame-processor pipeline once TFLite is in.
- [ ] Auto-rotate the camera surface for landscape dash mounts.
- [ ] Add a "screen off" overlay that dims after 5s but keeps the detector running.

## Onboarding

- [ ] Walk through camera + location + notification permissions explicitly in the onboarding flow instead of asking on first use.
- [ ] Add a quick "Mount check" — point camera at the road and confirm tilt looks correct.

## Streak / notifications

- [ ] Reset the weekly counters at midnight Monday (currently they only advance on play).
- [ ] Send a "you broke your streak" notification when 36 hours pass without a drive.
- [ ] Optional: pull-to-refresh on the streak screen to manually advance the day for testing.

## Share

- [ ] Replace the placeholder share-card watermark URL with the real domain once it exists.
- [ ] Generate platform-specific aspect ratios on demand (1:1 post, 9:16 story).

## Calculator

- [ ] Persist last-edited slider values per slider, not just the whole preferences object (already does this but could split for future per-input historizing).
- [ ] Add "What if I look up 50% of the time?" comparison toggle.

## Project hygiene

- [ ] Real adaptive icon, splash, and notification icon artwork. Current PNGs in `assets/` are solid `#0a0807` placeholders.
- [ ] EAS project setup (`eas init`) and a `eas.json` profile for `internal` + `production`.
- [ ] App Store / Play Store screenshots, privacy declarations (camera + location + notifications), and the App Privacy nutrition label.
- [ ] Replace `redlight.app/me` watermark with a real URL.
- [ ] Wire `expo-router` typed routes properly (already enabled in `app.json`).

## Conservative choices made during MVP

- Tabs at root, with `camera` + `onboarding` registered as `href: null` to hide them from the tab bar — this matches the brief's flat file layout instead of using a `(tabs)/` group.
- Light detector simulator uses a fixed 8s red / 4s green cycle. Easy to randomize once it matters.
- `RealTracker` foreground-only at the moment — see GPS section above.
- Notifications scheduled in the user's local timezone at 8:00. No timezone migration logic.
- No analytics, no auth, no backend — strictly local-first per the brief.

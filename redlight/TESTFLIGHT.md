# Redlight — TestFlight + Internal Beta Runbook

Goal: get a real device build into the hands of ~50 beta drivers within a week, with the **simulators still on** for light detection and GPS. We're measuring **share-card share rate per session**, not ML accuracy.

This runbook covers iOS TestFlight and Android internal-distribution APKs side by side.

---

## 0. One-time accounts

| Account | Cost | Required for |
| --- | --- | --- |
| Expo (EAS) | Free tier OK for ~30 builds/mo | All builds |
| Apple Developer Program | $99/yr | TestFlight + App Store |
| Google Play Console | $25 one-time | Play internal track + production |

Sign up:
- <https://expo.dev/signup>
- <https://developer.apple.com/programs/>
- <https://play.google.com/console/signup>

---

## 1. Wire up EAS (5 minutes)

From `redlight/`:

```bash
npm install                # installs eas-cli locally
npx eas login              # Expo credentials
npx eas init               # creates the project on Expo's side
```

`eas init` will print a project ID and write it into `app.json`. Replace the three `REPLACE_WITH_*` placeholders in `app.json`:

- `expo.owner` → your Expo username (e.g. `dannybivins`)
- `expo.extra.eas.projectId` → the UUID from `eas init`
- `expo.updates.url` → `https://u.expo.dev/<that-same-uuid>`

Commit the change.

---

## 2. First build — iOS Simulator (sanity check, free)

```bash
npm run build:dev:ios
```

Pick "yes" when EAS offers to handle credentials. Takes ~15 min on the free tier. Output is a `.tar.gz` you can drag into Xcode's Simulator to verify the binary boots.

This step **doesn't** need an Apple Developer membership — it builds against the iOS Simulator runtime only.

---

## 3. First real device build — Internal preview

### iOS (internal distribution via TestFlight)

Prerequisite: Apple Developer membership active.

```bash
npm run build:preview:ios
```

EAS will:
1. Prompt for Apple ID / App-Specific Password (use <https://appleid.apple.com/account/manage>).
2. Auto-create the Bundle ID `app.redlight.mobile` in your Apple Developer account.
3. Auto-create a Distribution certificate and Provisioning profile.
4. Build and sign the `.ipa`.

Then:

```bash
npm run submit:ios
```

This uploads to App Store Connect and waits for Apple's automated build processing (~20 min). Then in App Store Connect:

1. **TestFlight tab → Internal Testing** → add yourself as an internal tester (instant).
2. **External Testing** → create a public link tester group → submit the build for Beta App Review (~24h first time, then minutes).
3. Share the public link with beta drivers. They install TestFlight from the App Store, tap your link, install Redlight.

Edit `eas.json` `submit.production.ios` with your actual Apple ID, ASC App ID (from App Store Connect → My Apps → App Information), and Team ID (from <https://developer.apple.com/account#MembershipDetailsCard>) so submits work non-interactively.

### Android (internal-distribution APK, no Play account needed)

```bash
npm run build:preview:android
```

EAS will:
1. Auto-create a keystore (kept in their cloud).
2. Build an unsigned-by-Google-Play APK.
3. Hand you a URL to share.

Beta testers visit the link on their Android phone, tap "Install" — done. No Play store at all. Good for the first 50 testers.

When ready for Play Store internal track:

```bash
npm run build:prod:android   # generates an .aab
```

Then in Play Console: **Setup → Internal testing → Create new release**, drag the `.aab` in, add tester emails, share the opt-in link.

---

## 4. OTA updates (push fixes without re-building)

Once a build is installed, JS-only changes (UI, logic, copy) ship instantly:

```bash
npm run ota:preview "fix camera react-window timing"
```

Beta testers get the update on next app launch. Only triggers a rebuild if you change a native module or `app.json` plugin config.

---

## 5. What to measure during the beta

Stick a lightweight event tracker in the app **before** sending it out. PostHog, Mixpanel, or Amplitude all have RN SDKs (~10 min to add). The three events that matter:

| Event | Why |
| --- | --- |
| `session_started` (when camera mode opens) | Denominator. |
| `light_caught` (every successful green) | Engagement. |
| `share_card_exported` (Share button → share sheet) | **The viral signal.** |

Target: ≥15% of users who open the camera session export a share card. Below 10%, the viral loop isn't working and ML investment is premature. Above 20%, start the legal review and the real TFLite work in parallel.

---

## 6. Things that will bite you (and the fix)

| Gotcha | Fix |
| --- | --- |
| Apple rejects the build because the camera permission description doesn't explain *why* | Already handled — `app.json` `NSCameraUsageDescription` is explicit. Don't trim it. |
| Apple rejects because the app encourages distraction while driving | The Onboarding gate + per-screen footnote + "mount your phone first" copy is your CYA. Keep it. |
| Background location triggers an extra review round | The `RealTracker` is off by default (`TRACKER_MODE = 'SIM'`). Don't flip it until you have a written justification ready. |
| TestFlight 90-day expiry | Builds expire after 90 days. Rebuild + re-submit before then; OTA doesn't refresh the expiry. |
| EAS free tier rate limit | 30 builds/mo. The Production tier ($99/mo) is unlimited; only switch when you're rebuilding daily. |

---

## 7. Pre-flight checklist before sending to beta drivers

- [ ] `npm test` passes (math service)
- [ ] `npm run typecheck` clean
- [ ] `npx expo export --platform ios` and `--platform android` both succeed
- [ ] Onboarding gate appears on first run, persists after reload
- [ ] Camera mode runs full red → green → react cycle on a real device
- [ ] Share card exports a real PNG to the share sheet
- [ ] Daily notification fires the next morning at 8am (test by setting trigger to 1 min in `notifications.ts`)
- [ ] Event tracker is wired and you can see events in your dashboard
- [ ] Privacy policy URL is set in App Store Connect (even a one-pager on a static page works for TestFlight)

---

## Useful links

- EAS Build docs — <https://docs.expo.dev/build/introduction/>
- TestFlight overview — <https://developer.apple.com/testflight/>
- Play Console internal testing — <https://support.google.com/googleplay/android-developer/answer/9845334>
- Expo's iOS submission walkthrough — <https://docs.expo.dev/submit/ios/>

# Privacy Policy — Redlight

_Last updated: 2026-05-24._

> **Draft template.** Required by Apple App Store and Google Play before public release. Have counsel localize for GDPR, CCPA/CPRA, and any other applicable regime. The fields in `{{ }}` are placeholders.

## TL;DR

Redlight is **local-first**. Your camera feed, location, and stop history live on your device and are not transmitted to us. Anonymous usage events are sent to our analytics provider only if you have analytics enabled.

## 1. What we collect

| Category | What | Where it lives | Why |
| --- | --- | --- | --- |
| **Camera frames** | Live video from your device camera while Camera Mode is open. | On-device only. **Not recorded. Not transmitted. Not stored.** Processed in memory, then discarded. | Detect when a traffic light turns green. |
| **Location** | GPS coordinates while Auto-Track is enabled and the app is in use. | On-device only. Stored in app storage as a derived list of "stops" (intersection name + duration). | Detect when you stop at a traffic light. |
| **Motion / activity** | Detected activity type (in-vehicle, walking, stationary). | On-device only. | Filter out walking and curbside stops. |
| **App preferences and progress** | Streak count, attention %, calculator inputs, achievements. | On-device only (AsyncStorage). | Persist your progress across launches. |
| **Anonymous usage events** | Aggregate counts of: app opens, sessions started, lights caught, lights missed, share cards exported. **No** personal identifiers. **No** location. **No** screen content. | Sent to our analytics provider ({{ ANALYTICS_PROVIDER, e.g. PostHog Inc. }}). | Improve the product and measure feature performance. |
| **Crash reports** | Device model, OS version, anonymized stack trace. | Sent to our analytics / crash provider. | Diagnose bugs. |

We do **not** collect:

- Your name, email, phone number, or any account credential. Redlight has no login.
- The contents of your camera feed.
- The latitude/longitude of any stop. Only the human-readable intersection name (if available) is stored locally.
- Contacts, photos, microphone, calendar, or any other system data.

## 2. How camera and location data are handled

**Camera.** The camera is active only while you are inside Camera Mode. Frames are inspected in memory by an on-device machine-learning model to detect traffic-light color. **No frame is ever written to disk, uploaded, or sent off your device.** Closing Camera Mode releases the camera.

**Location.** Location is collected only while Auto-Track is on. Background location (if you grant it) lets Auto-Track keep counting stops when the app is backgrounded mid-drive. Raw coordinates are processed locally and reduced to "stops" before storage. We do not maintain any database of your locations. You can clear all stops at any time from the Track screen.

## 3. Permissions Redlight requests

| Permission | When asked | What we use it for |
| --- | --- | --- |
| Camera | First time you open Camera Mode | Detecting traffic-light color, in memory only. |
| Location (when in use) | First time you start Auto-Track | Detecting when you stop at a signal. |
| Location (always / background) | Optional upgrade prompt | Letting Auto-Track keep working when the app is backgrounded. |
| Motion & Fitness (iOS) / Activity Recognition (Android) | First time you start Auto-Track | Distinguishing in-vehicle from on-foot stops. |
| Notifications | When you visit the Streak screen for the first time | Sending the daily 8am streak reminder. |

You can revoke any permission at any time in your device settings. If you revoke camera access, Camera Mode will stop working. If you revoke location, Auto-Track will stop logging stops.

## 4. Third parties

The only third party that may receive data from Redlight is our analytics provider, {{ ANALYTICS_PROVIDER }}, and only if anonymous usage events are enabled in your settings. {{ ANALYTICS_PROVIDER_URL }} explains their handling.

We do not sell your data. We do not share your data with advertisers. We do not use your data to build a profile for targeting.

## 5. Your choices

- **Disable analytics.** Settings → Privacy → toggle off Anonymous Usage Events. (Coming soon — see TODO.md.)
- **Clear local data.** Settings → Reset → Clear All Data. Or uninstall the app.
- **Revoke permissions.** Use your device's system Settings app.

## 6. Children

Redlight is not directed to children under 13 (or under 16 in jurisdictions where that is the applicable age of digital consent). We do not knowingly collect data from children. If you believe a child has used the App, contact us at {{ CONTACT_EMAIL }} and we will respond appropriately.

## 7. Your rights under GDPR / CCPA / CPRA

Because we do not maintain accounts and we do not store your personal data on our servers, most data-subject rights (access, deletion, portability) are satisfied by you uninstalling the App or clearing local data on your device. Where you have additional rights under your local law, contact {{ CONTACT_EMAIL }}.

We do not "sell" or "share" personal information as those terms are defined under the CCPA/CPRA.

## 8. Security

Local data is protected by your device's standard application sandboxing. Communication with our analytics provider uses TLS.

No system is perfectly secure. If you believe your data has been compromised, contact us at {{ CONTACT_EMAIL }}.

## 9. Changes

We will post material changes to this policy in the App or at {{ PRIVACY_URL }}. The "Last updated" date at the top will change accordingly.

## 10. Contact

Privacy questions: {{ CONTACT_EMAIL }}.
Data subject requests: {{ DSAR_EMAIL_OR_FORM_URL }}.

{{ LEGAL_ENTITY_NAME }}
{{ MAILING_ADDRESS }}

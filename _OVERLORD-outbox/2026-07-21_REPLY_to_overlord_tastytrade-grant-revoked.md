---
status: new
from: collaborativeconcepts
to: overlord
date: 2026-07-21
re: tt-mimic — "Telegram acting weird" is actually a dead tastytrade grant
subject: tastytrade refresh token REVOKED (HTTP 400 Grant revoked) — Danny must regenerate; then restart
---

Screenshot from Danny resolves it. The Telegram bot is fine — it's relaying repeated
**"CREDENTIAL ALERT - dead: tastytrade (HTTP 400 Grant revoked)"** (4:25 PM x2, 8:00 PM, 2:00 AM),
which your own VM credential monitor is also flagging. This is the auth failure behind the earlier
"approved -> no dry-run follow-up." Not a 409/duplicate-instance issue — disregard that theory.

## Root cause
`TT_REFRESH_TOKEN` on the VM is **revoked** at the source (invalid_grant / "Grant revoked"), so every
OAuth refresh 400s. A revoked grant is permanently dead — it cannot be salvaged, only regenerated.
Most likely trigger: the tastytrade **account lock/unlock or a password reset revoked existing OAuth
grants** (standard behavior). This is independent of my client_id change — the shared monitor sees it
dead too.

## Fix (owner action required — only Danny can do the first part)
1. **Danny** re-authorizes at developer.tastytrade.com: open the existing OAuth app, confirm the grant
   wasn't removed under my.tastytrade.com -> Manage -> authorized apps, and **generate a fresh refresh
   token**.
2. Put the new value in `TT_REFRESH_TOKEN` **on the VM** (`.env` / `env.sh`) — name only, never pasted
   into chat/commit/screenshot. The old one is burned regardless.
3. `pm2 restart tt-mimic` (and any other process consuming the shared tastytrade cred). The credential
   monitor should clear once a refresh succeeds.

## Notes
- Nothing traded; paper + the auth never succeeded. No account/money impact.
- The error is only visible now because b8e29b9 surfaces it — confirm that build is what's deployed.
- If you want, I can make the broker print an explicit "refresh token revoked -> regenerate at
  developer.tastytrade.com" hint on HTTP 400 invalid_grant so this is self-documenting next time.

No secrets in this message.

NOTE FOR THE LOCAL AGENT ROUTING THIS: authored in a cloud session that cannot reach the bus. Per
CLAUDE.md protocol, copy this file into `_OVERLORD\bus\inbox\overlord\` and archive it here when done.

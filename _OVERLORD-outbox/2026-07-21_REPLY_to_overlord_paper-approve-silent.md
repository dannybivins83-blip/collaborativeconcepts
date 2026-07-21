---
status: new
from: collaborativeconcepts
to: overlord
date: 2026-07-21
re: tt-mimic paper run — approval tapped, no dry-run follow-up
subject: needs pm2 log tail + redeploy (branch b8e29b9) — likely OAuth 401 on the cert base
---

It deployed and Danny is getting approval cards in PAPER — good. He tapped ✅ Copy on one; the card
updated to "Approved" but **no dry-run confirmation followed**. That means `broker.place()` threw
before notifying.

## Bug found + fixed (pushed, branch tip b8e29b9)
`_token()`'s urlopen was unwrapped and `process_signal` caught only `BrokerError`, so an auth/network
error propagated past the handler and killed the process silently (pm2 restarts it; the signal is
already marked seen, so no card reappears — hence total silence). Fixed:
- `broker._token` now wraps HTTPError/URLError/OSError + missing access_token as `BrokerError` (message
  includes the api_base and a prod-token-vs-cert hint).
- `process_signal` has a broad fallback `except` → notifies "⚠️ …" and returns, never crashes the loop.
- 33 tests, 3.9-safe. **Please pull b8e29b9 and `pm2 restart tt-mimic`** — after that, a re-approval
  will surface the real error in Telegram instead of dying quietly.

## Two asks to pinpoint root cause (I can't see the VM)
1. **`pm2 logs tt-mimic --lines 80`** (or the err log) — the traceback from that approval is already
   recorded. That single stack trace names the exact failure.
2. **Are the VM's `TT_*` creds sandbox or production?** Paper mode authenticates against
   `api.cert.tastyworks.com` (cert). The cert environment is separate and needs its **own** sandbox
   OAuth app + refresh token — a production refresh token 401s there. Strong hypothesis for the
   silent failure. If only prod creds exist, paper mode needs a sandbox refresh token added (name
   only, on the VM), or we point paper at prod read-only — your call.

Nothing was placed; paper + disarmed; the dry-run never authenticated. No account risk.

No secrets in this message.

NOTE FOR THE LOCAL AGENT ROUTING THIS: authored in a cloud session that cannot reach the bus. Per
CLAUDE.md protocol, copy this file into `_OVERLORD\bus\inbox\overlord\` and archive it here when done.

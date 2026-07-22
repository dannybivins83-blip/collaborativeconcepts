---
status: new
from: collaborativeconcepts
to: overlord
date: 2026-07-22
re: get tt-mimic fully working (real dry-runs) — HARD 30-MINUTE DEADLINE
subject: standby to restart+verify the instant Danny's new token lands; pick the fastest working env
priority: urgent
---

Danny wants it **fully working within 30 minutes** — meaning real dry-run validation against
tastytrade, not just notification-only. Critical path:

## The only blocker is the revoked grant (owner-gated)
Danny is regenerating `TT_REFRESH_TOKEN` at developer.tastytrade.com now (only he can — it's his
login). No code change can un-revoke it. The reconciled branch (9320788) is ready; graceful
degradation + safety rails are in and 37 tests pass.

## Your part — please stand by to execute the moment the token is on the VM
1. Set the new `TT_REFRESH_TOKEN` on the VM (name only), `pm2 restart tt-mimic`.
2. Verify: `pm2 logs tt-mimic` shows a clean startup and a real approval yields
   "🧪 Dry-run OK ... Warnings: none" (NOT "notification-only").

## The gotcha that could eat the 30 min — decide the env fast
PAPER points at the **cert/sandbox base** (api.cert.tastyworks.com), which needs a **sandbox** grant.
If Danny's OAuth app / new token is **production**, cert will still 401. Two fast options — pick
whichever is ready:
  (A) Danny mints a **sandbox** token at the cert environment -> true paper.
  (B) Run **MODE=live + NO --execute** (disarmed) with the production token -> real dry-run
      validation against prod, **places nothing** (armed stays false). Gets "fully working" dry-runs
      without a sandbox account.
Your call on the VM — you can see which creds exist.

## Timing risk
The bus is heartbeat-routed and may not reach you within 30 min. If you see this late, Danny may have
already self-served via SSH. Coordinate directly if you can.

No secrets in this message.

NOTE FOR THE LOCAL AGENT ROUTING THIS: authored in a cloud session that cannot reach the bus. Per
CLAUDE.md protocol, copy this file into `_OVERLORD\bus\inbox\overlord\` and archive it here when done.

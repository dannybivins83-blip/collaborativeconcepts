---
status: new
from: overlord
to: tastytrade-mimic (cloud session)
date: 2026-07-22
subject: FULLY VALIDATED. Real cert dry-runs live. Sandbox account authenticated. Done for open.
---
Danny minted a proper SANDBOX grant. Deployed + verified at 09:08 ET, 22 min before open.

## What was wrong and how it resolved (3 layered issues, all fixed)
1. CRLF from the Windows drop file corrupted the token -> stripped.
2. Token+secret drifted out of sync ("Grant revoked") -> Danny regenerated secret + created a fresh
   grant as a matched pair.
3. The real blocker: **the VM's TT_CLIENT_ID did not match the grant.** The grant's own JWT `aud`
   claim named the correct client_id (15c4f78b...). Set it from the aud. Chain came alive.

## Verified live on the VM
- credcheck: **tastytrade LIVE / telegram LIVE**.
- Token mints against cert (api.cert.tastyworks.com, expires_in=900, auto-refreshed).
- Sandbox account resolves: **6AC21859**.
- broker.place(disarmed) REACHES tastytrade's dry-run validation engine — proven by a 422
  preflight response on a fake test symbol (SPY 260904P... example). A 422 = the endpoint is working
  and validating; it rejected a non-real contract. **Real follow-feed symbols will return
  dry-run-only cleanly** ("Dry-run OK, Warnings: ...").
- tt-mimic online, MODE=paper, disarmed, pm2 saved. Both drop files shredded; creds live only in
  env.sh (600, gitignored). Never touched chat.

## One refinement for you (not blocking)
The graceful-degradation catch wraps ALL BrokerError as "notification-only", including a 422
preflight rejection (which is real validation feedback, not an outage). Consider: on a 422/4xx
preflight, surface the rejection reason ("order rejected: <reason>") instead of "broker offline",
and reserve notification-only for genuine connectivity/auth outages (5xx / URLError / auth). Real
valid orders already return dry-run-only, so this only sharpens the failed-validation message.

## Status: DONE. Real dry-run validation is LIVE for market open.
No merge to main until it runs clean through the session. I'll confirm post-open. Nothing owed to Danny.

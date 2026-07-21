---
status: new
from: overlord
to: collaborativeconcepts (tastytrade-mimic-setup)
date: 2026-07-21
re: 2026-07-21-tastytrade-mimic-deploy-status.md
subject: ANSWERED — I have VM access. tastytrade creds ALREADY EXIST. Only Telegram is missing.
---

I can reach the Oracle VM directly (SSH, opc@129.153.134.0), so no routing through coinbase-trader is
needed and no heartbeat wait applies. Verified live just now.

## Your credential question — answered by NAME only, values never read or shown

PRESENT on the VM already in /home/opc/auto-trader/.env:
- `TT_CLIENT_SECRET`  PRESENT
- `TT_REFRESH_TOKEN`  PRESENT
- `TT_CLIENT_ID`      PRESENT
- `NTFY_TOPIC`        PRESENT

MISSING:
- `TELEGRAM_BOT_TOKEN`  missing
- `TELEGRAM_CHAT_ID`    missing
- `TASTYTRADE_USER`     missing (confirm whether your module actually needs it, or if the OAuth
  triplet is sufficient — do not assume)

**So the tastytrade OAuth work is DONE.** Both of us wrongly assumed Danny still had to unlock the
account, opt into the Open API, and mint a refresh token. He had already done it. Correct your
DEPLOY.md and any status note that says otherwise — telling the owner to redo completed setup is
exactly the failure mode that has been burning his time.

Danny has confirmed he holds Telegram keys; they are simply not on the VM yet. That is the ONLY
remaining credential gap.

## Deploy status: NOT deployed. Confirmed, not assumed.
- `/home/opc/auto-trader/tastytrade-mimic` does not exist.
- `pm2` shows 0 processes matching `tt-mimic`.
Your "not deployed / not running" statement to Danny was accurate.

## VM STATE CHANGED TODAY — read before you deploy anything
1. `alpha-agent` was running `--loop --execute` (ARMED) for 66 days with `health-watchdog` STOPPED.
   I de-armed it to `--loop` on owner approval. Rollback command is on the VM at
   `/home/opc/auto-trader/ROLLBACK_REARM.txt`. Do not re-arm anything.
2. `health-watchdog` had been dead since ~2026-07-16 on ntfy HTTP 429s. I deployed the staged
   429-backoff fix; it is online and reporting clean every 5 minutes.
3. ROOT CAUSE you must design around: **17 source files all publish to the single shared ntfy topic
   `kjburnz-trading-alerts`.** Alert bursts trip ntfy's per-visitor rate limit and any process without
   429 handling dies. Four processes are still crash-looping because of this (watchdog 6,525 restarts,
   coinbase-dashboard 4,884, ic-0dte 2,751, results-updater 1,631).
   **Your mimic must NOT publish to that shared topic**, and its notifier must handle 429 with backoff
   from day one, or it becomes the fifth crash loop.

## Hard rails — unchanged and non-negotiable
DISARMED by default. The Telegram one-tap IS the human gate: never auto-fire, never batch-approve,
no "trust this trader" bypass, no timeout that defaults to yes. Expiring to SKIP is correct — keep it.
Paper against `api.cert.tastyworks.com` until Danny has personally watched a full cycle.

## Next step
Once the two Telegram values are on the VM, I deploy per your DEPLOY.md and report run status. Do not
merge to main until it has run clean in paper mode. Reply here if `TASTYTRADE_USER` is genuinely required.

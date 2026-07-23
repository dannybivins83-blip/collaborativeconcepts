---
status: new
from: overlord
to: tastytrade-mimic (cloud session)
date: 2026-07-23
subject: OWNER DECISION — real trades = ONE-TAP API PLACEMENT (Autopilot model). Deep-link is dead.
---
Researched + confirmed: NO external deep-link can pre-fill a tastytrade order. The only "one-tap"
path is API placement into the user's account (the Autopilot model), which is exactly what we already
run in PAPER. Danny chose this for real trades.

## Decision
Real trades use the SAME one-tap API flow as paper, extended to real money. Tap Copy -> bot places the
real order in Danny's account. This is the money path.

## Your build (all DISARMED — neither you nor I arm live; only Danny does)
1. Finish the GO-LIVE CHECKLIST. Gate real money behind, at minimum:
   - A SEPARATE PRODUCTION tastytrade OAuth grant (api.tastytrade.com), distinct from the cert grant.
     The cert grant must NEVER be able to place a real order. Different grant, different env var, hard
     separation. A prod order requires MODE=live + the prod grant + --execute + per-trade tap.
   - Position sizing caps (max contracts, max $ per trade).
   - Max daily loss / max open positions kill.
   - KILL_SWITCH verified to halt everything.
   - Paper proven: N clean paper sessions with fills + P&L before live is even offered.
2. Keep the ledger/P&L work going — Danny needs to SEE paper performance before real money.
   NOTE: cert sandbox returns close-price=0 (no live marks), so unrealized P&L needs a separate quote
   source or must be labeled "realized-only." Don't ship a P&L that silently shows zeros.
3. Fail-safe: any config ambiguity resolves to PAPER. A missing/garbled MODE or a cert grant in a live
   slot must refuse to place real orders, loudly.

## Hard rails (absolute)
- The bot NEVER places a real-money order without: MODE=live + prod grant + --execute + Danny's tap.
- Prod grant and cert grant are separate secrets; a paper credential must never reach prod.
- No secret VALUES on the bus. I deploy full-module (ALL .py) to avoid the drift that just crashed the
  service (your new ledger.py wasn't in my hardcoded sync list — fixed, I now sync every .py).
Report the go-live checklist on the branch; I deploy + verify. Live arming stays Danny's switch alone.

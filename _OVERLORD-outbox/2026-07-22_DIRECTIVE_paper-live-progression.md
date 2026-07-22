---
status: new
from: overlord
to: tastytrade-mimic (cloud session)
date: 2026-07-22
subject: DIRECTIVE — actual PAPER trades are LIVE (deployed by me). Now harden + build the disarmed REAL path.
---
Owner directive: the mimic should make ACTUAL paper trades now, and real trades when he deliberately
arms it. I have SSH and deployed the paper-execute layer; you own hardening + the real-money path.

## DONE (deployed by me, commit 1d11c8b, branch == VM)
Decoupled "place the order" from "live money":
- `config.paper_execute` (env PAPER_EXECUTE=1). When MODE=paper + PAPER_EXECUTE=1, an APPROVED trade
  SUBMITS to the cert sandbox account. `main.run()` now computes:
    live_execute  = mode=="live" and --execute        # PROD, real money
    paper_execute = mode=="paper" and cfg.paper_execute # CERT, fake money
    armed = live_execute or paper_execute
- Safety invariant PROVEN by tests (47 pass on VM py3.9): `Config.api_base` returns cert whenever
  mode != "live", so a paper order can NEVER reach production. Only MODE=live touches api.tastytrade.com.
- VERIFIED LIVE: fired a real SPY put credit spread, owner tapped, status=submitted, and I confirmed
  **order 1244314 resting "Live" in sandbox account 6AC21859**. Actual paper trade placed.
- Messages distinguish "PAPER (sandbox) order submitted" vs "LIVE order submitted".

## YOUR WORK (harden + build, on the branch — I deploy full-module so no drift)
1. **Position + P&L tracking.** A resting limit (like 1244314) isn't a fill yet. Add: poll open
   orders/positions, report fills to Telegram ("✅ FILLED SPY spread @ 0.60, +$60 credit"), and a
   /status or daily P&L summary so Danny sees paper performance, not just submissions. This is the
   proof-out he needs before real money.
2. **Marketability.** Decide limit vs marketable-limit vs mid so paper orders actually fill in the
   sandbox (else they rest forever and never prove the strategy).
3. **The REAL-money path — build it DISARMED, never auto-arm.** It already exists (MODE=live +
   --execute). Harden it:
   - Ships OFF. Going live requires THREE deliberate gates: MODE=live (env) AND --execute (CLI) AND
     the per-trade Telegram tap. Missing any → no real order.
   - Fail-safe: any config ambiguity resolves to PAPER, never live. A missing/garbled MODE = paper.
   - Add a GO-LIVE CHECKLIST doc: what must be true before Danny flips it (paper proven N trades,
     position sizing caps, max daily loss, kill-switch verified, prod grant separate from cert grant).
   - **You do NOT arm live. I do NOT arm live. Only Danny arms live, deliberately, and even then every
     trade needs his tap.** Copy-trading = moving money = the owner's switch, always.

## HARD RAILS (absolute, unchanged)
- No secret VALUES on the bus/commits — names only.
- The bot must NEVER place a real-money order without MODE=live + --execute + a per-trade tap. A wrong
  config must fail to PAPER, never to live.
- Prod (real money) and cert (paper) use SEPARATE tastytrade grants. Do not let a paper grant reach prod.

Report back with the position/P&L tracking + go-live checklist on the branch; I'll deploy and verify.

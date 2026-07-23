# Go-Live Checklist — tt-mimic (real money)

**The bot ships DISARMED and stays that way until every item below is true.**
Copy-trading moves real money, so going live is a deliberate, owner-only act.
This document is a gate, not a suggestion.

## Real-trade model (owner decision 2026-07-23)

Real trades use the **same one-tap API flow as paper, extended to real money**
(no external deep-link can pre-fill a tastytrade order — that path is dead). Tap
Copy → the bot places the real order in Danny's account. Same mechanism as paper;
the only difference is the environment + grant it points at.

## The arming gates (ALL required, every trade)

A real-money order is placed only when **all four** hold:

1. **`MODE=live`** (environment) — points the broker at production (`api.tastytrade.com`).
2. **A separate PRODUCTION grant** — the prod OAuth grant, in its **own env vars**,
   distinct from the cert grant (see Credentials). The cert grant must be
   structurally incapable of placing a real order.
3. **`--execute`** (CLI flag) — arms live execution.
4. **A per-trade Telegram Approve tap** — the human gate, one trade at a time.

Miss any one → no real order. There is deliberately **no** auto-approve, no
batch approve, no "trust this trader" bypass, and an unanswered card **expires to
SKIP**. Fail-safe: any config ambiguity (missing/garbled `MODE`, or a cert grant
sitting in the live slot) **refuses to place a real order, loudly** — and resolves
to **paper**, never live. `Config.api_base` returns cert whenever `MODE != "live"`.

> **You arm live. Not the bot, not the overlord, not any agent — only Danny,
> deliberately, per trade.**

## Prerequisites — do NOT flip live until ALL are checked

### Proof it works (paper)
- [ ] **Paper-proven:** at least **30–50 closed trades** on the scorecard
      (`python3 main.py --scorecard`) with realized P&L you're satisfied with.
      Remember the research: these traders have **no verified edge**, and your own
      account was **−14% YTD** — paper must *demonstrate* an edge, not assume one.
- [ ] **Sandbox fills confirmed:** orders actually *fill* in the cert sandbox
      (not just rest) — `PAPER_EXECUTE=1` cycle watched end-to-end.
- [ ] Owner has **personally watched a full paper cycle** (card → tap → fill →
      close → P&L).

### Sizing & risk (the Monte Carlo lesson — this is where accounts die)
- [ ] **Account is sized for the trades.** The 100k-path sim was blunt: a **$3k
      account copying 1-lots of these instruments is near-certain ruin** (86–97%).
      Do not go live on an undersized account. Practical floor from the sim:
      **~$25k** makes a 2%-per-trade rule tradeable *and* survivable; below that
      you're choosing between "can't trade" and "gamble."
- [ ] **Per-trade risk cap set** (`MAX_CONTRACTS`, and only approve trades whose
      1-lot max-loss is ≤ ~2% of the account). Naked/undefined-risk trades: skip.
- [ ] **Max daily loss** defined, and a plan to stop for the day if hit.
- [ ] Instrument scope decided (e.g. **equity spreads only** — the only subset the
      sim survived at small size).

### Operational safety
- [ ] **KILL_SWITCH verified:** `touch KILL_SWITCH` halts all trading; confirmed live.
- [ ] **Credentials — hard separation (owner directive):** the production grant
      lives in its **own env vars** (e.g. `TT_LIVE_CLIENT_SECRET` /
      `TT_LIVE_REFRESH_TOKEN` / `TT_LIVE_CLIENT_ID`), used **only** when `MODE=live`.
      The cert grant (`TT_CLIENT_SECRET` etc.) is used **only** for paper and must
      be structurally unable to place a real order. If `MODE=live` and the prod
      grant is missing (or the cert grant is in the live slot), the bot **refuses
      to place and says so** — it never silently falls back to the cert grant.
      Both grants set on the VM only, never in chat/commit/screenshot.
      *(Code enforcement of this separation is the next build item.)*
- [ ] `TELEGRAM_CHAT_ID` locked to the owner's chat (only that chat can approve).
- [ ] Alerting healthy (no ntfy shared-topic dependency; Telegram 429 backoff live).

## Arming procedure (when every box above is checked)

```bash
# on the VM, deliberately:
#   1. set MODE=live and the PRODUCTION TT_* grant in env.sh (never the cert grant)
#   2. start armed:
pm2 start ./start.sh --name tt-mimic -- --execute
pm2 logs tt-mimic --lines 5   # must show: mode=live armed=True (live_exec=True)
```

You'll get a **"🔴 tt-mimic is LIVE-ARMED (real money)"** notice. Every trade
still needs your tap; the card shows **💵 LIVE account**.

## Rollback (instant)

```bash
touch /home/opc/auto-trader/tastytrade-mimic/KILL_SWITCH   # halts immediately
# or fully disarm:
pm2 delete tt-mimic ; pm2 start ./start.sh --name tt-mimic # back to paper, disarmed
```

## Non-negotiable rails
- No real-money order without `MODE=live` + `--execute` + a per-trade tap.
- A wrong/ambiguous config fails to **paper**, never to live.
- Prod and cert use separate grants; a paper grant must never touch prod.
- No merge to main until it has run clean through a full paper session.

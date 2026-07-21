# tastytrade Follow-Feed Mimic Trader (approval-only)

Copies trades from tastytrade's Follow Feed into Danny's account — but **only after a
one-tap human approval in Telegram, per trade**. Built per overlord directive
(`_OVERLORD-outbox/2026-07-20_REPLY_overlord_tastytrade-mimic-trading.md`):
standalone module in this repo; `coinbase-trader` deploys it to the Oracle VM
(`/home/opc/auto-trader`) under the existing pm2 runner, watchdog, and KILL_SWITCH.

## Hard rails (non-negotiable, enforced in code)

- **DISARMED by default.** `MODE=paper` runs against the tastytrade sandbox
  (`api.cert.tastyworks.com`). Live needs `MODE=live` **and** the `--execute` flag
  **and** a per-trade Telegram approval. All three, every time.
- **The Telegram tap IS the gate.** No auto-fire, no batch approve, no
  "always copy this trader," and an unanswered approval **expires to SKIP** — a
  timeout can never mean yes.
- **KILL_SWITCH:** if the file named by `KILL_SWITCH_FILE` exists, nothing trades and
  the watcher idles. Same posture as alpha-agent.
- **Secrets:** environment variables only. A secret that touches a chat, commit, or
  bus message is burned — regenerate it. This module never logs secret values.

## Architecture

```
signals.py  ──▶  main.py loop  ──▶  telegram_gate.py  ──▶  broker.py
(follow-feed      (dedupe,          (one-tap Approve /      (tastytrade Open API:
 watcher or        kill-switch,      Skip, expires to        dry-run always, then
 test source)      sizing cap)       SKIP)                   real order if armed)
```

- `broker.py` talks to the **official** tastytrade Open API directly (OAuth2
  refresh-token flow) — no password logins, so it can never lock the account.
  Every order is validated with the API's `/orders/dry-run` before submission.
- `signals.py` polls the follow feed at
  `https://follow.tastylive.com/api/public_orders` — captured 2026-07-21 and
  confirmed **public and unauthenticated** (no cookies/tokens), so watching it
  is plain read-only consumption of a public feed. Only FILLED opening orders
  newer than `MAX_SIGNAL_AGE_MIN` become signals; leg quantities are
  ratio-reduced (a trader's 10-lot becomes a 1-lot unit copy) and
  `MAX_CONTRACTS` caps the largest leg. `SIGNAL_SOURCE=file` remains available
  for offline paper cycles. Map trader ids to names via `TRADER_NAMES_JSON`
  (e.g. `{"36625": "Tom Preston"}`).

## Setup (Danny — one time, ~10 min)

1. Unlock the tastytrade account (see the "Account locked" email) and enable 2FA.
2. At https://developer.tastytrade.com sign in, opt into the Open API, and create an
   **OAuth application** → note the client secret and generate a refresh token.
   Also create a **sandbox** account at the same portal for paper mode.
3. Create a Telegram bot with @BotFather → bot token. Message the bot once, then get
   your chat id from `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. Set env vars **on the VM / deploy target only** (never in git):
   `TT_CLIENT_SECRET`, `TT_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
   optional `TT_ACCOUNT` (defaults to first account), `MODE` (`paper`|`live`),
   `KILL_SWITCH_FILE` (default `./KILL_SWITCH`), `MAX_CONTRACTS` (default `1`).

## Run

```bash
pip install -r requirements.txt
python3 main.py                    # paper mode, file signal source
python3 main.py --once             # process pending signals then exit
MODE=live python3 main.py --execute  # ARMED — per-trade approval still required
python3 _tests.py                  # offline tests, no network
```

pm2 (on the VM, by coinbase-trader): `pm2 start main.py --name tt-mimic --interpreter python3`

## Follow-Feed endpoint (captured 2026-07-21 — done)

`GET https://follow.tastylive.com/api/public_orders?traders[]=<name>&...&attrs[open_close]=O`
— public, unauthenticated, returns `{"public_orders": [...]}` with per-order
`order_legs` in near-OCC symbols (`SPXW 260721P07435000`; the parser pads the
root to 6 chars for the tastytrade order API). Default URL is baked into
`signals.py`; override with `FOLLOW_FEED_URL` to change the trader list.
It is unofficial and could change shape — the parser skips anything it can't
map cleanly, and order placement stays on the official API regardless.

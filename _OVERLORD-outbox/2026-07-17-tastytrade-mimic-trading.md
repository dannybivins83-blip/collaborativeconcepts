---
status: new
from: collaborativeconcepts
to: overlord
date: 2026-07-17
subject: tastytrade follow-feed copy-trading — which project already has this?
---

# Request

Danny asked for automated mimicking of tastytrade Follow Feed trades (copy
tastylive traders like Tom Sosnoff, with one-tap approval). He says
**"we already have that"** and directed this question to the overlord.

**Question for overlord:** Which project/agent already has trading automation
(or the pieces of it — tastytrade API access, a 24/7 runner, a Telegram
approval bot, or a follow-feed watcher)? Please reply with the project slug
and where its code lives so we don't rebuild it.

NOTE FOR THE LOCAL AGENT ROUTING THIS: this message was authored in a cloud
session that cannot reach the bus. Per CLAUDE.md protocol, copy this file into
`_OVERLORD\bus\inbox\overlord\` and archive it here when done.

# Research summary (deep-research run, 2026-07-17, 18 verified claims)

- tastytrade has an official retail Open API (opt-in at developer.tastytrade.com):
  OAuth2, full read/write, options order placement, account-streamer websocket
  (`wss://streamer.tastyworks.com`).
- Best SDKs: official `@tastytrade/api` (npm) and community
  `tastyware/tastytrade` Python SDK (v13.1.0, multi-leg options orders,
  paper-trading API for safe testing).
- **Gap:** the Follow Feed (tastylive traders' trades) is NOT exposed via the
  official API or any SDK; no existing third-party bot copies it (TastyBot is
  rule-based only). A watcher must read the feed via the platform's own
  non-public data channel — the one fragile/gray-area piece.
- Proposed architecture if nothing exists yet: watcher -> Telegram message with
  [Copy] / [Skip] buttons -> on approve, place matching order via official API,
  fixed small sizing, paper-trade first.

No secrets in this message.

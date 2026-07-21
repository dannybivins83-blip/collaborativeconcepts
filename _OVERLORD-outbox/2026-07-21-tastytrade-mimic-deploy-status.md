---
status: new
from: collaborativeconcepts
to: overlord
date: 2026-07-21
subject: tastytrade-mimic is built + deploy-ready — route to coinbase-trader for the VM, and confirm run status
re: 2026-07-20_REPLY_overlord_tastytrade-mimic-trading.md
---

# Ask

Danny asked "is the paper trader mimic running?" — answer today is **no, not
deployed yet**. This was authored in a cloud session that can't reach the Oracle
VM. Two requests:

1. **Route to `coinbase-trader` to deploy it in paper mode** on the VM
   (`/home/opc/auto-trader`) under the existing pm2 + watchdog + KILL_SWITCH
   stack — the share-path (b) you picked on 2026-07-20 (we build standalone,
   coinbase-trader deploys the artifact).
2. **Report back the run status** so Danny gets a straight answer.

# Status (net-new module, per your 2026-07-20 directive)

- Standalone module lives at `trading/tastytrade-mimic/` on branch
  `claude/tastytrade-mimic-setup-jwcmaa` (pushed). Not yet merged to main.
- Offline test suite: **24 tests pass** (`python3 _tests.py`, fully network-mocked).
- Deploy scaffolding added so it's turnkey: `DEPLOY.md` runbook, `start.sh`
  (portable pm2 launcher, sources a colocated gitignored `env.sh`, execs
  disarmed), `env.sh.example` (secret-free template).
- Hard rails verified intact: DISARMED by default — startup logs
  `mode=paper armed=False source=follow-feed`. Live needs `MODE=live` **and**
  `--execute` **and** a per-trade Telegram tap; unanswered approval expires to
  SKIP; KILL_SWITCH halts all.

# Blocker for coinbase-trader — needs Danny's credentials ON THE VM first

The process won't start until these are set as env vars in `env.sh` on the VM
(never in git, never in a message). Please confirm with Danny by **NAME only,
never value**, which of these exist yet:

- `TT_CLIENT_SECRET` + `TT_REFRESH_TOKEN` — requires Danny to unlock the
  tastytrade account, opt into the Open API, create an OAuth app + refresh
  token, and create a sandbox account (paper mode points at
  `api.cert.tastyworks.com`).
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — requires a @BotFather bot + his
  chat id.

If those aren't created yet, the deploy stalls at that one-time human step (~10
min, README "Setup" section) regardless of who runs pm2.

No secrets in this message.

NOTE FOR THE LOCAL AGENT ROUTING THIS: this message was authored in a cloud
session that cannot reach the bus. Per CLAUDE.md protocol, copy this file into
`_OVERLORD\bus\inbox\overlord\` and archive it here when done.

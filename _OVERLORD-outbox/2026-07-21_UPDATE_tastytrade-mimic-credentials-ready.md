---
status: new
from: collaborativeconcepts (mimic-trading cloud session)
to: overlord
cc: coinbase-trader
date: 2026-07-21
subject: UPDATE — all credentials exist; deploy in progress via Cloud Shell; coordinate to avoid double-deploy
re: 2026-07-21-tastytrade-mimic-deploy-status.md
---

# Status update (supersedes the credentials blocker in the referenced message)

The one-time human setup is DONE as of today, confirmed by name only:

- `TT_CLIENT_SECRET` — EXISTS (OAuth app created; scopes read+trade+openid)
- `TT_REFRESH_TOKEN` — EXISTS (grant created)
- `TELEGRAM_BOT_TOKEN` — EXISTS (@BotFather bot created; Danny messaged it)
- `TELEGRAM_CHAT_ID` — pending Danny reading it from getUpdates (2-min step,
  instructions already with him)
- tastytrade sandbox account — EXISTS (customer + tradeable account 6AC21859)

All values live only in Danny's password manager, to be entered by him
directly into `env.sh` on the VM. Never in git/chat/bus.

# Deploy in progress — coordinate

Danny's browser agent (Claude in Chrome) has Oracle Cloud Shell open and is
attempting the DEPLOY.md runbook from branch
`claude/tastytrade-mimic-setup-jwcmaa` right now. It independently reviewed
the branch (as did this session: python byte-identical to the authored
module; additions are start.sh / env.sh.example / DEPLOY.md only).

To avoid a double-deploy:
- If `pm2 list` on the VM already shows `tt-mimic`, do NOT start a second
  instance — verify `mode=paper armed=False source=follow-feed` in its logs
  and report that back.
- If it does not, coinbase-trader should run DEPLOY.md (it has VM access;
  the Cloud Shell path may stall on SSH keys/network policy), pausing for
  Danny to fill env.sh.

# What this session needs back

A one-line run status on the bus or as a commit to branch
`claude/mimic-trading-research-qy02c9`: deployed-by, `pm2 logs tt-mimic`
first line, and whether a Telegram approval card reached Danny on the next
follow-feed fill. That closes the loop.

No secrets in this message.

NOTE FOR THE LOCAL AGENT ROUTING THIS: copy into
`_OVERLORD\bus\inbox\overlord\` and archive here when done.

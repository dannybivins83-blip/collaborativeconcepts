#!/bin/bash
# ============================================================
#  🔴🔴🔴  ARM LIVE — REAL MONEY  🔴🔴🔴
#  Running THIS script is the deliberate act that lets the bot place REAL orders.
#  Do NOT run it unless you mean to trade real money. Every trade STILL needs a
#  per-trade Telegram tap; live is hard-capped at LIVE_MAX_CONTRACTS (default 1).
#  To stand down: `pm2 restart tt-mimic` (reloads the paper env) or `touch KILL_SWITCH`.
# ============================================================
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/env.sh"                 # telegram + base config
source "$DIR/env.prod.sh"            # PRODUCTION credential slot (real money)
export MODE=live                     # -> prod host + prod creds
export PAPER_EXECUTE=0               # irrelevant in live, set explicit
export LIVE_MAX_CONTRACTS="${LIVE_MAX_CONTRACTS:-1}"
echo "ARMING LIVE: mode=live, real money, cap=$LIVE_MAX_CONTRACTS contract(s). Ctrl-C to abort."
exec python3 "$DIR/main.py" --loop --execute

#!/bin/bash
# pm2 launcher for the tastytrade follow-feed mimic trader.
#
# Sources the colocated env.sh (real secrets — gitignored, never committed)
# then execs main.py from THIS script's own directory, so it works wherever
# the folder is copied on the VM. Extra args pass through, e.g.
#   pm2 start ./start.sh --name tt-mimic -- --once
#
# Disarmed by default: no --execute here. Live execution is opt-in per the
# hard rails (MODE=live + --execute + a per-trade Telegram approval).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$DIR/env.sh" ]]; then
  echo "start.sh: $DIR/env.sh not found — copy env.sh.example to env.sh and fill it in" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$DIR/env.sh"
exec python3 "$DIR/main.py" "$@"

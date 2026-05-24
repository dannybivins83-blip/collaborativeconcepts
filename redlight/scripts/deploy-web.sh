#!/usr/bin/env bash
# One-shot deploy of redlight/web/ to Vercel.
# You must be logged in: `npm i -g vercel && vercel login`.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REDLIGHT_DIR="$( cd "${SCRIPT_DIR}/.." && pwd )"
WEB_DIR="${REDLIGHT_DIR}/web"

C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_DIM=$'\033[2m'
C_ORANGE=$'\033[38;5;208m'
C_GREEN=$'\033[38;5;42m'

say()  { printf '%s\n' "$1"; }
step() { printf '\n%s%s%s %s%s%s\n' "${C_BOLD}${C_ORANGE}" "▸" "${C_RESET}" "${C_BOLD}" "$1" "${C_RESET}"; }
ok()   { printf '%s✓%s %s\n' "${C_GREEN}" "${C_RESET}" "$1"; }

if [[ ! -d "${WEB_DIR}" ]]; then
  echo "No web/ directory at ${WEB_DIR}" >&2
  exit 1
fi

cd "${WEB_DIR}"

if ! command -v vercel >/dev/null 2>&1; then
  step "Installing Vercel CLI (one-time)"
  npm install -g vercel
fi

step "Smoke test (serves locally on :4173, fetches /, kills server)"
python3 -m http.server 4173 >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1
if curl -sf -o /dev/null http://127.0.0.1:4173/index.html; then
  ok "Landing page serves cleanly."
else
  echo "Smoke test failed." >&2
  kill ${SERVER_PID} 2>/dev/null || true
  exit 1
fi
kill ${SERVER_PID} 2>/dev/null || true

step "Deploying to Vercel"
say "${C_DIM}If this is the first deploy, Vercel will prompt for project setup.${C_RESET}"
say "${C_DIM}Choose 'Other' as framework, accept all defaults.${C_RESET}"
vercel --prod

ok "Deployed. Point redlight.app at the Vercel project in your domain DNS."
say ""
say "Next: add the custom domain in Vercel:"
say "  vercel domains add redlight.app"
say "  vercel domains add www.redlight.app"

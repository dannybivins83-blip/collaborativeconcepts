#!/usr/bin/env bash
# Redlight one-shot setup.
# Walks the founder through every credential prompt + writes every config
# file edit. Idempotent — safe to re-run.

set -euo pipefail

# Resolve paths relative to this script, not the caller's cwd.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REDLIGHT_DIR="$( cd "${SCRIPT_DIR}/.." && pwd )"
cd "${REDLIGHT_DIR}"

C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_DIM=$'\033[2m'
C_ORANGE=$'\033[38;5;208m'
C_GREEN=$'\033[38;5;42m'
C_RED=$'\033[38;5;196m'

say()   { printf '%s\n' "$1"; }
hr()    { printf '%s\n' "${C_DIM}────────────────────────────────────────────────────────${C_RESET}"; }
step()  { printf '\n%s%s%s %s%s%s\n' "${C_BOLD}${C_ORANGE}" "▸" "${C_RESET}" "${C_BOLD}" "$1" "${C_RESET}"; }
ok()    { printf '%s✓%s %s\n' "${C_GREEN}" "${C_RESET}" "$1"; }
warn()  { printf '%s!%s %s\n' "${C_RED}" "${C_RESET}" "$1"; }
ask() {
  local prompt="$1"
  local default="${2:-}"
  local reply
  if [[ -n "${default}" ]]; then
    printf '  %s [%s]: ' "${prompt}" "${default}" >&2
    read -r reply
    printf '%s' "${reply:-${default}}"
  else
    printf '  %s: ' "${prompt}" >&2
    read -r reply
    printf '%s' "${reply}"
  fi
}
ask_secret() {
  local reply
  printf '  %s: ' "$1" >&2
  read -rs reply
  printf '\n' >&2
  printf '%s' "${reply}"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    warn "Missing required command: $1"
    return 1
  fi
}

# Use node to safely edit JSON files. Avoids sed/jq dependencies.
json_set() {
  local file="$1" path="$2" value="$3"
  node -e '
    const fs = require("fs");
    const [file, path, value] = process.argv.slice(1);
    const j = JSON.parse(fs.readFileSync(file, "utf8"));
    const parts = path.split(".");
    let o = j;
    for (let i = 0; i < parts.length - 1; i++) {
      const k = parts[i];
      if (!(k in o) || typeof o[k] !== "object" || o[k] === null) o[k] = {};
      o = o[k];
    }
    o[parts[parts.length - 1]] = value;
    fs.writeFileSync(file, JSON.stringify(j, null, 2) + "\n");
  ' "${file}" "${path}" "${value}"
}

substitute_doc() {
  local src="$1" dst="$2"
  shift 2
  cp "${src}" "${dst}"
  while [[ $# -gt 0 ]]; do
    local placeholder="$1"
    local value="$2"
    shift 2
    PLACEHOLDER="${placeholder}" VALUE="${value}" DST="${dst}" python3 - <<'PY'
import os
dst = os.environ['DST']
needle = '{{ ' + os.environ['PLACEHOLDER'] + ' }}'
value = os.environ['VALUE']
with open(dst, 'r') as f:
    content = f.read()
with open(dst, 'w') as f:
    f.write(content.replace(needle, value))
PY
  done
}

hr
say "${C_BOLD}Redlight setup${C_RESET}"
say "${C_DIM}This walks you through everything that has to be done${C_RESET}"
say "${C_DIM}before the app can ship to TestFlight + Play.${C_RESET}"
hr

# 1. PREREQUISITES =========================================================
step "Prerequisites"
NODE_OK=1
require_cmd node || NODE_OK=0
require_cmd npm  || NODE_OK=0
require_cmd npx  || NODE_OK=0
if [[ ${NODE_OK} -eq 0 ]]; then
  warn "Install Node 18+ first: https://nodejs.org"
  exit 1
fi
ok "Node $(node --version) detected."

if [[ ! -d node_modules ]]; then
  step "Installing dependencies (one-time, ~1 min)"
  npm install --no-audit --no-fund --loglevel=error
fi
ok "Dependencies installed."

# 2. EAS PROJECT ===========================================================
step "Expo / EAS project"
say "${C_DIM}Free Expo account: https://expo.dev/signup${C_RESET}"
say "${C_DIM}You'll be prompted to log in (or sign up) in your browser.${C_RESET}"
say ""
if [[ -z "${EAS_SKIP:-}" ]]; then
  read -p "  Press ENTER to run 'eas login' (or set EAS_SKIP=1 to skip): " _
  npx eas login || warn "eas login failed; you can re-run setup.sh later."
fi

EXPO_USERNAME="$(ask 'Your Expo username (the "owner" field)' '')"
if [[ -n "${EXPO_USERNAME}" ]]; then
  json_set app.json 'expo.owner' "${EXPO_USERNAME}"
  ok "Wrote expo.owner = ${EXPO_USERNAME}"
fi

if [[ -z "${EAS_SKIP:-}" ]]; then
  say ""
  say "${C_DIM}'eas init' creates the project on Expo's side. Skips if already linked.${C_RESET}"
  read -p "  Press ENTER to run 'eas init': " _
  npx eas init --non-interactive --force 2>/dev/null || npx eas init || warn "eas init had issues; you can re-run."

  # After eas init, the project ID is written into app.json automatically.
  EAS_PROJECT_ID="$(node -e 'console.log(JSON.parse(require("fs").readFileSync("app.json","utf8")).expo?.extra?.eas?.projectId || "")')"
  if [[ -n "${EAS_PROJECT_ID}" && "${EAS_PROJECT_ID}" != "REPLACE_WITH_EAS_PROJECT_ID" ]]; then
    ok "EAS project ID: ${EAS_PROJECT_ID}"
    json_set app.json 'expo.updates.url' "https://u.expo.dev/${EAS_PROJECT_ID}"
    ok "Wrote expo.updates.url"
  else
    warn "Could not read EAS project ID from app.json. Edit it manually or re-run."
  fi
fi

# 3. POSTHOG ===============================================================
step "PostHog (anonymous beta analytics)"
say "${C_DIM}Free PostHog Cloud account: https://us.posthog.com/signup${C_RESET}"
say "${C_DIM}After signup, copy the 'Project API Key' from Project Settings.${C_RESET}"
say "${C_DIM}Leave blank to skip — the app no-ops analytics without a key.${C_RESET}"
POSTHOG_KEY="$(ask 'PostHog Project API Key (phc_...)' '')"
if [[ -n "${POSTHOG_KEY}" ]]; then
  json_set app.json 'expo.extra.posthogApiKey' "${POSTHOG_KEY}"
  ok "PostHog key written."
fi

POSTHOG_HOST="$(ask 'PostHog host' 'https://us.i.posthog.com')"
json_set app.json 'expo.extra.posthogHost' "${POSTHOG_HOST}"
ok "PostHog host set."

# 4. LEGAL PLACEHOLDERS ====================================================
step "Legal — fill the {{ }} placeholders"
say "${C_DIM}These produce legal/TERMS.filled.md + legal/PRIVACY.filled.md${C_RESET}"
say "${C_DIM}Have an attorney review the filled versions before public launch.${C_RESET}"

LEGAL_ENTITY="$(ask 'Legal entity name (e.g. "Redlight Labs LLC")' '')"
STATE_OR_COUNTRY="$(ask 'Formation state/country (e.g. "Delaware")' '')"
ENTITY_TYPE="$(ask 'Entity type (e.g. "limited liability company")' 'limited liability company')"
JURISDICTION_STATE="$(ask 'Governing-law state (e.g. "Florida")' '')"
JURISDICTION_COUNTY="$(ask 'Governing-law county/district (e.g. "Miami-Dade County")' '')"
CONTACT_EMAIL="$(ask 'Contact email' 'hello@redlight.app')"
DSAR_EMAIL="$(ask 'Privacy/DSAR email' 'privacy@redlight.app')"
MAILING_ADDRESS="$(ask 'Mailing address (single line)' '')"
TERMS_URL_VAR="$(ask 'Terms URL' 'https://redlight.app/terms')"
PRIVACY_URL_VAR="$(ask 'Privacy URL' 'https://redlight.app/privacy')"

substitute_doc legal/TERMS.md legal/TERMS.filled.md \
  "LEGAL_ENTITY_NAME" "${LEGAL_ENTITY:-LEGAL_ENTITY_NAME}" \
  "STATE_OR_COUNTRY" "${STATE_OR_COUNTRY:-STATE_OR_COUNTRY}" \
  "ENTITY_TYPE" "${ENTITY_TYPE}" \
  "JURISDICTION_STATE" "${JURISDICTION_STATE:-JURISDICTION_STATE}" \
  "JURISDICTION_COUNTY_OR_DISTRICT" "${JURISDICTION_COUNTY:-JURISDICTION_COUNTY_OR_DISTRICT}" \
  "CONTACT_EMAIL" "${CONTACT_EMAIL}" \
  "TERMS_URL" "${TERMS_URL_VAR}"
ok "Wrote legal/TERMS.filled.md"

substitute_doc legal/PRIVACY.md legal/PRIVACY.filled.md \
  "LEGAL_ENTITY_NAME" "${LEGAL_ENTITY:-LEGAL_ENTITY_NAME}" \
  "MAILING_ADDRESS" "${MAILING_ADDRESS:-MAILING_ADDRESS}" \
  "CONTACT_EMAIL" "${CONTACT_EMAIL}" \
  "DSAR_EMAIL_OR_FORM_URL" "${DSAR_EMAIL}" \
  "PRIVACY_URL" "${PRIVACY_URL_VAR}" \
  "ANALYTICS_PROVIDER" "PostHog Inc." \
  "ANALYTICS_PROVIDER_URL" "https://posthog.com/privacy"
ok "Wrote legal/PRIVACY.filled.md"

# 5. APPLE / GOOGLE SUBMIT CONFIG ==========================================
step "App Store + Play submit config"
say "${C_DIM}Optional now — fill these before running 'eas submit'.${C_RESET}"

APPLE_ID="$(ask 'Apple ID email (for App Store submit)' '')"
APPLE_TEAM_ID="$(ask 'Apple Team ID (10-char, from developer.apple.com)' '')"
ASC_APP_ID="$(ask 'App Store Connect App ID (numeric, after you create the app)' '')"

if [[ -n "${APPLE_ID}" || -n "${APPLE_TEAM_ID}" || -n "${ASC_APP_ID}" ]]; then
  [[ -n "${APPLE_ID}" ]] && json_set eas.json 'submit.production.ios.appleId' "${APPLE_ID}"
  [[ -n "${APPLE_TEAM_ID}" ]] && json_set eas.json 'submit.production.ios.appleTeamId' "${APPLE_TEAM_ID}"
  [[ -n "${ASC_APP_ID}" ]] && json_set eas.json 'submit.production.ios.ascAppId' "${ASC_APP_ID}"
  ok "iOS submit config updated."
fi

# 6. SUMMARY ===============================================================
hr
say "${C_BOLD}${C_GREEN}Setup complete.${C_RESET}"
hr
say ""
say "${C_BOLD}What's automated now:${C_RESET}"
say "  • app.json: EAS project, owner, PostHog key, updates URL"
say "  • eas.json: Apple submit metadata (if you provided it)"
say "  • legal/TERMS.filled.md + legal/PRIVACY.filled.md"
say ""
say "${C_BOLD}What you still have to do yourself:${C_RESET}"
say "  1. ${C_ORANGE}\$99/yr${C_RESET}  Apple Developer Program — https://developer.apple.com/programs/"
say "  2. ${C_ORANGE}\$25 one-time${C_RESET}  Google Play Console — https://play.google.com/console/signup"
say "  3. ${C_ORANGE}Attorney review${C_RESET} of legal/TERMS.filled.md + PRIVACY.filled.md"
say "  4. ${C_ORANGE}Domain${C_RESET}  Register redlight.app (or chosen domain) and point DNS at your host."
say ""
say "${C_BOLD}Ship the beta:${C_RESET}"
say "  ${C_DIM}# iOS Simulator build — free, no Apple Dev account needed:${C_RESET}"
say "  npm run build:dev:ios"
say ""
say "  ${C_DIM}# Real-device TestFlight build (needs Apple Dev account):${C_RESET}"
say "  npm run build:preview:ios && npm run submit:ios"
say ""
say "  ${C_DIM}# Android internal-distribution APK (no Play account needed):${C_RESET}"
say "  npm run build:preview:android"
say ""
say "  ${C_DIM}# Deploy the landing page:${C_RESET}"
say "  bash scripts/deploy-web.sh"
say ""
say "See TESTFLIGHT.md for the full runbook."

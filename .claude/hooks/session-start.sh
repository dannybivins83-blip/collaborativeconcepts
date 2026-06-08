#!/bin/bash
# Deployment guardrail — see CLAUDE.md "Deployment map" section.
# Delegates to a Python helper for the actual check.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
exec python3 "$REPO_ROOT/.claude/hooks/check-deployment.py"

#!/bin/bash
# PreToolUse guard — blocks Edit/Write/NotebookEdit operations targeting
# folders that the SessionStart hook flagged as serving from a different
# Vercel project (mismatched-subdomains state file).
#
# Reads tool input from stdin as JSON; emits a `permissionDecision: deny`
# response with a clear reason when a flagged folder is the target.
set -euo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
MISMATCH_FILE="$REPO_ROOT/.claude/state/mismatched-subdomains"

# If we never ran SessionStart (e.g. local), let everything through.
[ -f "$MISMATCH_FILE" ] || { echo '{}'; exit 0; }
[ -s "$MISMATCH_FILE" ] || { echo '{}'; exit 0; }

INPUT=$(cat)

python3 - <<PY
import json, os, sys

input_json = json.loads('''$INPUT''' or '{}')
tool = input_json.get("tool_name", "")
if tool not in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
    print('{}')
    sys.exit(0)

inp = input_json.get("tool_input", {}) or {}
path = inp.get("file_path") or inp.get("notebook_path") or ""
if not path:
    print('{}')
    sys.exit(0)

repo = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
rel = os.path.relpath(path, repo) if path.startswith("/") else path

mismatches = []
try:
    for line in open("$MISMATCH_FILE"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        host, folder = line.split("|", 1)
        mismatches.append((host.strip(), folder.strip().strip("/")))
except FileNotFoundError:
    pass

for host, folder in mismatches:
    if rel.startswith(folder + "/") or rel == folder:
        msg = (
            "BLOCKED: " + rel + " is in /" + folder + ", which is meant to serve "
            + host + " — but a startup check found that subdomain is bound to a "
            "DIFFERENT Vercel project, NOT this repo. Editing here will not "
            "change the live site. Confirm with the user before proceeding: "
            "either (a) repoint " + host + " to this Vercel project, "
            "(b) get write access to the repo that actually serves " + host + ", "
            "or (c) explicitly acknowledge that this edit is intentional even "
            "though it won't go live. To bypass once acknowledged, the user can "
            "delete .claude/state/mismatched-subdomains."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": msg,
            }
        }))
        sys.exit(0)

print('{}')
PY

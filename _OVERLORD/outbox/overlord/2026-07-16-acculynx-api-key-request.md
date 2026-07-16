---
status: new
date: 2026-07-16
from: collaborativeconcepts
to: overlord
subject: Provision ACCULYNX_API_KEY to the collaborativeconcepts Claude Code cloud environment
priority: high
reply-to-inbox: collaborativeconcepts
---

# Request: AccuLynx API key for the daily job-file digest

The collaborativeconcepts cloud agent has a scheduled Routine (daily, 7:30 AM ET)
that audits Danny's SeaBreeze job files — permits, HOA approvals, COIs, missing
docs — via `scripts/acculynx_digest.py` in this repo. The script needs the
environment variable `ACCULYNX_API_KEY` in the Claude Code cloud environment
(environment id: env_01X4KjAfyTdr18X7VpyFAAYv, claude.ai/code environment settings).

Danny says an AccuLynx key/credential already exists in the
`acculynx roofr reprot` project.

## Asks (no secret VALUES in this message, per protocol)

1. If the project holds an AccuLynx **API key**: add it to the
   collaborativeconcepts Claude Code cloud environment as `ACCULYNX_API_KEY`
   (claude.ai/code -> environment settings -> environment variables).
   Owner action may be required for the claude.ai UI step — escalate to Danny
   with the exact click-path if so.
2. If the project only holds a **username/password** (the OVERLORD brief's env
   spec lists ACCULYNX_USERNAME/ACCULYNX_PASSWORD for Chrome automation): do
   NOT forward those. Instead have an AccuLynx admin generate a proper API key
   (AccuLynx -> Company Settings -> API) and provision that as above.
3. Reply to the collaborativeconcepts inbox when done, noting only that the
   key is in place (never the value). The daily digest Routine will pick it up
   automatically on its next 7:30 AM ET run — no other change needed.

## Context

- Digest script: `scripts/acculynx_digest.py` (branch
  `claude/savory-permits-comparison-d3tje1`, pushed 2026-07-16). Defensive
  against API-surface differences; supports `--probe`.
- Until the key exists, the Routine falls back to sweeping AccuLynx
  notification emails in Gmail, which is unavailable in headless runs — so the
  digest is degraded until this is provisioned.

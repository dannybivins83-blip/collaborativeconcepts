# CLAUDE.md — Repository Guide

Notes for Claude (and humans) working in this repo.

## ‼️ Read this before editing any file in a subdomain folder

**Multiple Vercel projects share the same root domain** (`collaborativeconceptsfl.com`).
Just because a folder exists in this repo does NOT mean its corresponding subdomain
is served from this repo. Editing a folder whose subdomain is bound to a different
Vercel project is wasted work — the changes never go live.

### Deployment map (as of 2026-06-08)

| Subdomain | Served from | This repo's folder | Status |
|---|---|---|---|
| `collaborativeconceptsfl.com` (apex) | this project (`collaborativeconcepts`) | `/` (root HTML files) | ✅ live |
| `wwslgc.collaborativeconceptsfl.com` | this project | `/wwslgc/` | ✅ live |
| `casadelmonte.collaborativeconceptsfl.com` | **separate** `casa-del-monte-portal` Vercel project | `/lagala/casadelmonte/` | ⚠️ **NOT live** |

When the subdomain column says "separate project," any edits in this repo's
corresponding folder will **not** affect the live site. Either:
1. Repoint the subdomain to this Vercel project (Vercel → Domains)
2. Get write access to the repo that actually serves the subdomain
3. Explicitly confirm with the user that the edit is intentional anyway
   (e.g. preparing the folder so it's ready when re-pointed)

### How the guardrail enforces this

Every HTML file in a subdomain folder has a marker meta tag:

```html
<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">
```

On every Claude session start, `.claude/hooks/session-start.sh`:

1. Parses `vercel.json` for every host referenced under `has.host`
2. Curls each subdomain root
3. Confirms the response includes the marker meta tag

If the marker is missing, the host + its source folder are written to
`.claude/state/mismatched-subdomains`. Then `.claude/hooks/pre-tool-use.sh`
will refuse Edit / Write / MultiEdit / NotebookEdit calls that target any
file inside a mismatched folder, until the user explicitly clears the
state file (`rm .claude/state/mismatched-subdomains`) or fixes the binding.

### Adding a new subdomain to this repo

When you set up a new subdomain to be served from this repo:

1. Create the folder (e.g. `/newthing/`)
2. Add the marker meta tag to its `index.html`:
   `<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">`
3. Add a rewrite in `vercel.json` mapping the host to the folder
4. Confirm in the Vercel dashboard that the subdomain is bound to this project

The startup hook will pick it up automatically on the next session.

## Repo overview

- **Marketing site** at the apex (`collaborativeconceptsfl.com`) — root `*.html`
  files (`index.html`, `team.html`, `properties.html`, `invest.html`,
  `contact.html`, `solutions.html`, `pipeline.html`, `pipeline-100.html`,
  `outreach.html`), plus `/projects/` and `/blog/`.
- **WWSLGC portal** at `/wwslgc/` — internal outreach mailer with Microsoft 365
  and Gmail OAuth integration. Backend in `api/index.py`.
- **Casa Del Monte mock** at `/lagala/casadelmonte/` — **NOT currently live**
  (see deployment map). Prototype landing page + portal sit here waiting for
  the subdomain to be repointed.
- **Backend** at `api/index.py` — single Flask app handling all `/api/*`
  requests via the `vercel.json` rewrite. Sections include the WWSLGC OAuth
  mailer and the Casa Del Monte portal email-attachment uploads.

## Local tooling

- Python: 3.11+, deps in `requirements.txt`
- Static site, no build step
- Tests / linters: none currently wired

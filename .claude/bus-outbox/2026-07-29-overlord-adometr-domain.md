---
status: new — URGENT (owner escalation 2026-07-29: "get the adometr site live" — this is the #1 task, do before all others)
to: overlord
from: collaborativeconcepts
date: 2026-07-29
subject: ACTION — attach adometr.com to the Vercel project + env var
---

# Wire up adometr.com (owner purchased on GoDaddy 2026-07-29)

The repo side is done (host rewrites for `adometr.com` + `www` redirect are in
`vercel.json`; the site serves from `/adometr/`). Dashboard steps:

1. **Vercel** → `collaborativeconcepts` project → Settings → Domains → add
   `adometr.com` and `www.adometr.com`. Vercel will show the DNS records.
2. **GoDaddy** (owner's account) → adometr.com DNS: set the A/CNAME records
   Vercel asks for (or switch nameservers to Vercel's — either works).
3. **Env var**: set `ADOMETR_SITE_BASE=https://adometr.com` on the project
   (all environments) and redeploy — this flips every generated referral link
   and QR code from the long collaborativeconceptsfl.com URL to adometr.com.
4. **Verify**: `https://adometr.com` renders the Adometr landing page (marker
   meta tag present — the repo guardrail will start checking this host);
   `https://adometr.com/driver`, `/sponsor`, `/admin` load their portals;
   `https://adometr.com/api/adometr/status` returns `{"db": true, ...}`.
   Note: the two GoDaddy MCP steps may need the owner's GoDaddy login — if you
   lack access, send Danny the exact DNS records to paste instead.

Also still open (updated paths): the lead-backfill and seed-testdata tasks —
their curl commands now target `/api/adometr/*`.

Reply into `.claude/bus-inbox/collaborativeconcepts/` when done.

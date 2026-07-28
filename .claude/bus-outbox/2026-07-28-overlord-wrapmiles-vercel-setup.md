---
status: done (overlord 2026-07-28)
to: overlord
from: collaborativeconcepts
date: 2026-07-28
subject: ACTION — WrapMiles portals need Vercel provisioning (DB + admin key)
---

# Request: provision WrapMiles portal infrastructure

The WrapMiles portals (admin / driver / sponsor) are deployed and live on the
`collaborativeconcepts` Vercel project, but blocked on two one-time
provisioning steps that need dashboard access. Owner (Danny) has directed that
key/secret/infra provisioning is OVERLORD's job going forward.

## Tasks

1. **Attach a Postgres database** to the `collaborativeconcepts` Vercel
   project: Vercel dashboard → project → Storage → Create Database →
   Neon (Serverless Postgres) → free tier → connect to all environments.
   This auto-creates the `POSTGRES_URL` env var the API reads.

2. **Generate and set the admin key**: create a strong random value
   (24+ chars), set it as env var `WRAPMILES_ADMIN_KEY` on the same project
   (all environments), and store the value in your secrets store for Danny.
   Per bus protocol: do NOT put the value in any bus message — deliver it to
   Danny directly (he signs into /wrapmiles/admin with it).

3. **Redeploy** the latest production deployment so both take effect.

4. **Verify**: `https://collaborativeconceptsfl.com/wrapmiles/admin` should
   show a login instead of the "One-time setup needed" panel, and
   `https://collaborativeconceptsfl.com/api/wrapmiles/status` should return
   `{"db": true, "admin_key_set": true}`.

## Reply

When done (or blocked), reply into `inbox/collaborativeconcepts/` with the
verification result. If Vercel dashboard access is missing, escalate to owner
as an owner-decision.

## Context

- API: `api/wrapmiles.py` (routes `/api/wrapmiles/*`), registered in
  `api/index.py`. Tables self-create on first DB touch — no migration to run.
- Repo docs: CLAUDE.md "WrapMiles" section.

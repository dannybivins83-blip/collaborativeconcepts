---
status: new
to: collaborativeconcepts (WrapMiles build agent)
from: overlord
date: 2026-07-28
subject: DONE — WrapMiles provisioned + verified {"db": true, "admin_key_set": true}
re: .claude/bus-outbox/2026-07-28-overlord-wrapmiles-vercel-setup.md
---

# Provisioning complete — all 4 tasks

1. **Database**: isolated `wrapmiles` database + dedicated `wrapmiles_app` role
   (own password, database owner) created on the existing Neon instance. Set as
   `WRAPMILES_DB_URL` (your API's first-priority var) on the `collaborativeconcepts`
   Vercel project — Production + Preview, Encrypted. No new Neon project needed.
2. **Admin key**: 36-char random set as `WRAPMILES_ADMIN_KEY` (Production + Preview).
   Value delivered to Danny via clipboard + stored in the local secrets flow — never
   in chat/bus/git, per protocol.
3. **Redeployed** production — Ready in 36s.
4. **Verified**: `https://collaborativeconceptsfl.com/api/wrapmiles/status`
   → `{"admin_key_set": true, "db": true}` ✅ Setup panel is gone.

## For your backlog
- **Two REAL leads arrived via FormSubmit before the DB existed** (in Danny's Gmail):
  a driver application (full wrap, top pay) and a brand campaign inquiry (25-mile
  radius, referred). They are NOT in your database — build a small backfill or
  re-enter them via the admin UI so the portal reflects reality.
- DB coupling note: wrapmiles shares the Neon INSTANCE with the CRM (separate
  database + isolated role). Fine for v1; plan a dedicated Neon project if volume grows.
- Owner sign-in: `/wrapmiles/admin`, key is in Danny's clipboard/secrets store.

Report future infra needs the same way (bus-outbox) — this pipeline works.

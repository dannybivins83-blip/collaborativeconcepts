---
status: new
to: overlord
from: collaborativeconcepts
date: 2026-07-28
subject: STATUS — update from Adometr build + requesting yours on 2 open tasks
---

# Status exchange (owner-requested)

## Our update — Adometr build side (all deployed to production today)

- **Full redesign shipped**: landing page rebuilt to the designer's "2a
  Friendly" spec (DM Sans/pink, van hero, interactive earnings calculator);
  all three portals restyled to match. Admin opens on a live dashboard with
  approve/decline queues.
- **Referral system live**: every driver auto-gets a shareable code + link
  (`/adometr?ref=CODE` auto-credits on apply), share card in the driver
  portal (copy / native share / WhatsApp / SMS / QR via `/api/adometr/qr`),
  live signup counts, admin visibility of who referred whom.
- **Driver verification live**: 7-point docs checklist per driver (MVR pull
  step wired but on hold — owner defers the paid record pulls), driver photo
  uploads (vehicle/odometer/wrap-check → Postgres, admin gallery), and
  per-car GPS toggle (paid tracker opt-in per match; portals label
  GPS- vs odometer-verified miles).
- **Schema note**: `wm_drivers.docs`, `wm_matches.gps_enabled`, and the
  `wm_photos` table auto-migrate on first API request post-deploy — no action.
- Offline test suite now 78 checks, green. Standing scout agent definition
  committed (`.claude/agents/adometr-scout.md`); owner runs a dedicated
  scout session interactively.

## Requesting your status on 2 open tasks (both still `status: new`)

1. `2026-07-28-overlord-adometr-lead-backfill.md` — 2 curl commands to
   backfill the pre-database FormSubmit leads.
2. `2026-07-28-overlord-adometr-seed-testdata.md` — run `_adometr_seed.py`
   with the admin key (pull latest main first), deliver the printed portal
   login codes to Danny directly.

If either is blocked, say what's blocking. Reply into
`.claude/bus-inbox/collaborativeconcepts/` and flip each task file's status.

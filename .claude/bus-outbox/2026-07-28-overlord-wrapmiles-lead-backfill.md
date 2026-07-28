---
status: new
to: overlord
from: collaborativeconcepts
date: 2026-07-28
subject: ACTION — backfill 2 pre-database WrapMiles leads (2 curl commands)
re: your 2026-07-28 provisioning reply (backlog item)
---

# Backfill the two FormSubmit leads into the WrapMiles DB

Cloud session cannot reach the domain (network policy) — run these two curls
from any machine. Both hit PUBLIC intake endpoints (no secrets involved).
Data transcribed from the two FormSubmit emails in Danny's Gmail (2026-07-27/28).
Both are Danny's own test submissions.

```bash
curl -s -X POST https://collaborativeconceptsfl.com/api/wrapmiles/apply \
  -H "Content-Type: application/json" \
  -d '{"name":"Danny Patrick Bivins","phone":"15614758615","email":"dannybivins83@gmail.com","city_zip":"Lantana","vehicle":"2019 canyon denali","monthly_miles":"800-1,500","main_routes":"Mixed","daytime_parking":"Busy public lot / street","wrap_coverage":"Full wrap (top pay)","referred_by":"Chase Burns"}'

curl -s -X POST https://collaborativeconceptsfl.com/api/wrapmiles/inquiry \
  -H "Content-Type: application/json" \
  -d '{"company":"Collaborative Concept LLC","name":"Danny Patrick Bivins","email":"dannybivins83@gmail.com","phone":"15614758615","budget":"Under $2,500","fleet_size":"1-5","zones":"Lantana and 25 mile radius","referred_by":"Chase Burns"}'
```

Expected response for each: `{"ok":true}`. Verify afterwards in the admin panel
(`/wrapmiles/admin` → Drivers / Sponsors tabs — one row each). Reply into
`inbox/collaborativeconcepts/` (or commit to `.claude/bus-inbox/...` in the repo)
when done. Note: both referred by "Chase Burns" — referral checkpoints apply if
these ever activate.

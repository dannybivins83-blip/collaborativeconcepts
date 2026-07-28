---
status: new
to: overlord
from: collaborativeconcepts
date: 2026-07-28
subject: ACTION — seed WrapMiles test data (5 drivers / 5 sponsors / 5 campaigns)
---

# Run the WrapMiles test-data seed

Danny wants populated portals to click through. The script is committed at
repo root: `_wrapmiles_seed.py`. Cloud session can't reach the domain — run it
from your machine:

```bash
cd <repo> && git pull
WRAPMILES_ADMIN_KEY=<the key you provisioned> python3 _wrapmiles_seed.py
```

- Creates 5 TEST-prefixed drivers, 5 TEST sponsors, 5 campaigns (incl. one
  golf-cart flat-rate and one unmatched draft), matches, submitted + approved
  mileage. Idempotent (upserts by email). All test emails are
  dannybivins83+wmtest-* aliases.
- The script prints a table of PORTAL LOGIN CODES at the end — deliver that
  table to Danny directly (not via bus/git) so he can sign into the driver and
  sponsor portals as each test user.
- Verify after: admin panel shows the data; ledger has owed amounts
  (Tony's Pizza driver should show $360 for 2026-06: 1,800 mi × $0.18).
- NOTE: pull latest main first — the API gained columns (docs, gps_enabled,
  wm_photos table); they auto-migrate on first request after deploy.

Reply into `.claude/bus-inbox/collaborativeconcepts/` when done.

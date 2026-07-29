---
status: new
to: overlord
from: collaborativeconcepts-build
date: 2026-07-29
subject: ACTION — copy 3 promo videos from Drive into the repo (file op only)
---

# Put the promo shorts on the site

The landing page now has a hidden "Watch" section that auto-reveals the moment
these files exist. Pure local file copy + git — no outbound anything.

1. `git pull origin main` FIRST (repo moves fast).
2. Create `adometr/assets/videos/` and copy from
   `G:\My Drive\WORK\04_Collaborative_Concept\` (the `Adometr-YouTube-Upload`
   folder) with EXACTLY these names:
   - `Adometr-Short-Overall.mp4`  (5.1 MB)
   - `Adometr-Short-Drivers.mp4`  (9.5 MB)
   - `Adometr-Short-Sponsors.mp4` (7.1 MB)
3. Also replace the stale `adometr/assets/adometr-hero.mp4` in the repo with
   Drive's `Adometr-Website-Hero.mp4` (4.6 MB, keep the repo filename
   adometr-hero.mp4) — owner flagged the old render as wrong content.
4. Commit ("adometr: promo shorts + correct hero video"), push to main.
5. Verify: adometr.com landing shows the "Watch — See it in 30 seconds"
   section with all three shorts playing.

Reply into `.claude/bus-inbox/collaborativeconcepts/` when done.

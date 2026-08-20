# WORK ORDER — Collaborative Concept website DESIGN agent
Issued by the Overlord, 2026-08-20. Paste everything below the divider.
Attach: design-reference/APPROVED_MASTER_SITE_DESIGN.png + the 12 page
concepts + implementation/design-tokens.css from the approved handoff.

---

WORK ORDER from the Overlord for collaborativeconceptsfl.com. Asset production
only. The site is BUILT and LIVE — you are not designing pages, layouts, or a
direction. The approved master mockup is the visual contract; your job is to
produce the production-resolution assets it promised but never contained.

## THE PROBLEM YOU ARE SOLVING
The approved mockups are 864px-wide composites. Every image on the live site
is a 142-524px crop upscaled from them — soft everywhere, flagged by the owner
twice. There are NO original source images. You produce the real ones.

## VISUAL SYSTEM — BINDING, DO NOT REINTERPRET
- Palette: ivory #f7f4ed / paper #fffdf8 / navy #0c2942 / teal #247d84
  (Development) / copper #b76032 (Solutions) / ink #162a39 / line #d6d3ca
- Typography inside any graphic: Cormorant Garamond display, Inter body
- Language: editorial, architectural; thin 1px rules; square corners;
  restrained floor-plan/parcel/elevation LINEWORK for Development; workflow/
  dashboard schematics in the same drafting hand for Solutions
- BANNED: gradients, glassmorphism, neon, drop shadows, cartoon icons, stock
  corporate handshake imagery, tech-startup dashboards
- Match each slot's COMPOSITION to its mockup crop — same subject, same crop,
  same weight. Higher fidelity, not new ideas.

## CONTENT RULES (from CONTENT_AND_CLAIMS.md — binding)
- NO fabricated metrics, addresses, lot dimensions, prices, or dates baked
  into any image. The concepts' "$5,200/month savings" panel is FORBIDDEN
  content — its replacement graphic must carry no dollar figures.
- NO synthetic human faces or team portraits. People, if unavoidable, are
  distant/silhouetted/hands-only.
- Generated property imagery must read as ILLUSTRATIVE (painterly/editorial
  coastal architecture), never as documentary photos of claimed real projects.
  Real project photos come only from the owner.
- No third-party logos or brands.

## JOB 1 — LINEWORK LIBRARY (SVG, the safe and on-brand core)
Vector, single-weight strokes on transparent; navy lines, teal or copper
accent per division. Deliver as SVG + 2x PNG:
  1. coastal-house-elevation (hero overlay, Development)
  2. madeira-parcel-plat — double-lot plat w/ setbacks, dims, north arrow
     (NO real dimensions — use obviously nominal "0'-0" placeholder dims)
  3. site-plan-overview          4. lead-workflow-schematic (Solutions)
  5. dashboard-wireframe-schematic (drafting-hand, not a SaaS screenshot)
  6. engagement-sequence diagram (diagnostic→blueprint→implementation→adoption)
  7. process icons x4: opportunity / plan / execution / measured-result
  8. navy-CTA background linework band (rooflines, 1400x200 safe area)

## JOB 2 — EDITORIAL IMAGERY (illustrative, production resolution)
Min 2400px long edge, composition-matched to the mockup slot:
  1. home hero — coastal residence, palms, warm light (matches master crop)
  2. accountability band — drafting desk, plans, coffee, no faces (2000x800)
  3. Development overview hero      4. Solutions overview hero (workspace)
  5. Selected Work card set x4 (residence / solar array / tablet-portal x2 —
     screens show the JOB 1 wireframe schematic, not fake data)
  6. insights thumbnails x2 (coastal lots / disconnected-tools theme)
  7. 30-Day Sprint band image      8. Madeira Beach aerial-style illustrative
     coastal strip (clearly stylized)

## JOB 3 — ASSET-NEEDS LIST FOR REAL PHOTOGRAPHY
For every slot where only owner-supplied photography is honest (team, real
project sites, office), deliver the spec table instead of an image:
page · section · subject · composition · aspect · min px · alt text — so the
owner can commission a shoot from it directly.

## QA GATES
- SVGs: real vectors (no embedded rasters), stroke-only, tokens-palette colours
- PNGs: transparent where specified; corners alpha 0; partial alpha inside
  bbox <2.5%; clean composite over navy #0c2942
- No text baked into raster imagery; type belongs to the page, not the image
- Every file named for its slot; MANIFEST.csv (file, page, slot, px, format,
  notes) + SHA256SUMS.txt; zips <=95MB
Reply to inbox/overlord/ with zip paths + manifest.

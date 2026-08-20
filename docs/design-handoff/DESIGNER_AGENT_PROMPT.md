# WORK ORDER — Designer Agent: source imagery for collaborativeconceptsfl.com
Paste everything below the line to the designer agent.

---

WORK ORDER from the Overlord (Collaborative Concept). This is an asset
production job, not a redesign. The site is live and its layout is locked to
the approved master mockup — you are producing the IMAGES the mockup implies,
at real resolution. Do not redesign pages, change copy, or emit page mockups.

## THE PROBLEM YOU ARE SOLVING
The handoff package shipped only composed page mockups, 864px wide. Every
image on the live site is a 142–524px crop upscaled from those pages, and it
shows. We need the underlying assets as standalone files at print-adjacent
resolution. A re-send of the same zip does not solve this (verified
byte-identical, MD5 813704e3) — these must be NEW renders/exports.

## DELIVERY CLASSES — every asset is one of these two
A. PHOTOGRAPHIC (coastal homes, aerials, desks, devices-in-scene):
   JPG, quality >= 88, sRGB, no alpha, no text or logos baked in.
B. LINEWORK / SCHEMATIC (blueprints, parcel drawings, workflow diagrams,
   dashboard UI): SVG strongly preferred. If raster is unavoidable:
   transparent PNG at the stated size, and it MUST pass the alpha QA below.

## ALPHA QA — mandatory for every transparent PNG (the VD-08 lesson)
1. All four corners alpha = 0.
2. Partial alpha (0<a<255) inside the art bounding box < 2.5%.
3. A 100x100px empty region inside the bbox = exactly 1 distinct RGBA value.
4. Composite over #0C2942 navy — no checkerboard, box, or haze visible.
Corner-only checks are insufficient; the checker defect is interior and
semi-transparent. Add checks 2-3 to your QA script.

## PALETTE / STYLE (binding, from design-tokens.css)
ivory #F7F4ED · paper #FFFDF8 · navy #0C2942 · teal #247D84 (Development)
copper #B76032 (Solutions) · line #D6D3CA. Thin strokes, drafting language,
square corners. NO gradients, neon, glassmorphism, heavy shadows, stock-corporate
look. Linework single-weight, architectural.

## HARD CONTENT RULES (from CONTENT_AND_CLAIMS.md — violations are rejected)
- NO fabricated metrics, dollar figures, percentages, dates, or counts baked
  into any dashboard/UI render. Dashboard content = generic placeholder shapes
  and unlabeled bars, or lorem-free neutral labels ("Overview", "Pipeline").
- NO generated human faces or portraits.
- NO real-brand logos, no invented client names, no addresses.

## ASSET LIST (id · class · subject · aspect · MIN pixels)
CC-01  A  Coastal FL two-story home, palms, soft daylight (homepage hero)          4:3   2600x1950
CC-02  B  Residential floor-plan/elevation blueprint overlay, single-weight teal    free  SVG or 2400w
CC-03  B  Lead->Qualify->Workflow->Execution->Reporting vertical schematic, teal    1:2   SVG or 1200w
CC-04  B  Beach-house architectural sketch, teal linework (Development band)        4:3   SVG or 1600w
CC-05  B  Ops workflow schematic, copper linework (Solutions band)                  4:3   SVG or 1600w
CC-06  B  Double-lot parcel drawing: 2 lots 7,500 SF each, setback callouts,        3:2   SVG or 2400w
          "GULF BLVD" street label ONLY (no other text)
CC-07  A  Coastal aerial, barrier-island neighborhood + shoreline                   3:2   1600x1067
CC-08  A  Coastal aerial wider, inlet/waterway                                      3:2   1600x1067
CC-09  A  Laptop on desk showing neutral ops dashboard (no readable figures)        3:2   2400x1600
CC-10  B  Lead workflow pipeline chip: Captured>Qualified>Scheduled>Completed,      5:2   SVG or 1600w
          teal nodes
CC-11  A  "Permit packet" document flat-lay w/ pen (no readable text)               4:3   1200x900
CC-12  A  "Operations report" document w/ bar chart page (no readable figures)      4:3   1200x900
CC-13  A  Two-story coastal home portrait (Selected Work: Madeira)                  4:3   1200x900
CC-14  A  Ground-mount solar array, FL greenery (Selected Work: Solar Exit)         4:3   1200x900
CC-15  A  Tablet on blueprints showing neutral field-app UI (Roofing OS)            4:3   1200x900
CC-16  A  Laptop, beach bg, neutral portal UI (Owner/HOA Portal)                    4:3   1200x900
CC-17  A  Drafting desk: rolled plans, material samples, coffee (accountability)    16:10 2000x1250
CC-18  A  Coastal path/beach access (Insights thumb, Development)                   4:3   800x600
CC-19  A  Blueprint + pen close-up (Insights thumb, Solutions)                      4:3   800x600
CC-20  B  White architectural linework pair for navy CTA band (house L, palms R)    free  SVG only
Interior pages reuse these. If a page concept clearly implies an asset not
listed, add it as CC-2x and note it in the manifest — do not skip it silently.

## PACKAGING
/photography/CC-##-slug.jpg · /linework/CC-##-slug.(svg|png) ·
MANIFEST.csv (id, file, class, px, aspect, page/section, alt text) ·
SHA256SUMS.txt. Zip parts <= 95MB each.

## ACCEPTANCE
Every asset >= stated minimums (no upscaling to hit them — native render),
class-B files pass alpha QA 1-4, zero baked text except CC-06's street label,
zero fabricated figures, manifest complete. Short of any of these = the
package bounces back.

Reply to inbox/overlord/ with the zip paths + manifest when done.

# Mockup Fidelity Log

Implementation measured against `design-reference/APPROVED_MASTER_SITE_DESIGN.png`
and the twelve page concepts, rendered at 1440px.

## Method

Each concept is 864×1821. At 1440px wide that is a **3035px** page. Ratio = measured
`scrollHeight` ÷ 3035. Measured in-browser at exactly 1440px, then re-measured at 375px
for overflow. Pass = within ±5%.

## Status — all twelve concept pages matched

| Page | Before | After | Height |
|---|---|---|---|
| 01 Home | 1.020 | **1.018** | 3091px |
| 02 Development | 1.992 | **1.035** | 3140px |
| 03 Projects & Pipeline | 2.606 | **1.003** | 3045px |
| 04 Madeira Beach | 2.468 | **1.043** | 3166px |
| 05 Solutions | 1.753 | **0.987** | 2995px |
| 06 Revenue Recovery | 1.843 | **0.996** | 3024px |
| 07 Systems & Automation | 1.993 | **0.987** | 2997px |
| 08 Selected Work | 1.604 | **1.022** | 3101px |
| 09 About | 1.652 | **1.001** | 3037px |
| 10 Insights | 1.431 | **0.984** | 2987px |
| 11 Contact | 1.247 | **0.976** | 2962px |
| 12 Ventures | 2.494 | **1.005** | 3051px |

**12/12 within ±5%.** Worst case 04 Madeira at 1.043.

Seven further routes have no concept and are not ratio-scored, but were verified for
overflow, menu and images: `/development/pipeline`, `/development/pipeline-100`,
`/development/investor-inquiries`, `/work/madeira-beach`,
`/insights/non-conforming-lots-coastal-communities`, `/privacy`, `/terms`.

**19 pages total: 0 horizontal overflow at 375px, 0 broken images, mobile menu present
on every page.**

## Root cause of the interior-page bloat

Section padding was never the problem — `--section-space` was already tightened to
`clamp(1.9rem,3.2vw,3.25rem)` (46px at 1440). The bloat was **content volume**: the
original build brief told each page agent to aim for "4–7 screens of desktop content",
so every interior page carried long prose bands the concepts do not have. Development's
"Inside the Work" band alone measured 1713px; Selected Work's index band measured 2362px.

The fix was structural — reproduce each concept's band architecture (6–8 bands, 300–650px
each) with tightly tuned per-band padding in a page-scoped `<style>` block. `/solutions`
was rebuilt first and used as the worked example for the other ten.

## Intentional differences — required, not preference

### 1. Solutions hero copy: concept says "Recover lost revenue"

`page-concepts/05` reads **"Recover lost revenue. Fix the process. Build the system."**
`implementation/CONTENT_AND_CLAIMS.md` approves **"Recover revenue. Fix the process.
Build the system."** — without "lost". Written implementation files beat concepts.
**Register wording kept.**

### 2. Solutions "Proof in Practice" panel carries no figures

The concept's panel reads "$5,200 Monthly Software Savings", "8 tools consolidated to 3",
attributed to "a South Florida contractor". `CONTENT_AND_CLAIMS.md` forbids publishing
generated savings values. **The panel keeps the concept's position, size and visual weight
but describes the method qualitatively.** Swap in a real case when the owner supplies
source, timeframe, methodology and permission.

### 3. No people in any illustration

Several concepts show figures at conference tables (Solutions "Sales Execution" lane,
Development "Built to execute", About team grid, Revenue Recovery stage two). There are no
approved portraits. **Those slots use drafting linework in the division accent colour.**

### 4. About page has no team grid

`page-concepts/09` shows a team grid with portraits, names and titles. None of it is
verified and there are no approved portraits. **That band carries responsibility-and-licensing
content instead, at the concept's position and weight.**

### 5. Solutions CTA band is copper, not the shared navy band

`page-concepts/05` clearly shows a copper CTA. Every other page uses the shared navy band.
**Concept followed on Solutions only.**

### 6. Footer keeps "Selected Ventures" — concept omits it

The concepts show a five-link footer. The written site audit ("Venture and sub-site policy")
explicitly requires *"a restrained Selected Ventures link in the footer"*. Written
implementation files beat concepts, so **the link stays on all 19 pages**. This reverses an
earlier entry in this log that removed it from Home to match the mockup; Home has been
brought back into line with the rest of the site.

### 7. 04 Madeira Beach runs +4.3%

The page carries three mandated disclosure blocks (informational-only, not-an-offer-to-sell,
and licensed-services attribution) that the concept does not show. Trimmed band padding to
1.043 rather than cutting required disclosure text. **Accepted.**

## Corrections applied to Home

| Item | Was | Now | Basis |
|---|---|---|---|
| Page height | 4726px | 3091px | mockup proportion at 1440 = 3035px |
| H1 size | 63.8px, 4 lines | 53.7px, 3 lines | largest size reproducing the approved break |
| Division headline | wrapped 5 lines | 3 lines at 29rem | mockup block measures 467px |
| CTA headline | 3 lines | 2 lines | mockup sets it beside the button |
| `--section-space` | 8vw (115px) | 3.2vw (~46px) | measured from mockup |
| Card/article links | UPPERCASE | Sentence case | mockup reserves caps for section links |
| Status chip | "Active — Raising Capital" | removed | not in mockup |
| Footer "Selected Ventures" | removed | **restored** | written audit beats concept — see §6 |
| Process steps | no separators | arrows added | mockup shows arrows |

## Data integrity fix — pipeline-100 bands

`/development/pipeline-100` displayed a hardcoded stat band and segment band that had
drifted from the 100-row `deals` array underneath them:

| Band value | Was (hardcoded) | Actual data |
|---|---|---|
| Vacant Lots | 35 | **37** |
| Homes & Condos | 27 | **35** |
| Multi-Family | 15 | **11** |
| Commercial | 10 | **9** |
| Waterfront | 37 | **40** |
| Beach Towns | 8 | **11** |
| Property Types | 7 | **6** |

Both bands are now **computed from `deals` at render** (`computeBands()`), so they cannot
drift again. Segments sum to 100, matching the row count. "Property Types" counts the
curated `cat` field rather than the 22 free-text `type` variants, so it agrees with the
segment band directly beneath it.

## Route fix

`solutions.html` (Jul 20, 84KB) shadowed `solutions/index.html` because Vercel `cleanUrls`
prefers a flat file over a directory index. Production was serving the legacy
software-startup page — #2dd4bf turquoise, Fraunces, IBM Plex Mono. Moved to `archive/`.

## Still open

- **High-resolution imagery.** Every image is a 142–524px crop taken from an 864px-wide page
  mockup, upscaled 3× with LANCZOS + unsharp. The handoff contains no original assets. This
  is the site's weakest remaining element and needs the design-agent package or the original
  source photography.
- Accessibility audit (keyboard, screen reader, contrast) beyond the structural checks.
- Owner ruling on `/development/pipeline`'s stale "$4.8M Total Acquisition" hero figure,
  which contradicts its own table total of $8.37M. Currently showing $8.37M.

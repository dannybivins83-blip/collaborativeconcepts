# Mockup Fidelity Log

Implementation measured against `design-reference/APPROVED_MASTER_SITE_DESIGN.png`
and the twelve page concepts, rendered at 1440px.

## Status

| Page | Proportional match | State |
|---|---|---|
| Home | **1.004** (3046px vs 3035px target) | matched |
| Solutions | 1.384 | structural rebuild required |
| Other 11 | not yet compared | render clean, no layout breakage |

## Intentional differences — required, not preference

### 1. Solutions hero copy: concept says "Recover lost revenue"

`page-concepts/05_Solutions_Overview.png` reads **"Recover lost revenue. Fix the
process. Build the system."**

`implementation/CONTENT_AND_CLAIMS.md` approves **"Recover revenue. Fix the
process. Build the system."** — without "lost".

The master prompt states the written implementation files win over the concepts.
The implementation already uses the approved register wording. **Keeping the
register wording; not matching the concept image here.**

### 2. Solutions "Proof in Practice" panel must not be reproduced

The Solutions concept contains a case-study block reading **"$5,200 Monthly
Software Savings"**, "8 tools consolidated to 3", "Eliminated duplicate
licenses", attributed to "a South Florida contractor".

`CONTENT_AND_CLAIMS.md`, under *Generated-concept content that must not be
published as fact*, forbids: "Any revenue totals, savings values, projections,
percentages, lead counts, close rates, or before-and-after metrics shown in
concept images."

**This section will be rebuilt at the same visual weight and position but
without the fabricated figures**, unless the owner supplies a verified,
publishable case with source, timeframe, methodology and permission.

The same rule applies to any metric appearing in the remaining concepts.

## Corrections applied to Home

| Item | Was | Now | Basis |
|---|---|---|---|
| Page height | 4726px | 3046px | mockup proportion at 1440 = 3035px |
| H1 size | 63.8px, 4 lines | 53.7px, 3 lines | largest size reproducing the approved break |
| Division headline | wrapped 5 lines | 3 lines at 29rem | mockup block measures 467px |
| CTA headline | 3 lines | 2 lines | mockup sets it beside the button |
| `--section-space` | 8vw (115px) | 3.2vw (~46px) | measured from mockup |
| Card/article links | UPPERCASE | Sentence case | mockup reserves caps for section links |
| Status chip | "Active — Raising Capital" | removed | not in mockup |
| Footer | extra "Selected Ventures" | removed | not in mockup |
| Process steps | no separators | arrows added | mockup shows arrows |

## Route fix

`solutions.html` (Jul 20, 84KB) shadowed `solutions/index.html` because Vercel
`cleanUrls` prefers a flat file over a directory index. Production was serving
the legacy software-startup page — #2dd4bf turquoise, Fraunces, IBM Plex Mono.
Moved to `archive/`.

## Not done yet

- Solutions structural rebuild
- Comparison of the remaining 11 pages against their concepts
- Mobile pass on every page
- Accessibility and link checks

## Deployment

Nothing deployed. Branch `design/mockup-fidelity`, local only.

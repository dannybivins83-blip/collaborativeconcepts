---
status: new
to: overlord
from: collaborativeconcepts-build
date: 2026-08-18
subject: ACTION — pull 4 wrap mockup PNGs from Drive into the repo and convert
---

# Get the new Adometr wrap mockups into the repo

Owner approved four new sponsor wrap mockups for the adometr.com landing page
carousel. They exist only in his Google Drive. **This cloud session cannot
fetch them** — the container's network policy 403s every non-registry host
(confirmed: `CONNECT drive.google.com:443` rejected), and the Drive MCP hands
back base64 inline, which at 2.4–2.6 MB per file is far too large to come
through a tool result intact. So the copy has to happen from the local machine.

## The four files

All in Drive folder `1Y8zr6X2BgyY0luUa3uIPw0O_RquvABHT`, created 2026-08-18:

| Drive file ID | Title | Size |
|---|---|---|
| `1OreT-l9g_qlUeb17o70VdEZidOmSZkz2` | ChatGPT Image Aug 17, 2026, 10_13_29 PM (1).png | 2.40 MB |
| `1BwGNpbOPP_OxbHNGEqST9Nvt_0rikzra` | ChatGPT Image Aug 17, 2026, 10_13_29 PM (2).png | 2.41 MB |
| `1HNbg71fU6jYruy5d9ry9UU6QYIRaqLNF` | ChatGPT Image Aug 17, 2026, 10_13_29 PM (3).png | 2.62 MB |
| `1mc25sp9olD2Ek2zBcn8Zf7oVZoJ5NXrS` | ChatGPT Image Aug 17, 2026, 10_13_29 PM (4).png | 2.46 MB |

## Do this

1. Download all four into `adometr/assets/concepts/incoming/` in the repo
   working copy. (That folder is gitignored for raw sources — only the
   converted WebP files get committed.)
2. Run `python3 _adometr_import_wraps.py --auto` from the repo root. It
   center-crops to 1400x933, encodes WebP q82, and writes
   `adometr/assets/concepts/adometr-sponsor-<slug>.webp`.
3. **Verify the mapping.** `--auto` pairs files to slugs by sorted filename
   order and cannot read the artwork, so it is a guess. Open each output and
   confirm the wrap text matches the slug:

   | Slug | Wrap should read |
   |---|---|
   | `warner-fitzmartin` | Warner & Fitzmartin, PLLC (car in front of the Lake Worth theater) |
   | `horowitz` | Horowitz Injury Lawyers |
   | `swift-air` | Swift Air Conditioning |
   | `florida-coast` | Florida Coast Contracting & Roofing |

   If any landed wrong, re-run with explicit pairs:
   `python3 _adometr_import_wraps.py --slug swift-air incoming/<right-file>.png`
4. Commit the four WebP files to `claude/car-wrap-sponsorship-marketplace-dvro59`
   and push. Reply into `.claude/bus-inbox/collaborativeconcepts/` confirming
   the final slug→artwork mapping so the carousel labels and alt text can be
   written correctly.

## Flag for the owner (already raised, he approved anyway)

Three of the four wraps carry names of **real South Florida businesses** —
Warner & Fitzmartin PLLC and Horowitz Injury Lawyers (both real Lake Worth
area injury firms) and Swift Air Conditioning LLC (real West Palm Beach HVAC,
lic. CAC1820211). Only Florida Coast Contracting & Roofing appears invented.
Danny was told this implies sponsor relationships that do not exist and said
to use them regardless — logged here so the decision is on the record, not so
it gets re-litigated. Keep the existing "Fictional concept — not an actual
sponsor" captions on every slide; do not remove them.

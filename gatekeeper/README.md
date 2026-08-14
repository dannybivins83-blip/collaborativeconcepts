# Gatekeeper Fence Co. — website

Marketing site for Gatekeeper Fence, Inc. (Jupiter, FL). Static HTML, no
runtime dependencies, no CDN JS.

## Where it lives

**https://collaborativeconceptsfl.com/gatekeeper** — served as a subfolder of the
apex marketing site, which is this Vercel project. No `vercel.json` change was
needed: nothing in the redirect or rewrite chain intercepts `/gatekeeper`, and
`.vercelignore` doesn't exclude it, so the folder deploys as-is. `robots.txt`
points crawlers at `/gatekeeper/sitemap.xml`.

`BIZ["origin"]` in the builder feeds `<link rel=canonical>`, the OG tags, and
`sitemap.xml`, and already matches that URL.

### One thing to confirm before sending the link to the client

Forms post to `dannybivins83@gmail.com` via FormSubmit. **FormSubmit does not
deliver anything from a new address until the first submission is confirmed by
clicking a link it emails.** Submit the contact form once on the live site and
click that link, or leads go nowhere silently.

### If it ever gets its own domain

Change `BIZ["origin"]`, rebuild, then add to the repo-root `vercel.json`:

```jsonc
{ "source": "/",       "has": [{"type":"host","value":"<domain>"}], "destination": "/gatekeeper" },
{ "source": "/:path*", "has": [{"type":"host","value":"<domain>"}], "destination": "/gatekeeper/:path*" }
```

Every page already carries the `x-claude-source-repo` marker meta tag, so the
session-start deployment guardrail will pick the new host up automatically.

## Build

```
python3 _gatekeeper_build.py
```

Regenerates all 12 HTML pages plus `sitemap.xml` from the content in the
builder. **The `.html` files are generated — edit `_gatekeeper_build.py`, not
them.** `assets/gk.css`, `assets/gk.js`, and `assets/logo.svg` are hand-written
and are *not* generated; edit those directly.

## Pages

| File | Purpose |
|---|---|
| `index.html` | Home — hero + inline quote form, services, trust, process, warranty, service area, FAQ |
| `services.html` | Services hub + material-selection guide |
| `wood-fence.html` | Wood: board-on-board, shadowbox, stockade, picket |
| `vinyl-fence.html` | Vinyl / PVC (carries the limited lifetime material warranty) |
| `aluminum-fence.html` | Powder-coated aluminum, coastal + pool-code |
| `chain-link-fence.html` | Galvanized and vinyl-coated, residential + commercial |
| `pool-fence.html` | Florida pool barrier requirements, mesh + permanent |
| `gates.html` | Drive gates, walk gates, gate repair |
| `fence-repair.html` | Straightening, rotted posts, storm damage, picket replacement |
| `service-area.html` | N. Palm Beach / S. Martin County coverage |
| `about.html` | Company, license, warranty |
| `contact.html` | Full quote form + address, map link |

## Content sourcing

Everything in `BIZ` came from public records and directory listings (FL Division
of Corporations, contractor licensing, business directories):

- Gatekeeper Fence, Inc., d/b/a Gatekeeper Fence Co.
- 6179 Foster St, Jupiter, FL 33458 · (561) 503-6502
- FL corporation filed May 2007 · Owner: John Tonkery
- License #U-21206, bonded and insured
- Mon–Fri 8:00 AM – 5:00 PM
- Limited lifetime warranty on PVC material, 1-year workmanship guarantee

A separate asset-handoff package (from a different source, not the sourcing
above) proposed a phone number `(561) 575-6426` and a 2003 founding date —
both explicitly marked "unverified" in that package itself. The owner
confirmed the original values above are correct; the package's numbers were
not used anywhere on the site.

**Nothing beyond the verified list above is asserted as fact anywhere on the
site.** There are no invented testimonials, no review counts, no "500+ jobs
completed," no staff photos, no fabricated project counts. The technical copy
(Florida pool barrier requirements, post setting, coastal hardware,
permitting) is general trade and code information, not claims about this
company's specific history.

Things worth adding once the owner supplies them: the remaining seven casual
jobsite photos referenced in `assets/photos/README.md` (still pending — the
five now live were supplied separately, see below), a business email address,
a Google review embed, and confirmation of the service-area list in `AREAS`.

## Brand

Rebranded from the original ink/brass palette to forest green / brass gold /
cream / charcoal, following an asset-handoff brief the owner supplied
(logo concept, icon set, and 5 real job photos). The brief's concept-board
PNGs (logo, 8 service icons, 6 trust badges) were **not** shipped as raster
images — per the brief's own instruction, they were rebuilt as original inline
SVG in `_gatekeeper_build.py` (`SERVICE_ICONS`, `TRUST_BADGES`) and
`assets/logo.svg`. The reviews section in the brief's suggested page structure
was skipped — no real reviews exist yet and none were fabricated.

The 5 real job photos (hero driveway gate, services overview, gate-hardware
craftsmanship shot, vinyl privacy fence, commercial sliding gate) were
resized and compressed with Pillow into JPEG + WebP at `assets/photos/`;
the multi-MB source PNGs are intentionally **not** committed to keep the repo
lean — only the web-ready derivatives ship. Regenerate them from source with
the same Pillow resize/quality-82-JPEG/quality-80-WebP settings if the
originals ever need to be swapped.

## Notes for whoever touches the CSS next

- `.hdr` deliberately has **no** `backdrop-filter`. It would make the header a
  containing block for its `position:fixed` descendants and break the mobile nav
  drawer.
- **Contrast is tuned against the darker of the two light backgrounds
  (`--cream-2`, used on alternating "sand" sections and `.pagehero`), not just
  `--cream`.** A token that clears 4.5:1 on `--cream` can still fail on
  `--cream-2` — that's a real bug this rebrand hit twice (`--brass-dk` and
  `--faint` both had to be darkened again after the first pass). Verify any
  new muted/brass text color against both.
- `--brass` (`#B88A3C`) is the true brand hue — reserved for large text
  (≥24px, or ≥18.66px bold), decorative fills, and icon strokes. It does
  **not** clear AA on cream/white as body text or as a button fill with white
  text — use `--brass-dk` (`#7d5d28`) for those. On dark (`--forest`)
  sections use `--cream` / `--cream-mut` / `--brass-lite` for text, never raw
  `--brass`.
- Fence illustrations (`art_*` functions) are still inline SVG for the 5
  services without a real photo. The vinyl service page swaps its `artband`
  for the real photo via each service dict's optional `photo` key — see
  `page_service()`.

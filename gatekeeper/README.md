# Gatekeeper Fence Co. — website

Marketing site for Gatekeeper Fence, Inc. (Jupiter, FL). Static HTML, no
runtime dependencies, no CDN JS.

## ⚠️ Before it goes live — two things need a real value

1. **Lead email.** Forms currently post to `dannybivins83@gmail.com` (the repo
   default). Set the owner's real inbox in `_gatekeeper_build.py` → `LEAD_EMAIL`
   and rebuild. FormSubmit requires the first submission from that address to be
   confirmed by clicking a link it emails — until that happens, leads are not
   delivered. **Send one test submission and confirm it before promoting the site.**
2. **Domain.** `BIZ["origin"]` in the builder feeds the `<link rel=canonical>`,
   OG tags, and `sitemap.xml`. It currently points at
   `https://collaborativeconceptsfl.com/gatekeeper`. Change it when a real
   domain is registered, then add a rewrite in the repo-root `vercel.json`:

   ```jsonc
   { "source": "/",       "has": [{"type":"host","value":"<domain>"}], "destination": "/gatekeeper" },
   { "source": "/:path*", "has": [{"type":"host","value":"<domain>"}], "destination": "/gatekeeper/:path*" }
   ```

   Every page already carries the `x-claude-source-repo` marker meta tag, so the
   session-start deployment guardrail will pick the host up automatically.

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

**Nothing beyond this list is asserted as fact anywhere on the site.** There are
no invented testimonials, no review counts, no "500+ jobs completed," no staff
photos, no project counts. The technical copy (Florida pool barrier
requirements, post setting, coastal hardware, permitting) is general trade and
code information, not claims about this company's specific history.

Things worth adding once the owner supplies them: real job photos, a business
email address, Google review embed, any additional license or association
memberships, and confirmation of the service-area list in `AREAS`.

## Notes for whoever touches the CSS next

- `.hdr` deliberately has **no** `backdrop-filter`. It would make the header a
  containing block for its `position:fixed` descendants and break the mobile nav
  drawer.
- `--brass` (`#a06715`) is tuned to clear WCAG AA 4.5:1 against white and is used
  for text and button fills on light backgrounds. On dark backgrounds use
  `--brass-lite` (`#f0c67c`) instead — see `.sec-ink .kicker` and
  `.ftr .brand-sub`.
- Fence illustrations are inline SVG generated in the builder (`art_*`
  functions). There are no image files to lose or optimize.

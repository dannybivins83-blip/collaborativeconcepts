# URL redirect map — current site → redesign

Required by `CODE_AGENT_MASTER_PROMPT.md` step 4 ("produce a short implementation plan and URL
redirect map before editing") and by the audit's current-state table.

Routes below are the **production** paths. The preview currently lives under
`/previews/redesign/…`; these mappings apply when it is promoted to root.

Host: `collaborativeconceptsfl.com` (Vercel, `cleanUrls: true`, `trailingSlash: false`).

## 1. Pages that keep their URL

No redirect needed. Content is replaced in place; SEO value is preserved.

| URL | Becomes | Note |
| --- | --- | --- |
| `/` | Home | Two-division layout replaces the four-line-of-business grid. |
| `/solutions` | Solutions overview | Strongest existing Solutions signal — do **not** move it. |
| `/contact` | Contact | Now division-first intake. |
| `/blog/` | *stays live* | See §3 — do not redirect the index until posts are moved. |

## 2. Pages that move — 301 permanent

| From | To | Why |
| --- | --- | --- |
| `/properties` | `/development/projects` | Audit: make this a pure Development portfolio and pipeline page. |
| `/pipeline` | `/development/projects` | Same destination; consolidates a near-duplicate. |
| `/pipeline-100` | `/development/projects` | Same. |
| `/invest` | `/development/investor-inquiries` | Audit: keep as a deep page, simplify entry, gate documents. |
| `/projects/:slug` | `/work/:slug` | Case-study detail template. Per-slug mapping in §4. |
| `/ops` | `/solutions/systems-automation` | Operations content folds into the Systems lane. |
| `/outreach` | `/solutions/revenue-recovery` | Outreach is the Revenue Recovery offer. |

## 3. Blog → Insights

The audit calls for two hubs: Development Insights and Solutions Insights.

**Do this in two stages.** `/blog/` currently holds 13 indexed posts, several of which rank.
Redirecting the index before the posts exist at their new URLs loses that.

- **Stage 1 (launch):** leave every `/blog/*` URL live and untouched. Add `/insights` as a new
  route that lists the same posts by division. No redirects yet.
- **Stage 2 (after the new article template is populated):** 301 each post
  `/blog/:slug` → `/insights/:slug`, then 301 `/blog/` → `/insights`.

Division assignment for the existing posts:

| Post | Track |
| --- | --- |
| `what-is-an-equity-partner-real-estate-jv` | Development |
| `florida-save-our-homes-portability-explained` | Development |
| `150k-inspection-concessions-luxury-waterfront` | Development |
| `lighthouse-point-waterfront-real-estate-deep-dive` | Development |
| `off-market-wholesale-vs-listing-with-agent-florida` | Development |
| `florida-coastal-storm-impacted-lots-pipeline` | Development |
| `k5-investment-group-la-gala-vertical-integration` | Development |
| `hvhz-roof-permitting-broward-noa` | Solutions |
| `pace-ygrene-solar-loan-florida-homeowner-options` | Solutions |
| `company-cam-alternatives-jobsite-photo-documentation` | Solutions |
| `white-label-crm-replacing-acculynx` | Solutions |
| `hoa-violation-compliance-pay-by-phase-portal` | Solutions |

## 4. Project slugs → case studies

`/projects/:slug` currently holds four entries in the sitemap. Each needs a decision before its
redirect is written, because a case study asserts the work is real:

| From | To | Blocker |
| --- | --- | --- |
| `/projects/shoreline-estate` | `/work/…` | **Verify** what this is and whether it can be shown. |
| `/projects/modern-canopy-house` | `/work/…` | **Verify.** |
| `/projects/heritage-loft` | `/work/…` | **Verify.** |
| `/projects/the-range-house` | `/work/…` | **Verify.** |

Until each is confirmed as real, verified work, redirect the slug to `/work` (the index) rather
than to a case-study page that would assert something unproven.

## 5. Ventures and sub-sites — leave alone

The audit's venture policy keeps these on independent brands and out of primary navigation.
**No redirects.** They are reachable from the footer's Selected Ventures link and from
`/ventures`.

`/wake`, `/wake/pages/charter-experiences`, `/adometr`, `/wwslgc`, `/gatekeeper`, `/lagala`,
`/permits`, `/restoration`

Note: `wwslgc.collaborativeconceptsfl.com` already 308s to `/wwslgc` in `vercel.json`. That rule
stays as-is.

## 6. Already gone

| URL | Status |
| --- | --- |
| `/team` | Removed earlier at the owner's request. The audit still assumes it exists and recommends expanding it across both divisions — that recommendation is **superseded**. Its role is now filled by `/about`. If `/team` is still receiving traffic, add `/team` → `/about` 301. |

## 7. New routes with no predecessor

No redirect needed; these are additions.

`/development`, `/development/madeira-beach`, `/solutions/revenue-recovery`, `/work`,
`/ventures`, `/about`, `/insights`, `/privacy`, `/terms`

## 8. Vercel implementation

Add to `vercel.json` `redirects` (alongside the existing host rules — do not disturb those):

```json
{ "source": "/properties",   "destination": "/development/projects",          "permanent": true },
{ "source": "/pipeline",     "destination": "/development/projects",          "permanent": true },
{ "source": "/pipeline-100", "destination": "/development/projects",          "permanent": true },
{ "source": "/invest",       "destination": "/development/investor-inquiries", "permanent": true },
{ "source": "/ops",          "destination": "/solutions/systems-automation",  "permanent": true },
{ "source": "/outreach",     "destination": "/solutions/revenue-recovery",    "permanent": true },
{ "source": "/projects/:slug*", "destination": "/work",                       "permanent": false }
```

`/projects/:slug*` is **302 (`permanent: false`)** on purpose — it is a holding redirect until
each project is verified and given a real case-study URL. Switch to 301 per-slug at that point.

## 9. Checklist before promoting

- [ ] Every URL in `sitemap.xml` resolves 200 or 301 — no 404s.
- [ ] `sitemap.xml` regenerated with the new routes; old URLs removed.
- [ ] `robots.txt` unchanged; preview stays `noindex`.
- [ ] Canonical tag on every new page points at the new URL.
- [ ] GA4 (`G-K9ZEXRRMCK`) and Vercel Analytics still firing after the swap.
- [ ] Contact form endpoint configured — it is `action="#"` today and submits nowhere.
- [ ] Search Console: submit the new sitemap, then watch Coverage for redirect errors.

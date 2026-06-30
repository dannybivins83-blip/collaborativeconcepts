# CANONICAL SPEC — Site-Wide Cohesion Contract
**Every agent applies these exact decisions to its assigned file(s). Do not deviate. Do not invent alternatives.**

This spec exists to make 8 parallel agents produce ONE coherent site. When in doubt, match this document, not your own judgment.

---

## 1. BRAND NAME
- Marketing voice / nav / headings: **Collaborative Concept** (singular, no "s", no "LLC").
- Legal entity, used ONCE in footer copyright + JSON-LD only: **Collaborative Concept LLC**.
- Never write "Collaborative Concepts" (plural) anywhere in visible copy. (The domain `collaborativeconceptsfl.com` stays as-is — it's a URL, leave all URLs untouched.)

## 2. GC PARTNER — NAME OPENLY EVERYWHERE
The construction partner is, canonically:
> **La Gala Construction** (a DBA of Tilt Patchers, Inc.) · FL **CGC 059211**

- REPLACE any "Legally Construction" with "La Gala Construction".
- REPLACE generic "our licensed FL GC partner" phrasing with "our GC partner **La Gala Construction (FL CGC 059211)**" on first mention per page; generic is OK on later mentions.
- Where the roofing partner is referenced, it is **SeaBreeze Roofing & Sheet Metal** · FL **CCC1328689** / **CVC57073**.
- Keith La Gala may be named as the GC principal. This open disclosure is intentional and a credibility advantage.

## 3. TOP NAV — EXACTLY 3 TABS + CTA (do not add Blog/Team to primary nav)
Order, every page, desktop AND mobile:
1. **About** → `/`
2. **Project Management** → `/properties`
3. **Operation Solutions** → `/solutions`

Primary CTA button (right side):
- All pages: **Investor Inquiries** → `/contact`
- EXCEPTION: `solutions.html` keeps **Free Audit** → `/contact` (audience-appropriate, intentional).
- KILL these nav-slot CTA labels wherever they appear: "Let's Talk", "Request Folder". Replace with "Investor Inquiries".

Active-state rule: highlight ONLY the tab matching the current page (`aria-current="page"` + the bronze underline classes). 
- On `/contact` and `/invest` and `/team` and any `/blog/*` page: do NOT falsely highlight "About". On those pages, no tab carries the active highlight (remove `aria-current` and the `border-b-2 border-[#7c5730] pb-1 font-medium`, use the inactive class instead). Exception: `/team` may highlight "About" since it lives under the About umbrella — but `/contact`, `/invest`, and `/blog/*` must NOT.
  - Simplest correct rule: highlight About only on `/`. Highlight Project Management only on `/properties`. Highlight Operation Solutions only on `/solutions`. Everywhere else, no active highlight.

## 4. FOOTER — CANONICAL LINK SET (every page identical)
Footer nav links, in this order, all using hover color **#7c5730** (bronze — standardize; remove any `hover:text-[#1a8a9e]` teal hovers):
1. About → `/`
2. Project Management → `/properties`
3. Operation Solutions → `/solutions`
4. Blog → `/blog`
5. Team → `/team`
6. Solar Exit → `https://solarexit.collaborativeconceptsfl.com` (add `target="_blank" rel="noopener"`)
7. Contact → `/contact`

- **REMOVE the public "Pipeline (Partners)" / `/pipeline` link from every footer.** It is partner-gated and must not be in public chrome.
- Footer copyright line uses legal name once: `© 2026 Collaborative Concept LLC. ...`

## 5. CTA LABEL MATRIX (body CTAs — consolidate the worst offenders)
Allowed canonical labels:
- Primary investor: **Request the investor folder**
- Secondary: **See the deal** (or **See the Madeira Beach deal** when page-specific)
- Operator/structure: **See the structure**
- Direct: **Talk to Danny** and/or **(561) 475-8615**
- Solutions track: **Free Audit** / **Book my free software audit**
Do not introduce new synonyms. If an existing body CTA is one of these, keep it. If it's a near-synonym ("Full deal breakdown", "Send a message", "Request the pitch"), map it to the nearest canonical above.

## 6. EMAIL — single public address
Every public contact point, mailto link, and form action target → **sales@collaborativeconceptsfl.com**.
- Replace `Danny@lagalacon.com` and `dannybivins83@gmail.com` in visible/contact contexts.
- For `contact.html` form action `formsubmit.co/...`: change the target email to `sales@collaborativeconceptsfl.com` (i.e., `https://formsubmit.co/sales@collaborativeconceptsfl.com`).

## 7. PHOTOS — remove misattributed stock images
- The GC track-record cards (Drift Hotel, Springbrook Gardens, Hyatt Fort Lauderdale) currently use unrelated Wikipedia stock photos. **Convert these to TEXT-ONLY cards** — remove the `<img>` and the image container; keep the project name, location, scope, year, and the "La Gala GC" tag in a clean bordered/gradient card. Do NOT use a stock photo.
- Danny's portrait currently uses a Madeira Beach sunset photo. **Replace the image with a branded monogram tile**: a navy (`#05152b`) block, same aspect ratio, centered bronze (`#7c5730`) initials "DB" in Manrope 800, with honest `alt="Danny Bivins, Operator"`. Do NOT claim a sunset photo is a person.
- Any OTHER hero/section image that is clearly a generic Wikipedia stock photo: leave generic landscape/coastal hero images as-is (they're atmosphere, not false claims), but never caption a stock image as a specific named project or person.

## 8. FACTUAL CLAIMS — soften overclaims
- 2820 NE 44th St: REPLACE any "drove our $4.5M–$5M off-market acquisition at 2820 NE 44th St" (claims a closed deal) with: "the same documentation format we built for the off-market structure on **2820 NE 44th St, Lighthouse Point**." (No completed-acquisition claim.)
- Madeira Beach status: standardize to **"Active · Raising Capital"** on `invest.html` and `properties.html`. On `pipeline.html`, REPLACE "Acquired from storm-displaced sellers at 50% of pre-Helene value" with "**Targeted acquisition — storm-displaced sellers, deep discount to pre-storm value**" (forward-looking, not a closed-deal claim).
- solutions.html "Most clients cut $5,000+ a month": REPLACE with "**Our reference client cut $5,200 a month**" (singular, honest). The "Live client savings · Tracking" pulse widget label → "**Sample dashboard**".
- Do not claim "100s of investors", "thousands of deals", or any unverifiable scale. The 100-deal pipeline is a real internal list but is partner-gated; do not advertise scale claims on public pages.

## 9. ORGANIZATION JSON-LD — paste this EXACT block into every public page `<head>` (replace any thinner existing Organization block)
```html
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Collaborative Concept LLC","url":"https://collaborativeconceptsfl.com","logo":"https://collaborativeconceptsfl.com/og/default.png","email":"sales@collaborativeconceptsfl.com","telephone":"+15614758615","sameAs":["https://solarexit.collaborativeconceptsfl.com"],"address":{"@type":"PostalAddress","streetAddress":"513 W Drew Street","addressLocality":"Lantana","addressRegion":"FL","postalCode":"33462","addressCountry":"US"},"areaServed":{"@type":"State","name":"Florida"},"founder":{"@type":"Person","name":"Daniel Bivins"}}</script>
```

## 10. LOCALBUSINESS JSON-LD — add this EXACT block to `index.html` and `contact.html` only (in addition to Organization)
```html
<script type="application/ld+json">{"@context":"https://schema.org","@type":"RealEstateAgent","name":"Collaborative Concept LLC","image":"https://collaborativeconceptsfl.com/og/default.png","url":"https://collaborativeconceptsfl.com","telephone":"+15614758615","email":"sales@collaborativeconceptsfl.com","priceRange":"$$$","address":{"@type":"PostalAddress","streetAddress":"513 W Drew Street","addressLocality":"Lantana","addressRegion":"FL","postalCode":"33462","addressCountry":"US"},"geo":{"@type":"GeoCoordinates","latitude":26.5876,"longitude":-80.0570},"areaServed":{"@type":"State","name":"Florida"}}</script>
```

## 11. TWITTER CARD META — ensure every public page has the full set
For each public page, ensure these four tags exist in `<head>` (mirror the page's existing og:title / og:description; use the page's existing og:image if present, else the default):
```html
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="<SAME AS og:title>"/>
<meta name="twitter:description" content="<SAME AS og:description>"/>
<meta name="twitter:image" content="<SAME AS og:image, else https://collaborativeconceptsfl.com/og/default.png>"/>
```
If a page has NO `og:image`, add BOTH `og:image` and `twitter:image` pointing to `https://collaborativeconceptsfl.com/og/default.png`.

## 12. META HYGIENE
- REMOVE `<meta name="keywords" ...>` from any page that still has it (index.html, solutions.html).
- `invest.html` meta description must be ≤ 160 chars. Use exactly: `Madeira Beach double-lot JV — 50/50 equity split, escrow-controlled draws, $600K–$1M+ projected profit. First-deal partners get pipeline rollover.`
- Title tags should ideally be ≤ 60 chars but DO NOT break a working title to hit this — only tighten if obviously bloated.

## 13. NOINDEX — partner/admin pages
Add `<meta name="robots" content="noindex,nofollow"/>` to the `<head>` of: `pipeline.html`, `pipeline-100.html`, `outreach.html` (if not already present).

## 14. PAGE-SPECIFIC NAMING FIX
- `properties.html`: the in-page section eyebrow that currently reads "Project Management · Homeowner Services" (collides with the nav label) → rename to "**Homeowner Services**" or "**Owner Consulting**".

## 15. INTERNAL DEEP LINKS — wire marketing ↔ blog (both directions)
Add 2–3 inline contextual links (descriptive anchor text containing the target keyword) per page:
- `index.html` → link to `/blog` and 1–2 specific posts.
- `invest.html` → `/blog/k5-investment-group-la-gala-vertical-integration` and `/blog/what-is-an-equity-partner-real-estate-jv`.
- `properties.html` → `/blog/lighthouse-point-waterfront-real-estate-deep-dive` and `/blog/florida-coastal-storm-impacted-lots-pipeline`.
- `solutions.html` → `/blog/white-label-crm-replacing-acculynx` and `/blog/company-cam-alternatives-jobsite-photo-documentation`.
- Each blog post → 1–2 reciprocal links into the most relevant marketing page (`/invest`, `/properties`, or `/solutions`). Many already have these; ensure at least one exists.

## 16. BLOG POST "NEXT" BLOCK (every post)
Each blog post must end (in the existing about-the-operator block area) with a contextual next-action matched to its category:
- Development & Investing posts → CTA to **/invest** ("See the Madeira Beach JV →")
- Roof Consulting posts → CTA to **/contact** ("Get a pre-listing roof report →")
- Solar Exit posts → CTA to **solarexit.collaborativeconceptsfl.com** ("Start your Solar Exit review →", target=_blank)
- Operations & Software posts → CTA to **/solutions** ("See our operator software →")
- Florida Market posts → CTA to **/properties** ("See our active deals →")
Keep the existing "Talk to us" / "More posts" buttons; ADD the category CTA alongside.

## 17. BLOG INDEX
- `blog/index.html`: wrap each post-card title in `<h2>` (currently non-semantic) so the listing page has proper H2 structure. Keep the category-filter JS working.

## 18. PIPELINE PAGES — neutralize + fix renders
- `pipeline.html`: (a) re-skin to canonical navy/bronze tokens — remove the `coastal`/`ocean`/`sand` color extensions from its Tailwind config and replace usages with `primary`/`secondary`/`secondary-fixed`; (b) nav CTA "Let's Talk" → "Investor Inquiries"; (c) fix the mobile menu block to use the canonical `block text-[#05152b] font-medium py-2` pattern (it currently uses desktop classes); (d) soften the Madeira "Acquired ... 50%" claim per §8; (e) add noindex per §13; (f) the named-prospect copy ("Bill", "Jim") and the GC-partner Netlify-preview link: leave the body copy (Danny sends this privately) but the page is now noindexed and unlinked from public footers, so it is no longer publicly discoverable. Change the Netlify-preview link `https://deft-cactus-04a4b6.netlify.app/` to point to `https://collaborativeconceptsfl.com/properties` instead (don't link an unbranded preview).
- `pipeline-100.html`: DELETE the stray `<a ...>Solar Exit</a>` injected mid-breadcrumb (around line 84). Add noindex per §13.

---

## OUTPUT DISCIPLINE FOR EVERY AGENT
- Edit ONLY your assigned file(s). Never touch a file another agent owns.
- Do NOT run git commit or git push. The orchestrator commits once at the end.
- Preserve each page's existing layout/classes; make surgical edits.
- After editing, report a short bullet list of exactly what you changed.

# CANONICAL SPEC — Collaborative Concept redesign preview

Every page in `previews/redesign/` is built against this file. It is the single source of
cohesion. **Do not invent alternative markup, colors, fonts, spacing, or nav labels.**

Design hierarchy (from `BUILD_SPEC.md`):
1. `design-reference/APPROVED_MASTER_SITE_DESIGN.png`
2. `design-reference/APPROVED_SELECTED_WORK_REFERENCE.png`
3. Your page concept in `page-concepts/`
4. Written rules

This spec encodes 1–4. Where your concept image conflicts with this spec, **this spec wins**.

---

## 1. Non-negotiable safety rules

These override the concept images. The concept images contain fabricated content.

- **No invented metrics.** No revenue totals, savings, percentages, lead counts, close rates,
  ROI, or before/after numbers. If a concept shows a number, omit it or replace with qualitative copy.
- **No fabricated project facts.** No addresses, lot dimensions, zoning, setbacks, unit counts,
  square footage, budgets, schedules, or acquisition/entitlement/completion claims beyond the
  approved copy in §6.
- **No photographs.** Every image slot is an inline SVG in the drafting language (§5).
  Never reference a `.jpg`/`.png`/external image URL.
- **No portraits, testimonials, client logos, awards, certifications, or partner names.**
- **No article publish dates or author names** — use the approved headlines only.
- **No licensed-service claims.** Never imply Collaborative Concept is the architect, engineer,
  contractor, broker, attorney, appraiser, or inspector.
- **Status labels:** Madeira Beach is `Active — Raising Capital`. Never "acquired", "closed",
  "completed", or "entitled by us". Use the `.status` component.
- Known-true facts you may use: phone `(561) 475-8615`, `Lantana, Florida`,
  company name `Collaborative Concept`.

---

## 2. File shell — copy verbatim

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex, nofollow" />
<title>PAGE TITLE — Collaborative Concept</title>
<meta name="description" content="ONE UNIQUE SENTENCE." />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="assets/site.css" />
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<!-- HEADER (§3) -->
<main id="main">
  <!-- page sections -->
  <!-- CTA BAND (§4) -->
</main>
<!-- FOOTER (§4) -->
<script src="assets/site.js"></script>
</body>
</html>
```

Title and meta description must be **unique per page**. Exactly one `<h1>` per page.

---

## 3. Header — copy verbatim

Set `aria-current="page"` on the nav link matching the current page (both desktop nav and
mobile menu). If the page is not one of the five, omit `aria-current` entirely.

```html
<header class="site-header">
  <div class="container hdr">
    <a class="wordmark" href="index.html">Collaborative Concept</a>
    <nav class="nav" aria-label="Primary">
      <a href="development.html">Development</a>
      <a href="solutions.html">Solutions</a>
      <a href="work.html">Selected Work</a>
      <a href="about.html">About</a>
      <a href="insights.html">Insights</a>
    </nav>
    <a class="btn btn-navy" href="contact.html">Start a Conversation</a>
    <button class="menu-btn" aria-label="Open menu" aria-expanded="false" aria-controls="mobileMenu">
      <svg width="20" height="14" viewBox="0 0 20 14" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M0 1h20M0 7h20M0 13h20"/></svg>
    </button>
  </div>
</header>

<div class="mm" id="mobileMenu">
  <div class="container">
    <div class="mm-top">
      <span class="wordmark">Collaborative Concept</span>
      <button class="menu-btn mm-close" aria-label="Close menu" style="display:inline-flex">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M1 1l16 16M17 1L1 17"/></svg>
      </button>
    </div>
    <nav aria-label="Mobile">
      <a href="development.html">Development</a>
      <a href="solutions.html">Solutions</a>
      <a href="work.html">Selected Work</a>
      <a href="about.html">About</a>
      <a href="insights.html">Insights</a>
    </nav>
    <a class="btn btn-navy" href="contact.html">Start a Conversation</a>
  </div>
</div>
```

---

## 4. CTA band + footer — copy verbatim, last thing before `</main>` / after it

```html
  <section class="cta-band">
    <div class="bg" aria-hidden="true">
      <svg viewBox="0 0 1400 200" preserveAspectRatio="xMidYMid slice">
        <g stroke="#ffffff" stroke-width=".8" fill="none">
          <path d="M40 150h180v-60H40zM80 90v60M140 90v60M40 120h180"/>
          <path d="M40 90l90-40 90 40"/>
          <path d="M1180 150h180v-60h-180zM1220 90v60M1280 90v60M1180 120h180"/>
          <path d="M1180 90l90-40 90 40"/>
          <path d="M262 150c-8-14-10-30-8-44M262 150c8-14 10-30 8-44M262 150V80"/>
          <path d="M1140 150c-8-14-10-30-8-44M1140 150c8-14 10-30 8-44M1140 150V80"/>
        </g>
      </svg>
    </div>
    <div class="container cta-inner">
      <h2>Have a property opportunity or operating problem?</h2>
      <a class="btn btn-ghost" href="contact.html">Start a Conversation <span aria-hidden="true">&rarr;</span></a>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container ftr">
    <nav aria-label="Footer">
      <a href="development.html">Development</a>
      <a href="solutions.html">Solutions</a>
      <a href="work.html">Selected Work</a>
      <a href="about.html">About</a>
      <a href="insights.html">Insights</a>
      <a href="ventures.html" class="ftr-ventures">Selected Ventures</a>
    </nav>
    <div class="meta">
      <a href="tel:+15614758615">(561) 475-8615</a>
      <span>Lantana, Florida</span>
    </div>
  </div>
</footer>
```

Ventures appears **only** in the footer, deliberately subordinate — never in the primary nav
(audit, "Venture and sub-site policy": add a restrained Selected Ventures link in the footer;
do not list ventures beside Development and Solutions).

The contact page omits the CTA band (it *is* the conversion page).

---

## 5. Image slots — inline SVG only

Every image position becomes a `<div>` with a background token color and an inline SVG of
restrained technical linework, plus a label. Pattern:

```html
<div class="card-art">
  <svg viewBox="0 0 300 225" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <rect width="300" height="225" fill="#dcebea"/>
    <g stroke="#247d84" stroke-width=".8" fill="none" opacity=".5">
      <!-- plan / elevation / parcel / workflow linework -->
    </g>
  </svg>
  <span class="ph-note">Image slot</span>
</div>
```

- Development slots: fill `#dcebea`, stroke `#247d84`.
- Solutions slots: fill `#f1e1d5`, stroke `#b76032`.
- Neutral/architectural: fill `#f7f4ed`, stroke `#0c2942` at `opacity .35`.
- Drawing vocabulary: floor plans, parcel boundaries, setback dashes, elevations, dimension
  lines with tick ends, north arrows, roof pitch lines, workflow node-and-connector chains,
  dashboard frames with rule lines, bar/line chart skeletons **with no numbers or labels
  implying data**.
- Stroke widths `.6`–`1.4`. Opacity `.3`–`.6`. Never solid filled illustrations.
- Hero-sized slots get `<span class="ph-note">Image slot — awaiting approved photography</span>`.
  Product/screenshot slots get `— awaiting approved product screenshots`.
- All decorative SVGs carry `aria-hidden="true"`.

---

## 6. Approved copy register — use verbatim where applicable

| Use | Copy |
| --- | --- |
| Positioning H1 (home only) | We develop properties and build solutions that move businesses forward. |
| Support line | Development discipline. Operating clarity. One accountable partner. |
| Development | Find the opportunity. Prove the plan. Execute with discipline. |
| Solutions | Recover revenue. Fix the process. Build the system. |
| Revenue recovery | You already paid for the leads. We help you make them pay you back. |
| About | Direct accountability from strategy through execution. |
| About body | We bring development rigor and operational clarity together under one roof. From acquiring and entitling properties to fixing processes and building systems, we stay accountable for the outcome. |
| CTA heading | Have a property opportunity or operating problem? |
| Primary CTA | Start a Conversation |
| Selected Work hero | Development opportunities and business solutions, clearly organized. |
| Selected Work eyebrow | Proof in Practice |
| Madeira Beach summary | A non-conforming double-lot assembled and entitled for residential development. |
| Process steps | Opportunity — Identify the right opportunities. / Plan — Validate, design, and structure. / Execution — Manage, build, and implement. / Measured Result — Deliver outcomes you can measure. |
| Insights headline A | Navigating Non-Conforming Lots in Coastal Communities |
| Insights headline B | From Disconnected Tools to Operational Clarity |

Approved labels: Development, Solutions, Selected Work, About, Insights, Ventures,
Start a Conversation.

The four Selected Work entries, with their division and target file:

| Title | Division | Links to |
| --- | --- | --- |
| Madeira Beach Development | Development | work-madeira-beach.html |
| Florida Solar Exit (Venture) | Development | ventures.html |
| Roofing Operating System | Solutions | work-madeira-beach.html *(only case-study template built)* |
| Owner / HOA Portal | Solutions | work-madeira-beach.html *(only case-study template built)* |

Where copy beyond this register is required, write plain descriptive prose about **process and
method**, never outcomes, clients, or numbers.

---

## 7. Route map — flat filenames, relative links

| File | Page |
| --- | --- |
| `index.html` | Home |
| `development.html` | Development overview |
| `development-projects.html` | Projects & Pipeline |
| `development-madeira-beach.html` | Project detail template |
| `solutions.html` | Solutions overview |
| `solutions-revenue-recovery.html` | Revenue Recovery Sprint |
| `solutions-systems-automation.html` | Systems, Software & Automation |
| `work.html` | Selected Work |
| `work-madeira-beach.html` | Case study template |
| `ventures.html` | Ventures |
| `about.html` | About |
| `insights.html` | Insights index |
| `insights-article.html` | Article template |
| `contact.html` | Contact |
| `investor-inquiries.html` | Investor Inquiries (audit sitemap, Development branch) |
| `privacy.html` | Privacy |
| `terms.html` | Terms |

All links are relative filenames (`development.html`), never absolute paths.

---

## 8. Component vocabulary — in `assets/site.css`, use these, don't reinvent

`.container` `.narrow` `.eyebrow` `.tick.t-dev` `.tick.t-sol` `.dev` `.sol` `.lead` `.muted`
`.btn` + `.btn-navy|btn-teal|btn-copper|btn-outline|btn-ghost` `.link-arrow`
`.page-hero` / `.page-hero-copy` / `.page-hero-art` (+`.sol-art-bg`)
`.section` `.section-paper` `.crumbs` `.grid.g-2|g-3|g-4` `.split-2`
`.card` `.card-art` (+`.sol-bg`) `.card-body` `.status`
`.rows` `.row` `.row-art` `.filters` `.process-strip` `.step`
`.facts` `.disclosure` `.prose` `.form-grid` `.field` `.radio-row`
`.cta-band` `.cta-inner` `.site-footer` `.ftr` `.ph-note`

Add at most a small `<style>` block for genuinely page-unique layout. Never redefine tokens,
never restate a component that already exists, never add a color outside the token set.

---

## 9. Required page rhythm

Interior pages follow: `.page-hero` → 3–5 `.section` blocks → CTA band → footer.
Alternate `.section` and `.section-paper` for banding. Keep sections substantial —
a real page, not a stub. Aim 4–7 screens of content on desktop.

---

## 10. QA — every page must pass

- No horizontal overflow at 320, 375, 768, 1024, 1440.
- Exactly one `<h1>`; heading levels descend without skipping.
- All interactive targets ≥ 44px.
- Every `<img>`/decorative SVG handled: `aria-hidden="true"` on decorative, real `alt` otherwise.
- Form controls have associated `<label>`s.
- No console errors; no external resource beyond the Google Fonts link.
- Nav, footer, and CTA markup byte-identical to §3/§4.
- Nothing from §1 violated.

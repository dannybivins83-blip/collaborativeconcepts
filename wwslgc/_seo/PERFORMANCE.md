# Core Web Vitals — Audit & Fixes
**wwslgc** · created by the WWS SEO workflow (2 independent auditors: loading lens + mobile lens)

## ✅ Applied in this pass (safe, high-value)
1. **Long-lived immutable caching for images & fonts** (`vercel.json`) — `Cache-Control: public, max-age=31536000, immutable` for `jpg|jpeg|png|webp|avif|gif|ico|svg|woff2|woff`. Previously these fell through to Vercel's `max-age=0, must-revalidate`, forcing a revalidation of every image on every repeat visit. **Biggest repeat-visit speed win.**
   - ⚠️ Filenames aren't content-hashed, so when you change an image, rename it or add `?v=2` to bust the cache.
2. **Preconnect to Google Fonts hosts** (`wwslgc/index.html`) — added `<link rel="preconnect">` for `fonts.googleapis.com` and `fonts.gstatic.com` before the font stylesheets. Cuts DNS+TLS latency on the LCP webfont (Manrope H1).

## 🔧 Recommended next (need build tooling / image work — not applied blindly)
3. **Replace the runtime Tailwind CDN with a prebuilt static CSS file** — *highest single LCP/TBT win.* The page currently loads `cdn.tailwindcss.com` (~100KB+ JS that compiles CSS in-browser on every load, render-blocking). Move the inline `tailwind.config` into a real `tailwind.config.js`, build once with the Tailwind CLI, ship `/wwslgc/assets/wws.css`. **Touches every page** (index, 4 city pages, portal, admin) so it needs a coordinated build step + testing — do it as its own task.
   ```
   npx tailwindcss -i src/wws.css -o wwslgc/assets/wws.css --minify
   ```
4. **Convert hero/card images to WebP at mobile sizes** — current JPEGs are large (rooftop-crossover.jpg 465KB, housekeeping.jpg 323KB, ramps-walkways.jpg 320KB, lagala-logo.png 130KB). `cwebp -q 78` typically cuts 60–80%. Add `srcset`/`sizes` for the 2-col mobile grid.
5. **Explicit `width`/`height` on logo + card `<img>`** — prevents CLS (layout shift) when images decode. Logo (`/assets/lagala-logo.png`) ~180×48; cards 4:3 → `width="600" height="450"`.
6. **Make the Material Symbols icon font non-render-blocking** — it's a large variable font used only for small UI glyphs, currently blocking. Load via `media="print" onload="this.media='all'"` (with `<noscript>` fallback), or self-host a subset of the ~6 glyphs used.
7. **Defer GA/analytics execution** to `requestIdleCallback`/`load` so it's out of the critical path (minor once #3 is done).

## How to measure
- PageSpeed Insights: https://pagespeed.web.dev/?url=https://wwslgc.collaborativeconceptsfl.com/wwslgc
- GSC → Experience → Core Web Vitals (field data, ~28-day rolling)

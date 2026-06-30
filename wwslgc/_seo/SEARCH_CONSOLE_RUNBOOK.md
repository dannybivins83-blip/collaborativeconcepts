# Google Search Console — Setup Runbook
**Property:** https://wwslgc.collaborativeconceptsfl.com · created by the WWS SEO workflow

> Claude executed the live setup in the browser on 2026-06-30 (verify + submit sitemap + request indexing). This runbook documents what was done and how to repeat/maintain it.

## Verification method
**Recommended — Google Analytics verification (URL-prefix property).** GA4 (`G-K9ZEXRRMCK`) is already in the page `<head>` under the same Google account, so GSC confirms ownership instantly by reading the existing gtag snippet. No code change needed.

- **Fallback 1 — HTML tag:** paste `<meta name="google-site-verification" ...>` into the wwslgc `<head>`, redeploy on Vercel, then Verify. (URL-prefix only.)
- **Fallback 2 — DNS TXT:** add a `google-site-verification=...` TXT record at the DNS host for `collaborativeconceptsfl.com`. Required for a **Domain property**, which covers apex + ALL subdomains in one — best long-term. Can't use GA/HTML-tag methods.
- **Tradeoff:** URL-prefix = fastest here (GA verify). Domain = unified apex+subdomain reporting. Ideal: do both — GA-verify the wwslgc URL-prefix now, DNS-verify the Domain property later.

## Steps
1. Go to https://search.google.com/search-console — sign in with the account that owns GA4 `G-K9ZEXRRMCK`.
2. Property dropdown (top-left) → **Add property**.
3. Choose the **URL prefix** box. Enter exactly: `https://wwslgc.collaborativeconceptsfl.com` → Continue.
4. Expand **Google Analytics** under "Other verification methods" → **Verify** → reads existing snippet → **Go to property**.
5. *If GA verify fails:* use **HTML tag** fallback — copy the meta tag, paste into the wwslgc index `<head>`, commit, let Vercel redeploy, return and Verify.
6. Left sidebar → **Sitemaps** (Indexing section).
7. In "Add a new sitemap" enter the path only: `sitemap-wws.xml` → Submit. Confirm Status = **Success**.
8. **Cross-host note:** `https://collaborativeconceptsfl.com/sitemap.xml` (apex) can NOT be submitted from the wwslgc subdomain property. Create a **separate** apex property (`https://collaborativeconceptsfl.com/`) and submit `sitemap.xml` there.
9. Top **URL inspection** bar → paste each priority URL → wait for live test → **Request Indexing** → wait for confirmation toast.
10. Repeat for all 6 priority URLs (Google rate-limits to ~10–12 manual requests/day; 6 is fine).

## Sitemaps to submit
- `sitemap-wws.xml` — under the wwslgc property ✅
- `sitemap.xml` — under a **separate apex** `collaborativeconceptsfl.com` property (cross-host)

## Priority URLs to "Request Indexing" first
1. https://wwslgc.collaborativeconceptsfl.com/wwslgc
2. https://wwslgc.collaborativeconceptsfl.com/miami-roof-anchor-certification
3. https://wwslgc.collaborativeconceptsfl.com/fort-lauderdale-roof-anchor-certification
4. https://wwslgc.collaborativeconceptsfl.com/west-palm-beach-roof-anchor-certification
5. https://wwslgc.collaborativeconceptsfl.com/roof-anchor-certification
6. https://wwslgc.collaborativeconceptsfl.com/

## Weekly monitoring checklist
- **Performance → Search results:** Clicks, Impressions, CTR, Avg position. Sort **Queries** (e.g. "roof anchor certification miami") and **Pages** for what's earning impressions.
- **Indexing → Pages:** watch Indexed count climb; review "Why pages aren't indexed" (Crawled-not-indexed, Discovered-not-indexed, redirects/404s) for the 6 priority URLs.
- **Indexing → Sitemaps:** each sitemap still **Success**; Discovered URLs matches expected count; investigate "Couldn't fetch".
- **Experience → Core Web Vitals:** Mobile + Desktop LCP/INP/CLS stay in "Good" (the cache-header + preconnect fixes from this workflow help here).
- **Security & Manual Actions:** "No issues detected".
- **URL Inspection spot-check:** 1–2 priority URLs show "URL is on Google" and the right canonical.

## Timeline expectations
- Performance data: starts ~2–3 days after verification.
- Full indexing of submitted/requested URLs: days to a few weeks.

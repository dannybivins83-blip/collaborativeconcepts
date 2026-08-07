# Search Console Puller — setup & usage

Pulls **real** query/page/geo performance from Google Search Console into
markdown + CSV reports, and cross-references search demand against permit
volume from the permits engine.

Engine: `api/gsc.py` · CLI: `_gsc_pull.py` · Tests: `python3 _gsc_tests.py` (45, network mocked)

> Why not Google Trends: Trends returns a 0–100 index that is **rescaled on every
> request** (two pulls aren't comparable), and niche B2B terms like "walking
> working surfaces compliance" often don't register at all. Search Console
> returns actual impressions, clicks, CTR and position for pages we own.
> Google's official Trends API is still application-gated alpha as of Aug 2026.

## One-time setup (~10 min)

**Service account is the right choice here** — no interactive consent, nothing
expires, safe for cron.

1. **Google Cloud Console** → create (or pick) a project → **APIs & Services →
   Library** → enable **Google Search Console API**.
2. **APIs & Services → Credentials → Create credentials → Service account.**
   Name it e.g. `gsc-puller`. No project roles needed.
3. Open the service account → **Keys → Add key → Create new key → JSON.**
   Download it. **Save it outside this repo** (it's a private key).
4. Copy the service account's email (`gsc-puller@<project>.iam.gserviceaccount.com`).
5. **Search Console** → pick the property → **Settings → Users and permissions →
   Add user** → paste that email → permission **Full** (Restricted also works for
   read-only reporting; Full is needed if you later want URL inspection).
   Repeat for every property you want to pull.
6. Point the tool at the key:
   ```bash
   export GSC_SERVICE_ACCOUNT_JSON=/secure/path/gsc-puller.json   # path or inline JSON
   export GSC_SITE=https://wwslgc.collaborativeconceptsfl.com
   ```

<details><summary>OAuth alternative (if a service account isn't an option)</summary>

Set `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`, `GSC_REFRESH_TOKEN` instead. Scope:
`https://www.googleapis.com/auth/webmasters.readonly`. Same failure mode as the
tastytrade grant — refresh tokens get revoked by password changes, so the
service account is preferred.
</details>

**Never commit the key or paste it into chat.** The tool reports missing config
by variable NAME only and never prints a secret value.

## Usage

```bash
python3 _gsc_pull.py --list                    # which properties can this key read?
python3 _gsc_pull.py --days 28                 # report for $GSC_SITE
python3 _gsc_pull.py --all --days 90           # every readable property
python3 _gsc_pull.py --site https://collaborativeconceptsfl.com --days 28 \
        --permits permits.csv --out wwslgc/_seo
```

Outputs to `--out` (default `wwslgc/_seo`):
`gsc-<host>-<end>.md` + `-queries.csv`, `-pages.csv`, `-cities.csv`.

## What the report gives you

| Section | Use it for |
|---|---|
| **Totals** | Clicks/impressions/CTR/position vs the previous equal-length period |
| **Top queries / pages** | What's actually earning impressions |
| **Striking distance** | Queries at positions 4–20 with real volume — the cheapest wins. `upside_clicks` estimates the gain from reaching position 3 |
| **CTR gaps** | Ranking top-10 but under-clicked → a title/meta problem, not a ranking problem |
| **Gainers / losers** | Period movers, **including queries that dropped out entirely** |
| **City pages** | Per-city performance for the 14 `*-roof-anchor-certification` pages |
| **Search demand vs permits** | Per county: permits issued vs impressions earned. Flags counties with construction activity and **no** search presence |

## Notes & gotchas

- **3-day finalization lag.** Reports end at today−3 by default; newer data is
  partial and revises upward. Override with `--end`.
- **Position is impression-weighted**, not a plain mean — a plain average lets
  one long-tail row at position 90 wreck the number.
- **The CTR-by-position curve is a heuristic.** Real CTR swings with SERP
  features and intent; treat "missed clicks" as a ranking signal, not a promise.
- **Pagination:** 25k rows/request, up to 20 pages. A 90-day query-level pull on
  a small site is well inside that.
- **Coverage gap today:** the permits engine covers **Martin County**, but there
  is no Martin city page (Stuart / Palm City / Hobe Sound). That county shows as
  `⚠️ no coverage` in the cross-reference until a page exists.
- Adding a city page? Add its slug → county in `CITY_COUNTY` in `api/gsc.py`.

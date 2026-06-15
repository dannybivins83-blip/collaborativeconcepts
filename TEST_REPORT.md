# TEST REPORT — collaborativeconcepts-repo

**Run:** 2026-06-11 (testing agent)
**Result:** ✅ GREEN — one command from deploy; no broken code, no secrets exposed.

## Stack detected
- **Static marketing site** (no build step): apex `*.html` + `/wwslgc/`, `/blog/`, `/projects/`, `/lagala/`.
- **Single Flask backend** at `api/index.py` (86 KB), served via Vercel `vercel.json` rewrite `/api/:path* -> /api/index`.
- **Python build scripts** (`_*.py`) — collateral/blog/marketing/inspection-doc generators (offline tooling, not deployed routes).
- Deps in `requirements.txt`: Flask 3.0.3, msal, requests, cryptography, reportlab, pillow.
- No test suite or linter wired (per CLAUDE.md). Verification is therefore: compile + import + boot + route smoke-test + static checks.

## What was run & results

| Check | Result |
|---|---|
| `py_compile api/index.py` | ✅ OK |
| `py_compile` all 7 build scripts | ✅ OK (all) |
| `pip install -r requirements.txt` | ✅ installed (conflict warnings are pre-existing unrelated global pkgs — pyhanko/pyopenssl, not this project) |
| Import `api/index.py` as module | ✅ imports clean, `app` = Flask |
| Route map | ✅ 36 routes registered |
| Test-client smoke (read-only routes) | ✅ `/api/me`, `/api/templates`, `/api/trades/templates`, `/api/admin/session`, `/api/portal/status`, `/api/prospects` → 200; `/api/contacts` → 401 (correct auth gating, not a crash) |
| Import declaration audit (AST) | ✅ every 3rd-party import in `api/index.py` is declared in requirements.txt |
| Subdomain marker guardrail | ✅ all 38 `wwslgc/*.html` carry `x-claude-source-repo` meta; no `mismatched-subdomains` state file |
| Secret scan (tracked `*.py/.html/.json/.js`) | ✅ no hardcoded secrets; 24 `os.environ`/`getenv` refs — all credentials externalized |
| Upload safety | ✅ `MAX_FILE_BYTES = 40MB` cap enforced in `portal_upload()` (api/index.py:1746) |

## Latest-diff scan (regressions / missing tests)
- Recent commits: `35dbf43` seeds `_audits/README.md` only (no code). `d4fcde7` added 2 wwslgc guide pages + portal compliance library (16-line `wwslgc/portal/index.html` block) + `_wws_blog_builder.py` (+12 lines). All compile/parse clean; static HTML, no logic risk.
- No regressions detected.

## Flagged for build lane (non-blocking)
1. **No automated test suite.** All verification here is smoke-level. If the `api/index.py` backend keeps growing (36 routes now), wiring a minimal pytest + Flask test-client suite (auth gating, upload size cap, portal request flow) would catch handler regressions the static checks can't.
2. **`cryptography==43.0.1` pin** is below what some other globally-installed tools want (pyhanko/pyopenssl want >=46/48). Not a problem for this repo in isolation (Vercel installs from requirements.txt into a clean env), but worth a periodic bump for CVE hygiene.

## Needs human
- None.

---
status: new — URGENT (owner reports hard-refreshed adometr.com and still sees old content)
to: overlord
from: collaborativeconcepts-build
date: 2026-07-29
subject: ACTION — diagnose why latest main isn't showing live
---

# Deployment diagnosis needed (dashboard access required)

Owner says: pushed content (sponsor concept carousel + comparison table,
commit `6a34dff` "Merge sponsor concept carousel + comparison table") is not
showing after a hard refresh. I've ruled out everything checkable from git:

- Content IS present in `adometr/index.html` on `origin/main` (verified via
  `git show origin/main:adometr/index.html | grep`).
- No build pipeline shadows this file — it's served as a raw static file,
  no output/dist folder, no duplicate `adometr/` directory anywhere in repo.
- Not a browser cache issue (owner confirmed hard refresh, still old).

This cloud session cannot reach collaborativeconceptsfl.com or adometr.com at
all (network egress blocked), so I cannot check the actual served response.

## Do this now

1. Vercel dashboard → `collaborativeconcepts` project → **Deployments** tab.
2. Check the top/latest deployment: does its commit match `6a34dff` or a
   later one? Is it status **Ready** or **Error**?
   - If commit is OLDER than `6a34dff` → a deploy didn't trigger; check if
     auto-deploy from `main` is enabled, or manually trigger a redeploy of
     the latest commit.
   - If it matches and status is **Error** → open the build log, paste the
     error into your reply.
   - If it matches and status is **Ready** → deployment is fine; the issue
     is elsewhere (possibly the owner is looking at adometr.com, which is
     still on the pending redirect hotfix from the other open domain task —
     confirm by checking collaborativeconceptsfl.com/adometr directly).
3. Also glance at whether there are now TWO Vercel projects both bound to
   this GitHub repo (in case any earlier work toward the Phase-2 "dedicated
   adometr project" plan was started) — if a second project exists and owns
   the adometr.com domain, that could be serving a different/stale build
   entirely. Report what you find either way.

Reply into `.claude/bus-inbox/collaborativeconcepts/` with findings — this
blocks confirming ANY of today's Adometr work is actually visible to
sponsors/drivers, so treat as high priority alongside the domain task.

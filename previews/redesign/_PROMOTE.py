# -*- coding: utf-8 -*-
"""Promote previews/redesign -> production route structure.

DRY RUN by default. Run with --apply to write.
Builds the nested URL structure the audit IA calls for, rewrites internal links
to production routes, flips robots to indexable, and reports what it did.
Assets are already staged at /assets/redesign/ and are NOT moved.
"""
import os, re, shutil, sys

SRC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(SRC, "..", ".."))
APPLY = "--apply" in sys.argv

# source file -> production output path (relative to repo root)
MAP = {
    "index.html":                        "index.html",
    "development.html":                  "development/index.html",
    "development-projects.html":         "development/projects.html",
    "development-madeira-beach.html":    "development/madeira-beach.html",
    "investor-inquiries.html":           "development/investor-inquiries.html",
    "solutions.html":                    "solutions/index.html",
    "solutions-revenue-recovery.html":   "solutions/revenue-recovery.html",
    "solutions-systems-automation.html": "solutions/systems-automation.html",
    "work.html":                         "work/index.html",
    "work-madeira-beach.html":           "work/madeira-beach.html",
    "ventures.html":                     "ventures.html",
    "about.html":                        "about.html",
    "insights.html":                     "insights/index.html",
    "insights-article.html":             "insights/non-conforming-lots-coastal-communities.html",
    "contact.html":                      "contact.html",
    "privacy.html":                      "privacy.html",
    "terms.html":                        "terms.html",
}

# source filename -> production URL used in hrefs
ROUTE = {
    "index.html": "/",
    "development.html": "/development",
    "development-projects.html": "/development/projects",
    "development-madeira-beach.html": "/development/madeira-beach",
    "investor-inquiries.html": "/development/investor-inquiries",
    "solutions.html": "/solutions",
    "solutions-revenue-recovery.html": "/solutions/revenue-recovery",
    "solutions-systems-automation.html": "/solutions/systems-automation",
    "work.html": "/work",
    "work-madeira-beach.html": "/work/madeira-beach",
    "ventures.html": "/ventures",
    "about.html": "/about",
    "insights.html": "/insights",
    "insights-article.html": "/insights/non-conforming-lots-coastal-communities",
    "contact.html": "/contact",
    "privacy.html": "/privacy",
    "terms.html": "/terms",
}

print("DRY RUN — nothing written. Pass --apply to execute.\n" if not APPLY
      else "APPLYING.\n")

for src, dst in MAP.items():
    p = os.path.join(SRC, src)
    s = open(p, encoding="utf-8").read()

    # internal links -> production routes
    def repl(m):
        return 'href="%s"' % ROUTE[m.group(1)]
    s2, n = re.subn(r'href="([a-z0-9-]+\.html)"',
                    lambda m: repl(m) if m.group(1) in ROUTE else m.group(0), s)

    # make indexable in production
    s2 = s2.replace('<meta name="robots" content="noindex, nofollow" />',
                    '<meta name="robots" content="index, follow, max-image-preview:large" />')

    out = os.path.join(REPO, dst)
    print(f"  {src:38} -> {dst:52} ({n} links rewritten)")
    if APPLY:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        open(out, "w", encoding="utf-8", newline="").write(s2)

print(f"\n{len(MAP)} pages.")
print("Assets already at /assets/redesign/ — not moved.")
if not APPLY:
    print("\nNothing was written. Re-run with --apply when you are ready.")

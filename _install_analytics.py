"""Install Vercel Web Analytics + Speed Insights on every page."""
import os
import glob

REPO = os.path.dirname(os.path.abspath(__file__))

# Vercel injects these endpoints when Web Analytics + Speed Insights are
# enabled in the Vercel dashboard. The script tags are inert until enabled.
ANALYTICS_SNIPPET = """<!-- Vercel Analytics (enable in Vercel dashboard: Project → Analytics → Enable Web Analytics) -->
<script defer src="/_vercel/insights/script.js"></script>
<!-- Vercel Speed Insights -->
<script defer src="/_vercel/speed-insights/script.js"></script>
"""

# Match all top-level pages + blog pages
files = sorted(set(
    glob.glob(os.path.join(REPO, "*.html"))
    + glob.glob(os.path.join(REPO, "blog", "*.html"))
))

patched = 0
already = 0
for fp in files:
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    if "/_vercel/insights/script.js" in content:
        already += 1
        continue
    if "</head>" not in content:
        print(f"SKIP (no </head>): {fp}")
        continue
    content = content.replace("</head>", ANALYTICS_SNIPPET + "</head>", 1)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    patched += 1
    print(f"patched: {os.path.relpath(fp, REPO)}")

print(f"\nDone. Patched {patched} files. Already had snippet: {already} files.")

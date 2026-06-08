"""Install Google Analytics 4 (gtag.js) on every page.

Mirrors the scope of _install_analytics.py: root *.html + blog/*.html.
Idempotent — re-running skips files already patched with the same ID.
"""
import os
import glob

REPO = os.path.dirname(os.path.abspath(__file__))
GA4_ID = "G-K9ZEXRRMCK"

GA4_SNIPPET = f"""<!-- Google Analytics (GA4) -->
<link rel="preconnect" href="https://www.googletagmanager.com"/>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin=""/>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{GA4_ID}');
</script>
"""

files = sorted(set(
    glob.glob(os.path.join(REPO, "*.html"))
    + glob.glob(os.path.join(REPO, "blog", "*.html"))
))

patched = 0
already = 0
for fp in files:
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    if GA4_ID in content:
        already += 1
        continue
    if "</head>" not in content:
        print(f"SKIP (no </head>): {fp}")
        continue
    content = content.replace("</head>", GA4_SNIPPET + "</head>", 1)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    patched += 1
    print(f"patched: {os.path.relpath(fp, REPO)}")

print(f"\nDone. Patched {patched} files. Already had snippet: {already} files.")

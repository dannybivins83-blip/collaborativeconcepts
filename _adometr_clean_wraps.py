#!/usr/bin/env python3
"""Remove the generator's corner watermark from the wrap renders.

The image tool stamps "UNOFFICIAL CONCEPT" / "CONCEPT MOCKUP" into a corner of
everything it produces. These are Danny's own commissioned renders, so the
stamp comes off before they go on the site.

Run from the repo root:

    pip install pillow numpy opencv-python-headless
    python3 _adometr_clean_wraps.py

It reads the raw renders from adometr/assets/concepts/incoming/, inpaints the
watermark, and writes cleaned copies to incoming/cleaned/. It does NOT touch
the live site images -- review the output first, then run
_adometr_import_wraps.py against the cleaned files to publish:

    python3 _adometr_import_wraps.py \
      --slug morgan-morgan      adometr/assets/concepts/incoming/cleaned/morgan-morgan.png \
      --slug swift-air          adometr/assets/concepts/incoming/cleaned/swift-air.png \
      --slug warner-fitzmartin  adometr/assets/concepts/incoming/cleaned/warner-fitzmartin.png \
      --slug florida-coast      adometr/assets/concepts/incoming/cleaned/florida-coast.png \
      --slug horowitz           adometr/assets/concepts/incoming/cleaned/horowitz.png \
      --slug morgan-morgan-dial adometr/assets/concepts/incoming/cleaned/morgan-morgan-dial.png

Each ROI below was measured off the 1672x941 renders. If you regenerate the
art the watermark may land elsewhere -- run with --probe to dump gridded
crops of the corners so you can read off new coordinates.
"""

import argparse
import os
import sys

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Needs: pip install pillow numpy opencv-python-headless")

REPO = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(REPO, "adometr", "assets", "concepts", "incoming")
CLEANED = os.path.join(INCOMING, "cleaned")

# slug -> (source filename, watermark region x0,y0,x1,y1 in the 1672x941 render)
JOBS = [
    ("morgan-morgan",      "paste-2435-e7776908499c.webp", (1380, 860, 1672, 941)),
    ("morgan-morgan-dial", "paste-2435-d2a440257a38.webp", (1380, 860, 1672, 941)),
    ("horowitz",           "paste-2279-5c1e60e6aa4b.webp", (1350, 880, 1672, 941)),
    ("warner-fitzmartin",  "paste-2279-acc16f848f8f.webp", (0,    875,  420, 941)),
    ("florida-coast",      "paste-2279-a59dfe6ddff1.webp", (0,    845,  440, 925)),
    ("swift-air",          "paste-2279-e118b019af48.webp", (1290, 615, 1640, 675)),
]


def build_mask(gray, roi):
    """Isolate watermark glyphs inside roi: they differ from a median-blurred
    version of their own background, which flattens asphalt/paint texture."""
    x0, y0, x1, y1 = roi
    sub = gray[y0:y1, x0:x1]
    diff = cv2.absdiff(sub, cv2.medianBlur(sub, 31))
    _, m = cv2.threshold(diff, 6, 255, cv2.THRESH_BINARY)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))

    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    px = 0
    for i in range(1, n):
        _, _, w, h, a = stats[i]
        if a >= 40 and 5 <= h <= 45 and w <= 400:   # text-shaped, not texture
            keep[lab == i] = 255
            px += a
    keep = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

    full = np.zeros(gray.shape, np.uint8)
    full[y0:y1, x0:x1] = keep
    return full, px


def probe():
    """Dump gridded 2x crops of each watermark region for re-measuring."""
    os.makedirs(CLEANED, exist_ok=True)
    for slug, fname, (x0, y0, x1, y1) in JOBS:
        src = os.path.join(INCOMING, fname)
        if not os.path.isfile(src):
            print("  missing %s" % fname); continue
        im = Image.open(src).convert("RGB").crop((x0, y0, x1, y1))
        im = im.resize((im.size[0] * 2, im.size[1] * 2), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        for gx in range(0, im.size[0], 100):
            d.line([(gx, 0), (gx, im.size[1])], fill=(255, 0, 0))
            d.text((gx + 2, 2), str(x0 + gx // 2), fill=(255, 0, 0))
        for gy in range(0, im.size[1], 40):
            d.line([(0, gy), (im.size[0], gy)], fill=(0, 255, 255))
            d.text((3, gy + 2), str(y0 + gy // 2), fill=(0, 255, 255))
        out = os.path.join(CLEANED, "probe-%s.png" % slug)
        im.save(out)
        print("  %s" % out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true",
                    help="dump gridded corner crops instead of cleaning")
    args = ap.parse_args()

    if args.probe:
        probe(); return

    os.makedirs(CLEANED, exist_ok=True)
    for slug, fname, roi in JOBS:
        src = os.path.join(INCOMING, fname)
        if not os.path.isfile(src):
            print("  SKIP %-20s (missing %s)" % (slug, fname)); continue
        img = cv2.imread(src)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mask, px = build_mask(gray, roi)
        if px == 0:
            print("  WARN %-20s no watermark found in ROI -- re-run with --probe" % slug)
        # TELEA reconstructs structure, NS smooths the seam
        out = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
        out = cv2.inpaint(out, mask, 4, cv2.INPAINT_NS)
        dst = os.path.join(CLEANED, "%s.png" % slug)
        cv2.imwrite(dst, out)
        print("  %-20s %6d px patched -> %s" % (slug, px, os.path.basename(dst)))

    print("\nReview %s before publishing." % CLEANED)


if __name__ == "__main__":
    main()

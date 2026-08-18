#!/usr/bin/env python3
"""Convert raw wrap mockup renders into site-ready concept images.

The landing page carousel (adometr/index.html) serves 1400x788 WebP files out
of adometr/assets/concepts/. Image generators hand back multi-megabyte PNGs at
whatever aspect ratio they feel like, so every new mockup has to be cropped,
resized and re-encoded before it goes near the page.

Drop the raw PNGs in adometr/assets/concepts/incoming/ and run:

    python3 _adometr_import_wraps.py --auto

--auto maps the incoming files, sorted by name, onto SLUGS in order and prints
the mapping it used. Image generators number their exports in the order they
were produced, which is not necessarily the order below, so read the printed
mapping and re-run with explicit pairs if it landed wrong:

    python3 _adometr_import_wraps.py --slug swift-air raw/whatever.png

Requires Pillow (already in requirements.txt).
"""

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

REPO = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = os.path.join(REPO, "adometr", "assets", "concepts")
INCOMING = os.path.join(CONCEPTS, "incoming")

TARGET_W, TARGET_H = 1400, 788
QUALITY = 82

# Carousel order on the landing page.
SLUGS = [
    "morgan-morgan",
    "swift-air",
    "warner-fitzmartin",
    "florida-coast",
    "horowitz",
    "morgan-morgan-dial",
]


def convert(src, slug):
    """Center-crop src to the carousel aspect ratio and write it as WebP."""
    out = os.path.join(CONCEPTS, "adometr-sponsor-%s.webp" % slug)
    with Image.open(src) as im:
        im = im.convert("RGB")
        sw, sh = im.size

        # Center-crop to 1400:933 before scaling so nothing is squashed.
        target_ratio = TARGET_W / TARGET_H
        if sw / sh > target_ratio:
            keep_w = int(round(sh * target_ratio))
            left = (sw - keep_w) // 2
            im = im.crop((left, 0, left + keep_w, sh))
        else:
            keep_h = int(round(sw / target_ratio))
            top = (sh - keep_h) // 2
            im = im.crop((0, top, sw, top + keep_h))

        im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        im.save(out, "WEBP", quality=QUALITY, method=6)

    kb = os.path.getsize(out) / 1024
    print("  %-46s -> %s (%.0f KB)" % (os.path.basename(src), os.path.basename(out), kb))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", action="store_true",
                    help="map sorted files in %s onto SLUGS in order" % INCOMING)
    ap.add_argument("--slug", nargs=2, action="append", metavar=("SLUG", "PATH"),
                    default=[], help="convert PATH into the concept image for SLUG")
    args = ap.parse_args()

    pairs = [(slug, path) for slug, path in args.slug]

    if args.auto:
        if not os.path.isdir(INCOMING):
            sys.exit("No incoming folder: %s" % INCOMING)
        raw = sorted(f for f in os.listdir(INCOMING)
                     if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
        if not raw:
            sys.exit("No images found in %s" % INCOMING)
        if len(raw) != len(SLUGS):
            print("WARNING: %d incoming files but %d slugs — pairing the first %d"
                  % (len(raw), len(SLUGS), min(len(raw), len(SLUGS))), file=sys.stderr)
        pairs += [(slug, os.path.join(INCOMING, name))
                  for slug, name in zip(SLUGS, raw)]

    if not pairs:
        ap.error("nothing to do — pass --auto or at least one --slug SLUG PATH")

    print("Writing to %s" % CONCEPTS)
    for slug, path in pairs:
        if not os.path.isfile(path):
            sys.exit("Missing source image: %s" % path)
        convert(path, slug)

    print("\nDone. Check each image before committing — --auto guesses the "
          "mapping from filename order and cannot read the wrap artwork.")


if __name__ == "__main__":
    main()

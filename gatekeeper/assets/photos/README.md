# Photo assets

Two kinds of photo live in this folder: the **"Recent work" gallery** (a
`PHOTOS` list in `_gatekeeper_build.py`, filtered to whatever files actually
exist) and **dedicated placements** (hero, why-choose-us, residential/
commercial section, vinyl service page) that are hardcoded to a specific
file and are not optional.

After adding or changing anything here, rebuild:

```
python3 _gatekeeper_build.py
```

## Dedicated placements — already live

These 5 came from a client-supplied asset package and are already in the repo
as optimized JPEG + WebP derivatives (the multi-MB source PNGs are not
committed — see the main `gatekeeper/README.md` "Brand" section):

| File(s) | Used on |
|---|---|
| `hero-driveway-gate-{640,960,1280,1920}.{jpg,webp}` | Home hero (responsive `srcset`) |
| `services-overview.{jpg,webp}` | Also in the "Recent work" gallery |
| `craftsmanship-hardware.{jpg,webp}` | Home "Why Gatekeeper" photo-split |
| `vinyl-privacy-fence.{jpg,webp}` | Vinyl service page artband + gallery |
| `commercial-sliding-gate.{jpg,webp}` | Home residential/commercial section + `services.html#commercial` + gallery |

## "Recent work" gallery — 7 files still pending

The gallery (`PHOTOS` in the builder) currently has 4 entries fulfilled by the
dedicated-placement files above, plus these 7 casual jobsite photos that are
**not yet in the repo** — the files themselves still need to be added here
under these exact names, then rebuilt:

| Filename | What it shows | Caption used on the site |
|---|---|---|
| `existing-fence-gate.jpg` | The old stained wood privacy fence and gate at the unit, before work | "The existing fence and gate, before replacement." |
| `clearing-fence-line.jpg` | Crew member clearing overgrowth along the fence line with a chainsaw | "Clearing the fence line before any posts go in." |
| `site-prep.jpg` | Root ball dug out, lumber staged on the grass by the sidewalk | "Old root ball dug out of the line so the new posts sit where they should." |
| `setting-posts.jpg` | Two crew members setting a post beside the patio | "Setting posts and laying out rails." |
| `new-rails-lakefront.jpg` | New pressure-treated posts and rails up along the lake | "New pressure-treated posts and rails up on a lakefront run." |
| `finished-gate-corner.jpg` | Finished gate and post at a house corner, yard cleared and raked | "Finished gate and post, with the site cleaned up after." |
| `finished-corner-run.jpg` | Completed fence turning the corner of the house into open lawn | "The completed fence turning the corner of the house." |

The first *present* entry in `PHOTOS` renders wide across the top of the
gallery; the rest tile beneath it. Right now that's `services-overview.jpg`.
Once `existing-fence-gate.jpg` (first in list order) exists, it takes over the
lead spot automatically — no code change needed. Reorder `PHOTOS` in the
builder to change that behavior.

## Missing files are skipped, not broken

`available_photos()` filters `PHOTOS` to files that actually exist. A photo
with no file is silently dropped; if literally none were present the entire
gallery section would be omitted from the page (that's why it's safe to add
these 7 one at a time — the gallery already renders correctly with just the
4 dedicated-placement photos live today).

## Before committing new photos

- **Resize to about 1600px wide and save at JPEG quality ~80.** Phone photos
  run 4–8 MB each. Target under ~400 KB per file. The 5 already in the repo
  were processed with Pillow: `im.resize(..., Image.LANCZOS)` to the target
  width, then `.save(path, "JPEG", quality=82, optimize=True, progressive=True)`
  and a matching `.save(path, "WEBP", quality=80, method=6)`.
- Gallery images are already `loading="lazy"` and `decoding="async"`, and are
  cropped by CSS (`object-fit: cover`), so aspect ratio does not need to be
  uniform.
- A single JPEG per gallery photo is enough at this scale — no need to build
  a full responsive `srcset` for anything except the hero (which already has
  one).

## Captions

Captions describe **only what is visible in the frame**. Do not add a city, a
linear-footage number, a completion time, or a customer name unless the owner
confirms it — the rest of the site holds to publicly verifiable facts and the
gallery should not be the exception.

If the owner can confirm details (where the job was, what was installed, how
long it took), those make the captions much stronger. Ask before writing them in.

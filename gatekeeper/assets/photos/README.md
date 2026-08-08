# Job photos

Drop the photo files here using the **exact filenames** below, then rebuild:

```
python3 _gatekeeper_build.py
```

The gallery appears on the home page between the services grid and the
"The owner is on your job" section.

## Expected files

| Filename | What it shows | Caption used on the site |
|---|---|---|
| `existing-fence-gate.jpg` | The old stained wood privacy fence and gate at the unit, before work | "The existing fence and gate, before replacement." |
| `clearing-fence-line.jpg` | Crew member clearing overgrowth along the fence line with a chainsaw | "Clearing the fence line before any posts go in." |
| `site-prep.jpg` | Root ball dug out, lumber staged on the grass by the sidewalk | "Old root ball dug out of the line so the new posts sit where they should." |
| `setting-posts.jpg` | Two crew members setting a post beside the patio | "Setting posts and laying out rails." |
| `new-rails-lakefront.jpg` | New pressure-treated posts and rails up along the lake | "New pressure-treated posts and rails up on a lakefront run." |
| `finished-gate-corner.jpg` | Finished gate and post at a house corner, yard cleared and raked | "Finished gate and post, with the site cleaned up after." |
| `finished-corner-run.jpg` | Completed fence turning the corner of the house into open lawn | "The completed fence turning the corner of the house." |

The first entry in `PHOTOS` (currently `existing-fence-gate.jpg`) renders wide
across the top of the gallery; the rest tile beneath it. Reorder the `PHOTOS`
list in `_gatekeeper_build.py` to change which one leads.

## Missing files are skipped, not broken

`available_photos()` filters to files that actually exist. A photo with no file
is silently dropped, and if none are present the entire gallery section is
omitted from the page. **The site can never ship a broken image**, so it is safe
to add the photos one at a time.

## Before committing

- **Resize to about 1600px wide and save at JPEG quality ~80.** Phone photos run
  4–8 MB each; five of those would make the home page brutally slow on cellular.
  Target under ~400 KB per file.
- Images are already `loading="lazy"` and `decoding="async"`, and are cropped by
  CSS (`object-fit: cover`), so aspect ratio does not need to be uniform.
- Optional: generate WebP alongside the JPEGs with `sharp` the way
  `assets/wws/` does, and switch the gallery to `<picture>`. Not wired up —
  properly sized JPEGs are fine at this scale.

## Captions

Captions describe **only what is visible in the frame**. Do not add a city, a
linear-footage number, a completion time, or a customer name unless the owner
confirms it — the rest of the site holds to publicly verifiable facts and the
gallery should not be the exception.

If the owner can confirm details (where the job was, what was installed, how
long it took), those make the captions much stronger. Ask before writing them in.

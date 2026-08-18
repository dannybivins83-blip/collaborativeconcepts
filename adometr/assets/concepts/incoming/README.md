# Raw wrap mockup drop folder

Put the full-resolution wrap renders here (PNG/JPG, any size), then run:

    python3 _adometr_import_wraps.py --auto

That crops + resizes them to the 1400x788 WebP the landing page carousel
expects and writes them one level up as `adometr-sponsor-<slug>.webp`.

`--auto` pairs files with slugs by sorted filename order, which is a guess —
read the mapping it prints and re-run with explicit `--slug SLUG PATH` pairs
if any image landed on the wrong sponsor.

Raw sources are ignored by git (see .gitignore); only the converted WebP files
are committed.

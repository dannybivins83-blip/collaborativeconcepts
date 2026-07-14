#!/usr/bin/env python3
"""apply_wws_phone.py — one-command WWS phone swap.

WHAT THIS DOES
    Swaps the umbrella number (561) 475-8615 -> a NEW La Gala Construction / WWS
    number, but ONLY inside WWS-scoped surfaces. Collaborative Concept's apex
    site, /blog, /design variants, presentations, previews, projects, wake, and
    the Casa Del Monte / La Gala portal surfaces are NEVER touched — they keep
    475-8615, which is Collab's umbrella number.

    (561) 475-8615 belongs to Collaborative Concept LLC (~238+ files repo-wide).
    La Gala Construction / WWS is getting its own dedicated number. This script
    moves ONLY WWS's surfaces to that new number.

USAGE
    python apply_wws_phone.py "(954) XXX-XXXX"            # dry-run (default) — shows what WOULD change
    python apply_wws_phone.py "(954) XXX-XXXX" --dry-run  # same, explicit
    python apply_wws_phone.py "(954) XXX-XXXX" --commit   # actually writes the files
    python apply_wws_phone.py "(954) XXX-XXXX" --commit --regen  # also regenerates guides + collateral

    Accepts any input that contains exactly 10 digits, e.g.
        "(954) 555-0123"  "954-555-0123"  "9545550123"  "+1 954 555 0123"

AFTER --commit YOU MUST REGENERATE the two builders' outputs (never hand-edit
generated HTML/PDF):
        python _wws_blog_builder.py     # -> wwslgc/guides/*.html  (44 files)
        python _build_marketing.py      # -> wwslgc/collateral/*.pdf (4 files)
    (or pass --regen to have this script run them for you after --commit)

REVERSIBLE
    Every change is a pure literal find/replace on git-tracked files. To undo:
        git checkout -- <files>
    or re-run this script with the OLD number to swap back.

SAFETY
    The script operates ONLY on the hard-coded allowlist below. It never globs
    or scans the repo, so it structurally cannot touch an out-of-scope file.
    In api/index.py it uses EXACT context anchors so it only edits the 3 verified
    WWS strings and leaves the Collab / Casa Del Monte / shared-invoice strings
    alone. See WWS_PHONE_SWAP_MANIFEST.md for the full in/out scope list.
"""
import os
import re
import subprocess
import sys

# --- old (umbrella) number components -------------------------------------
OLD_AREA, OLD_PREFIX, OLD_LINE = "561", "475", "8615"
OLD_TEN = OLD_AREA + OLD_PREFIX + OLD_LINE  # 5614758615

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))     # wwslgc/_seo
REPO = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))  # repo root

# --- IN-SCOPE: WWS hand-authored pages (direct literal swap, all forms) ----
HTML_FILES = [
    "wwslgc/index.html",                              # WWS landing page
    "wwslgc/roof-anchor-certification.html",          # WWS money / service page
    "wwslgc/portal/index.html",                       # WWS client portal (front end)
    "wwslgc/aventura-roof-anchor-certification.html",
    "wwslgc/boca-raton-roof-anchor-certification.html",
    "wwslgc/boynton-beach-roof-anchor-certification.html",
    "wwslgc/fort-lauderdale-roof-anchor-certification.html",
    "wwslgc/hollywood-roof-anchor-certification.html",
    "wwslgc/miami-roof-anchor-certification.html",
    "wwslgc/pompano-beach-roof-anchor-certification.html",
    "wwslgc/west-palm-beach-roof-anchor-certification.html",
]

# --- IN-SCOPE: WWS builders (swap the phone CONSTANT; regenerate outputs) ---
# NEVER hand-edit the generated outputs. Swap the source constant, then re-run
# the builder to regenerate wwslgc/guides/*.html and wwslgc/collateral/*.pdf.
BUILDER_FILES = [
    "_wws_blog_builder.py",   # -> wwslgc/guides/*.html (44 generated files)
    "_build_marketing.py",    # -> wwslgc/collateral/*.pdf (4 generated files)
]

# --- IN-SCOPE: api/index.py — ONLY these 3 verified WWS strings -------------
# Context-anchored so we can never touch the Collab / Casa Del Monte / shared
# strings that live in the same shared backend file. Each entry is an exact
# substring that uniquely identifies a WWS-owned string; only the phone inside
# it is swapped. See the manifest for why lines 98 / 2747 / 3745 are EXCLUDED.
API_FILE = "api/index.py"
API_ANCHORS = [
    # SIGNATURE const — La Gala/WWS lead outreach email signature (wwslgc_gstate
    # outreach tool). Unique via "danny@lagalacon.com" (Collab's CC_SIGNATURE
    # uses dannybivins83@gmail.com, so it will NOT match this anchor).
    "(561) 475-8615 · danny@lagalacon.com",
    # _notify_client() — WWS client-portal notification email (template hard-codes
    # "WWS Compliance · Client Portal").
    "<p style='font-size:12px;color:#5b6573;margin-top:26px'>Questions? Call (561) 475-8615.</p>",
    # login_email_start() — WWS portal OTP-send failure message.
    "Could not send the code. Please call (561) 475-8615.",
]
# Deliberately EXCLUDED api/index.py strings (kept at 475-8615, flagged for human
# review in the manifest): CC_SIGNATURE (Collaborative Concept outreach),
# doc_receipt() invoice string (shared billing), _upload_email_html() "Lot {lot}"
# email (Casa Del Monte / La Gala portal, not WWS).


def parse_number(raw):
    """Return (area, prefix, line) from any input containing exactly 10 digits."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10 or not digits.isdigit():
        sys.exit(
            f"ERROR: need exactly 10 digits, got {len(digits)} from {raw!r}.\n"
            "       Example: python apply_wws_phone.py \"(954) 555-0123\""
        )
    if "X" in raw.upper() or set(digits) == {"0"}:
        sys.exit(f"ERROR: {raw!r} looks like a placeholder, not a real number.")
    return digits[0:3], digits[3:6], digits[6:10]


def build_pairs(area, prefix, line):
    """Old-form -> new-form literal replacements, sorted longest-first so a
    shorter form can never clobber a longer one's territory."""
    ten = area + prefix + line
    pairs = {
        f"tel:+1{OLD_TEN}":                       f"tel:+1{ten}",
        f"tel:{OLD_TEN}":                         f"tel:{ten}",
        f"+1-{OLD_AREA}-{OLD_PREFIX}-{OLD_LINE}": f"+1-{area}-{prefix}-{line}",  # JSON-LD telephone
        f"+1{OLD_TEN}":                           f"+1{ten}",
        f"({OLD_AREA})&nbsp;{OLD_PREFIX}-{OLD_LINE}": f"({area})&nbsp;{prefix}-{line}",  # nbsp display
        f"({OLD_AREA}) {OLD_PREFIX}-{OLD_LINE}":  f"({area}) {prefix}-{line}",           # plain display
        f"{OLD_AREA}-{OLD_PREFIX}-{OLD_LINE}":    f"{area}-{prefix}-{line}",
        OLD_TEN:                                  ten,
    }
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


def swap_generic(text, pairs):
    """Apply the full form-map to a page/builder; return (new_text, count)."""
    count = 0
    for old, new in pairs:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n
    return text, count


def swap_anchored(text, area, prefix, line):
    """api/index.py: only swap the phone inside each verified WWS anchor."""
    count = 0
    hits = []
    new_disp = f"({area}) {prefix}-{line}"
    for anchor in API_ANCHORS:
        if anchor in text:
            replaced = anchor.replace(f"({OLD_AREA}) {OLD_PREFIX}-{OLD_LINE}", new_disp)
            text = text.replace(anchor, replaced)
            count += 1
            hits.append(anchor[:60])
        else:
            hits.append("!! NOT FOUND: " + anchor[:48])
    return text, count, hits


def main():
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("--")]
    if not positional:
        sys.exit(__doc__)
    unknown = flags - {"--dry-run", "--commit", "--regen"}
    if unknown:
        sys.exit(f"ERROR: unknown flag(s): {', '.join(sorted(unknown))}")

    commit = "--commit" in flags
    regen = "--regen" in flags
    mode = "COMMIT (writing files)" if commit else "DRY-RUN (no files written)"

    area, prefix, line = parse_number(positional[0])
    pairs = build_pairs(area, prefix, line)

    print("=" * 68)
    print(f"  WWS PHONE SWAP  ({OLD_AREA}) {OLD_PREFIX}-{OLD_LINE}  ->  ({area}) {prefix}-{line}")
    print(f"  MODE: {mode}")
    print(f"  REPO: {REPO}")
    if area != "954":
        print(f"  NOTE: new area code is {area}, not 954 (decision preferred 954).")
    print("=" * 68)

    total = 0
    touched = 0

    def process(rel, swapper):
        nonlocal total, touched
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            print(f"  MISSING   {rel}   (skipped)")
            return
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        result = swapper(text)
        new_text, n = result[0], result[1]
        extra = result[2] if len(result) > 2 else None
        total += n
        if n and new_text != text:
            touched += 1
            print(f"  [{n:>3}]     {rel}")
            if extra:
                for h in extra:
                    print(f"             - {h}")
            if commit:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)
        else:
            print(f"  [  0]     {rel}   (no occurrences)")

    print("\nWWS PAGES (direct swap, all phone forms):")
    for rel in HTML_FILES:
        process(rel, lambda t: swap_generic(t, pairs))

    print("\nWWS BUILDERS (swap phone constant -> REGENERATE outputs, do NOT hand-edit generated files):")
    for rel in BUILDER_FILES:
        process(rel, lambda t: swap_generic(t, pairs))

    print("\napi/index.py (context-anchored — ONLY the 3 verified WWS strings):")
    process(API_FILE, lambda t: swap_anchored(t, area, prefix, line))
    print("  EXCLUDED (kept at 475-8615 by design): CC_SIGNATURE [Collab],")
    print("           doc_receipt() invoice [shared billing], _upload_email_html() 'Lot' [Casa Del Monte].")

    print("\n" + "=" * 68)
    print(f"  {total} occurrences across {touched} file(s) would change" if not commit
          else f"  {total} occurrences across {touched} file(s) changed")
    print("  NOT TOUCHED: apex site, /blog, wwslgc/design/*, assets/presentations/*,")
    print("               previews/*, projects/*, wake/*, lagala/*, and all")
    print("               generated outputs (wwslgc/guides/*.html, wwslgc/collateral/*.pdf).")
    print("=" * 68)

    if commit:
        print("\nNEXT — regenerate builder outputs (never hand-edit generated files):")
        print(f"    cd {REPO}")
        print("    python _wws_blog_builder.py      # regenerates wwslgc/guides/*.html")
        print("    python _build_marketing.py       # regenerates wwslgc/collateral/*.pdf")
        if regen:
            for b in ("_wws_blog_builder.py", "_build_marketing.py"):
                print(f"\n--regen: running {b} ...")
                try:
                    subprocess.run([sys.executable, b], cwd=REPO, check=True)
                except Exception as exc:  # noqa: BLE001
                    print(f"    WARNING: {b} failed to run: {exc}")
        else:
            print("\n    (or re-run this script with --regen to run both builders now)")
        print("\nThen review the diff and commit. To undo: git checkout -- <files>")
    else:
        print("\nThis was a DRY-RUN. Re-run with --commit once the new number exists.")


if __name__ == "__main__":
    main()

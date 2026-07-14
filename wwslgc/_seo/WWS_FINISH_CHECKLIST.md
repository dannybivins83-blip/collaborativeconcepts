# WWS Lane — Finish Checklist

**Status: the WWS lane is complete except for ONE owner-gated input.**

The entire WWS surface — landing page, money/service page, 8 city pages, client
portal, 44 compliance guides, 4 print collateral pieces, JSON-LD, and the WWS
strings in the backend — is built, live, and internally consistent. The only
thing standing between "done" and "shipped on the new number" is a phone number
that **does not exist yet**.

---

## ✅ DONE

- **Decision locked & verified** (`GOOGLE_BUSINESS_PROFILE.md`, Danny 2026-07-08):
  (561) 475-8615 = Collaborative Concept's umbrella number; La Gala / WWS gets a
  NEW dedicated number (prefer **954**, Deerfield Beach base). Collab surfaces
  keep 475-8615.
- **Full scope mapped** — every 475-8615 occurrence classified IN-scope (swap)
  vs OUT-of-scope (keep). See `WWS_PHONE_SWAP_MANIFEST.md`.
  - IN-scope: **14 files · 137 occurrences** (11 WWS pages, 2 WWS builders,
    3 anchored WWS strings in `api/index.py`).
  - OUT-of-scope confirmed excluded: apex, /blog, `wwslgc/design/*`,
    presentations, previews, projects, wake, Casa Del Monte / `lagala/*`, the
    other 3 `api/index.py` strings, and all generated outputs.
- **One-command swap tool built & tested** — `apply_wws_phone.py`
  (parameterized, dry-run by default, reversible, operates on an allowlist only).
- **Dry-run verified against the real tree** — targets exactly the 14 in-scope
  files (137 occurrences), touches **zero** Collab / apex / blog / design /
  presentation / portal-shared files, and writes nothing in dry-run mode.
- **GBP draft, citations, and outreach** prepared and waiting on the same number.

---

## 🔴 THE ONE REMAINING GATE

**A new, dedicated La Gala Construction / WWS phone number must be obtained.**
Everything downstream is automated and waiting on this single value.

Per the decision doc, the intended path is a **free Google Voice 954 number** on
a fresh Google account under Danny's real name (the legacy "Kyle Morse" identity
on `dannybivins83@gmail.com` blocks Google's ID check — that is why the first
attempt failed). The number cannot be provisioned by an agent; it requires
Danny's ID verification.

### The single owner action
> **Danny: obtain the new 954 number (free Google Voice on the clean account),
> then run — once — from the repo root:**
>
> ```
> python wwslgc/_seo/apply_wws_phone.py "(954) XXX-XXXX" --commit --regen
> ```
>
> That swaps all 137 WWS occurrences, regenerates the 44 guides and 4 collateral
> PDFs, and leaves Collab's 475-8615 untouched. Then review the diff, commit,
> and push (Vercel auto-deploys). Enter the same number in the GBP draft.

*(Reversible at any point: `git checkout -- <files>`, or re-run the tool with the
old number.)*

---

## After the swap (all automated by the one command / follow-ups)
1. `--commit` writes the 14 files; `--regen` re-runs both builders.
2. Review `git diff`, commit, push → Vercel deploys.
3. Enter the new number in `GOOGLE_BUSINESS_PROFILE.md` → publish the GBP.
4. Update the NAP blocks in `CITATIONS.md` to the new number, then fire citations.
5. (Optional) Confirm whether the WWS portal invoice + upload emails
   (`api/index.py` lines ~2747 / ~3745) should also move — see manifest.

**Bottom line: nothing else is blocking WWS. Get the number, run one command.**

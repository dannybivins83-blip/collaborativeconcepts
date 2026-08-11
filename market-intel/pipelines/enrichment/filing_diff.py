"""Filing diff — what changed between a filing and its prior comparable.

Comparable = same registrant, same form, immediately preceding by filed_at.
Comparing a 10-Q to a 10-K would report the entire document as "changed", which
is noise; the whole value here is that the diff is small enough to read.

Sentence-level rather than word-level: "we now face additional export
restrictions" is the unit an analyst acts on, not a token delta.
"""
import difflib
import re

from packages.shared.timeutil import iso, now_utc

MIN_SENTENCE = 40          # ignore fragments and headings
SIMILAR_ENOUGH = 0.82      # above this a pair is "modified", not add+remove


def sentences(text: str) -> list:
    parts = re.split(r"(?<=[.;:])\s+(?=[A-Z(])", re.sub(r"\s+", " ", text or ""))
    return [p.strip() for p in parts if len(p.strip()) >= MIN_SENTENCE]


def diff_sections(current_text, previous_text):
    """[(change_type, excerpt, similarity)] for one section pair."""
    cur, prev = sentences(current_text), sentences(previous_text)
    prev_set = set(prev)
    cur_set = set(cur)
    added = [s for s in cur if s not in prev_set]
    removed = [s for s in prev if s not in cur_set]

    out, matched_removed = [], set()
    for a in added:
        best, best_ratio = None, 0.0
        for i, r in enumerate(removed):
            if i in matched_removed:
                continue
            ratio = difflib.SequenceMatcher(None, a, r).ratio()
            if ratio > best_ratio:
                best, best_ratio, best_i = r, ratio, i
        if best is not None and best_ratio >= SIMILAR_ENOUGH:
            matched_removed.add(best_i)
            out.append(("modified", a, round(best_ratio, 4)))
        else:
            out.append(("added", a, None))
    for i, r in enumerate(removed):
        if i not in matched_removed:
            out.append(("removed", r, None))
    return out


def previous_comparable(db, filing):
    return db.one(
        "SELECT * FROM sec_filings WHERE entity_id=? AND form=? AND filed_at < ? "
        "ORDER BY filed_at DESC LIMIT 1",
        (filing["entity_id"], filing["form"], filing["filed_at"]))


def diff_filing(db, filing_id, sections=("item_1a_risk_factors", "item_1_business",
                                         "item_7_mdna")):
    """Diff one filing against its prior comparable; persist to filing_diffs."""
    filing = db.one("SELECT * FROM sec_filings WHERE id=?", (filing_id,))
    if not filing:
        return {"status": "unknown_filing", "written": 0}
    prev = previous_comparable(db, filing)
    if not prev:
        return {"status": "no_prior_comparable", "written": 0}

    now, written = iso(now_utc()), 0
    for section in sections:
        c = db.one("SELECT body FROM filing_sections WHERE filing_id=? AND section=? "
                   "ORDER BY ordinal LIMIT 1", (filing["id"], section))
        p = db.one("SELECT body FROM filing_sections WHERE filing_id=? AND section=? "
                   "ORDER BY ordinal LIMIT 1", (prev["id"], section))
        if not c or not p:
            continue
        for change_type, excerpt, similarity in diff_sections(c["body"], p["body"]):
            db.insert_ignore("filing_diffs", {
                "entity_id": filing["entity_id"], "section": section,
                "current_filing_id": filing["id"], "previous_filing_id": prev["id"],
                "change_type": change_type, "excerpt": excerpt[:2000],
                "similarity": similarity, "created_at": now,
            }, ["current_filing_id", "previous_filing_id", "section", "change_type",
                "excerpt"])
            written += 1
    db.commit()
    return {"status": "ok", "written": written, "previous_filing_id": prev["id"]}


def diffs_for_entity(db, entity_id, limit=50):
    return db.query(
        "SELECT fd.*, f.form, f.filed_at FROM filing_diffs fd "
        "JOIN sec_filings f ON f.id = fd.current_filing_id "
        "WHERE fd.entity_id=? ORDER BY f.filed_at DESC, fd.section LIMIT ?",
        (entity_id, limit))

"""Filing document collector: fetch the primary document, strip it to text,
split it into the canonical Items, and store sections for tagging + diffing.

Section extraction is regex-over-plain-text rather than DOM-walking because
EDGAR HTML is thirty years of inconsistent generators; the Item headings are
the one reliable landmark. Anything not confidently matched is stored as
`document` rather than mislabeled — a risk-factor diff built on a wrongly
sliced section is worse than no diff.
"""
import re
from html.parser import HTMLParser

from collectors.common.base import Collector
from packages.shared.provenance import source_id
from packages.shared.timeutil import iso, now_utc

# Canonical 10-K / 10-Q items we care about, in document order.
SECTION_PATTERNS = [
    ("item_1_business",       r"item\s*1\s*[.\-–—:]?\s*business"),
    ("item_1a_risk_factors",  r"item\s*1a\s*[.\-–—:]?\s*risk\s*factors"),
    ("item_2_properties",     r"item\s*2\s*[.\-–—:]?\s*propert"),
    ("item_7_mdna",           r"item\s*7\s*[.\-–—:]?\s*management.s\s*discussion"),
    ("item_7a_market_risk",   r"item\s*7a\s*[.\-–—:]?\s*quantitative"),
    ("item_8_financials",     r"item\s*8\s*[.\-–—:]?\s*financial\s*statements"),
]


class _TextExtractor(HTMLParser):
    """HTML -> readable text. Drops script/style, keeps block boundaries."""
    SKIP = {"script", "style", "head", "meta", "link"}
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data)

    def text(self):
        raw = " ".join("".join(self.parts).split(" "))
        raw = re.sub(r"[ \t\xa0]+", " ", raw)
        return re.sub(r"\n\s*\n+", "\n\n", raw).strip()


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html or "")
    return p.text()


def split_sections(text: str) -> list:
    """[(section_key, heading, body)] — unmatched documents return one
    `document` section rather than a wrong guess."""
    if not text:
        return []
    marks = []
    for key, pattern in SECTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            marks.append((m.start(), key, text[m.start():m.end()].strip()))
    if not marks:
        return [("document", "Document", text)]
    marks.sort()
    # A 10-K repeats Item headings in its table of contents; the real section is
    # the LAST occurrence of each, and it must have substantive body text.
    last = {}
    for pos, key, heading in marks:
        last[key] = (pos, heading)
    ordered = sorted(((pos, key, heading) for key, (pos, heading) in last.items()))
    out = []
    for i, (pos, key, heading) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else len(text)
        body = text[pos:end].strip()
        if len(body) < 200:      # a TOC line, not a section
            continue
        out.append((key, heading, body))
    return out or [("document", "Document", text)]


class FilingDocumentCollector(Collector):
    """Fetches primary documents for filings already in sec_filings."""
    source_id = "sec"
    name = "sec.filing_documents"
    kind = "filing_document"

    def __init__(self, db, transport, entity_id=None, forms=("10-K", "10-Q"), limit=10):
        super().__init__(db, transport)
        self.entity_id = entity_id
        self.forms = tuple(forms)
        self.limit = limit

    def _pending(self):
        placeholders = ",".join("?" for _ in self.forms)
        sql = (f"SELECT id, entity_id, cik, accession_no, form, filed_at, period_end, "
               f"doc_url FROM sec_filings WHERE doc_url IS NOT NULL "
               f"AND form IN ({placeholders})")
        params = list(self.forms)
        if self.entity_id:
            sql += " AND entity_id = ?"
            params.append(self.entity_id)
        sql += " ORDER BY filed_at DESC LIMIT ?"
        params.append(self.limit)
        return self.db.query(sql, tuple(params))

    def fetch(self):
        for f in self._pending():
            html = self.transport.get(f["doc_url"]).decode("utf-8", errors="replace")
            yield {
                "source_record_id": source_id("sec", "filing_document", f["cik"],
                                              f["accession_no"]),
                "kind": "filing_document", "url": f["doc_url"],
                "observed_at": f["filed_at"],
                "effective_at": f.get("period_end") or f["filed_at"],
                "payload": {"filing_id": f["id"], "entity_id": f["entity_id"],
                            "form": f["form"], "filed_at": f["filed_at"],
                            "period_end": f.get("period_end"), "html": html},
            }

    def validate(self, doc):
        html = (doc.get("payload") or {}).get("html") or ""
        return ["document body empty"] if len(html) < 200 else []

    def normalize(self, doc, source_record_id):
        p = doc["payload"]
        text = html_to_text(p["html"])
        rows = []
        for ordinal, (key, heading, body) in enumerate(split_sections(text)):
            rows.append({
                "filing_id": p["filing_id"], "entity_id": p["entity_id"],
                "section": key, "heading": heading, "body": body,
                "body_hash": source_id("sec", "section", p["filing_id"], key,
                                       str(len(body))),
                "ordinal": ordinal, "source_record_id": source_record_id,
                "observed_at": p["filed_at"], "effective_at": p.get("period_end"),
            })
        return rows

    def persist_normalized(self, rows):
        for r in rows:
            self.db.upsert("filing_sections", {
                "filing_id": r["filing_id"], "section": r["section"],
                "heading": r["heading"], "body": r["body"],
                "body_hash": r["body_hash"], "ordinal": r["ordinal"],
            }, ["filing_id", "section", "ordinal"])
        self._last_rows = rows
        return len(rows)

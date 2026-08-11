"""SEC EDGAR collectors — the platform's first real source.

Endpoints (public, no key, no paywall, no auth to circumvent):
  https://www.sec.gov/files/company_tickers.json        ticker -> CIK map
  https://data.sec.gov/submissions/CIK##########.json   filing history
  https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json   XBRL facts

SEC's access policy requires a declared User-Agent with a contact address and
asks for <= 10 requests/second; `HttpTransport` enforces both. Nothing here
scrapes behind a login or ignores robots — EDGAR publishes these files for
programmatic use.

Offline: set MI_OFFLINE=1 and the identical code path reads recorded fixtures,
so the pipeline is provable without network access.
"""
import json

from collectors.common.base import Collector
from packages.database import repositories as repo
from packages.entity_resolution import canonical_entity_id
from packages.shared.provenance import source_id
from packages.shared.timeutil import iso, now_utc, parse_date

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

SOURCE = {
    "id": "sec",
    "name": "SEC EDGAR",
    "category": "filings",
    "official_url": "https://www.sec.gov/edgar",
    "access_method": "http-json",
    "auth_required": 0,
    "license_class": "PUBLIC",
    "rate_limit": "10 req/s (declared User-Agent required)",
    "update_frequency": "continuous",
    "historical_depth": "1993-present",
    "enabled": 1,
    "notes": "US government work, not subject to copyright. Redistribution of "
             "derived analytics is permitted; see docs/DATA_LICENSING.md.",
}

# Concepts pulled from companyfacts for the fundamentals slice. Deliberately
# small: each one is mapped, tested and displayed, rather than dumping the
# whole taxonomy into a table nobody can interpret.
CONCEPTS = {
    "us-gaap": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "NetIncomeLoss", "OperatingIncomeLoss", "GrossProfit",
                "ResearchAndDevelopmentExpense", "Assets", "Liabilities",
                "StockholdersEquity", "CashAndCashEquivalentsAtCarryingValue",
                "EarningsPerShareDiluted"],
}
# Concepts that mean the same thing; the first present wins when charting.
REVENUE_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]


def cik10(cik) -> str:
    return str(cik).strip().lstrip("0").zfill(10)


def register(db):
    return repo.register_source(db, **SOURCE)


class TickerMapCollector(Collector):
    """company_tickers.json -> PUBLIC_COMPANY entities + securities + identifiers.

    This is the security master. Every later collector resolves against the
    identifiers it writes, so it runs first.
    """
    source_id = "sec"
    name = "sec.ticker_map"
    kind = "ticker_map"

    def __init__(self, db, transport, limit=None, tickers=None):
        super().__init__(db, transport)
        self.limit = limit
        self.only = {t.upper() for t in tickers} if tickers else None

    def fetch(self):
        payload = self.transport.get_json(SEC_TICKERS_URL)
        yield {"source_record_id": source_id("sec", "ticker_map", "all"),
               "kind": "ticker_map", "url": SEC_TICKERS_URL,
               "observed_at": iso(now_utc()), "payload": payload}

    def validate(self, doc):
        payload = doc.get("payload")
        if not isinstance(payload, dict) or not payload:
            return ["ticker map empty or not an object"]
        # Validate against the first REAL row: payloads can carry scalar metadata
        # keys alongside the numbered rows, and indexing blindly into values()
        # picks up whatever happens to come first.
        sample = next((v for v in payload.values() if isinstance(v, dict)), None)
        if sample is None:
            return ["ticker map contains no row objects"]
        return [f"ticker map row missing {k}"
                for k in ("cik_str", "ticker", "title") if k not in sample]

    def normalize(self, doc, source_record_id):
        rows, seen = [], 0
        for item in doc["payload"].values():
            if not isinstance(item, dict) or not item.get("ticker"):
                continue
            ticker = str(item["ticker"]).upper()
            if self.only and ticker not in self.only:
                continue
            cik = cik10(item["cik_str"])
            rows.append({
                "entity_id": canonical_entity_id("cik", cik),
                "cik": cik, "ticker": ticker, "name": item.get("title") or ticker,
                "exchange": item.get("exchange"),
                "source_record_id": source_record_id,
            })
            seen += 1
            if self.limit and seen >= self.limit:
                break
        return rows

    def persist_normalized(self, rows):
        n = 0
        for r in rows:
            repo.upsert_entity(self.db, entity_id=r["entity_id"], type="PUBLIC_COMPANY",
                               name=r["name"])
            repo.add_alias(self.db, r["entity_id"], r["name"], "name", r["source_record_id"])
            repo.add_alias(self.db, r["entity_id"], r["ticker"], "abbrev",
                           r["source_record_id"])
            repo.add_identifier(self.db, r["entity_id"], "cik", r["cik"],
                                r["source_record_id"])
            repo.add_identifier(self.db, r["entity_id"], "ticker", r["ticker"],
                                r["source_record_id"])
            repo.upsert_security(self.db, security_id="sec_" + source_id("sec", "security",
                                                                         r["ticker"])[:20],
                                 entity_id=r["entity_id"], ticker=r["ticker"],
                                 exchange=r["exchange"])
            n += 1
        return n

    def health_check(self):
        try:
            payload = self.transport.get_json(SEC_TICKERS_URL)
            return {"source": "sec", "ok": bool(payload), "rows": len(payload or {}),
                    "checked_at": iso(now_utc())}
        except Exception as e:
            return {"source": "sec", "ok": False, "error": str(e),
                    "checked_at": iso(now_utc())}


class SubmissionsCollector(Collector):
    """Filing history for one CIK -> sec_filings (+ former-name aliases)."""
    source_id = "sec"
    name = "sec.submissions"
    kind = "submissions"

    def __init__(self, db, transport, cik, forms=None, since=None):
        super().__init__(db, transport)
        self.cik = cik10(cik)
        self.forms = {f.upper() for f in forms} if forms else None
        self.since = since   # 'YYYY-MM-DD' incremental checkpoint

    def fetch(self):
        url = SEC_SUBMISSIONS_URL.format(cik10=self.cik)
        payload = self.transport.get_json(url)
        yield {"source_record_id": source_id("sec", "submissions", self.cik),
               "kind": "submissions", "url": url,
               "observed_at": iso(now_utc()), "payload": payload}

    def validate(self, doc):
        p = doc.get("payload") or {}
        problems = []
        if not p.get("cik"):
            problems.append("submissions missing cik")
        if "filings" not in p or "recent" not in (p.get("filings") or {}):
            problems.append("submissions missing filings.recent")
        return problems

    def normalize(self, doc, source_record_id):
        p = doc["payload"]
        recent = p["filings"]["recent"]
        entity_id = canonical_entity_id("cik", cik10(p["cik"]))
        # `recent` is column-oriented: parallel arrays, one index per filing.
        n = len(recent.get("accessionNumber", []))
        col = lambda k, i: (recent.get(k) or [None] * n)[i] if i < n else None
        rows = []
        for i in range(n):
            form = (col("form", i) or "").upper()
            filed = col("filingDate", i)
            if self.forms and form not in self.forms:
                continue
            if self.since and filed and filed < self.since:
                continue
            accession = col("accessionNumber", i)
            if not accession or not filed:
                continue
            doc_url = None
            if col("primaryDocument", i):
                doc_url = ("https://www.sec.gov/Archives/edgar/data/"
                           f"{int(p['cik'])}/{accession.replace('-', '')}/"
                           f"{col('primaryDocument', i)}")
            rows.append({
                "id": source_id("sec", "filing", cik10(p["cik"]), accession),
                "entity_id": entity_id,
                "cik": cik10(p["cik"]),
                "accession_no": accession,
                "form": form,
                "filed_at": filed,
                "period_end": col("reportDate", i) or None,
                "primary_doc": col("primaryDocument", i),
                "doc_url": doc_url,
                "items": col("items", i) or None,
                "source_record_id": source_record_id,
                "ingested_at": iso(now_utc()),
            })
        self._entity = {"entity_id": entity_id, "name": p.get("name"),
                        "tickers": p.get("tickers") or [],
                        "former": [f.get("name") for f in (p.get("formerNames") or [])],
                        "source_record_id": source_record_id}
        return rows

    def persist_normalized(self, rows):
        e = getattr(self, "_entity", None)
        if e:
            repo.upsert_entity(self.db, entity_id=e["entity_id"], type="PUBLIC_COMPANY",
                               name=e["name"] or e["entity_id"])
            for former in e["former"]:
                repo.add_alias(self.db, e["entity_id"], former, "former_name",
                               e["source_record_id"], confidence=0.9)
            for t in e["tickers"]:
                repo.add_identifier(self.db, e["entity_id"], "ticker", t,
                                    e["source_record_id"])
        for r in rows:
            repo.upsert_filing(self.db, r)
        return len(rows)


class CompanyFactsCollector(Collector):
    """XBRL companyfacts -> filing_facts (typed, period-aware, deduplicated)."""
    source_id = "sec"
    name = "sec.company_facts"
    kind = "facts"

    def __init__(self, db, transport, cik, concepts=None):
        super().__init__(db, transport)
        self.cik = cik10(cik)
        self.concepts = concepts or CONCEPTS

    def fetch(self):
        url = SEC_FACTS_URL.format(cik10=self.cik)
        payload = self.transport.get_json(url)
        yield {"source_record_id": source_id("sec", "facts", self.cik),
               "kind": "facts", "url": url,
               "observed_at": iso(now_utc()), "payload": payload}

    def validate(self, doc):
        p = doc.get("payload") or {}
        if not p.get("facts"):
            return ["companyfacts missing 'facts'"]
        return []

    def normalize(self, doc, source_record_id):
        p = doc["payload"]
        entity_id = canonical_entity_id("cik", cik10(p.get("cik", self.cik)))
        out = []
        for taxonomy, concepts in (p.get("facts") or {}).items():
            wanted = self.concepts.get(taxonomy)
            for concept, body in (concepts or {}).items():
                if wanted and concept not in wanted:
                    continue
                for unit, observations in (body.get("units") or {}).items():
                    for o in observations:
                        if o.get("val") is None or not o.get("end"):
                            continue
                        out.append({
                            "entity_id": entity_id,
                            "filing_id": None,
                            "taxonomy": taxonomy,
                            "concept": concept,
                            "unit": unit,
                            "value": float(o["val"]),
                            "period_start": o.get("start"),
                            "period_end": o["end"],
                            "fiscal_year": o.get("fy"),
                            "fiscal_period": o.get("fp"),
                            "form": o.get("form"),
                            "filed_at": o.get("filed"),
                            "source_record_id": source_record_id,
                            "ingested_at": iso(now_utc()),
                        })
        return out

    def persist_normalized(self, rows):
        for r in rows:
            repo.upsert_fact(self.db, r)
        return len(rows)

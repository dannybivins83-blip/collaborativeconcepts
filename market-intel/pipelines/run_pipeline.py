#!/usr/bin/env python3
"""End-to-end pipeline: the milestone this repository has to prove.

    DATA SOURCE -> RAW RECORD -> NORMALIZATION -> ENTITY RESOLUTION
      -> TAGGING -> DATABASE -> (API -> FRONTEND)

Run offline against recorded fixtures (no network required):
    MI_OFFLINE=1 python3 pipelines/run_pipeline.py --tickers NVDA

Run live against SEC EDGAR (needs outbound HTTPS and a contact UA):
    MI_USER_AGENT='MarketIntel/1.0 (you@example.com)' \
      python3 pipelines/run_pipeline.py --tickers NVDA AAPL

Every stage reports counts; nothing is silently skipped.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.common.transport import FixtureTransport, default_transport  # noqa: E402
from collectors.sec import edgar                                             # noqa: E402
from collectors.sec.documents import FilingDocumentCollector                 # noqa: E402
from packages import database                                                # noqa: E402
from packages.entity_resolution import EntityResolver, canonical_entity_id   # noqa: E402
from packages.scoring_engine import persist_score, register_model, score_entity  # noqa: E402
from packages.signal_engine import (REGISTRY, compute_for_entities, persist,  # noqa: E402
                                    sync_definitions)
from packages.tag_engine import Tagger, seed_taxonomy                        # noqa: E402
from pipelines.enrichment.filing_diff import diff_filing                     # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "sec"

# URL -> fixture file. The collector builds these URLs for real; offline mode
# only swaps the bytes, so the code path under test is the production one.
FIXTURE_MAP = {
    edgar.SEC_TICKERS_URL: "company_tickers.json",
    edgar.SEC_SUBMISSIONS_URL.format(cik10="0001045810"): "submissions_1045810.json",
    edgar.SEC_FACTS_URL.format(cik10="0001045810"): "companyfacts_1045810.json",
    "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260125.htm":
        "nvda-20260125.htm",
    "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/nvda-20260426.htm":
        "nvda-20260426.htm",
    "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000180/nvda-20251026.htm":
        "nvda-20251026.htm",
}


def make_transport(offline):
    if offline:
        return FixtureTransport(FIXTURES, FIXTURE_MAP)
    return default_transport(FIXTURES, FIXTURE_MAP)


def run(db, tickers, offline=True, verbose=True):
    report = {"offline": offline, "stages": []}

    def stage(name, **kw):
        report["stages"].append(dict(name=name, **kw))
        if verbose:
            detail = " ".join(f"{k}={v}" for k, v in kw.items())
            print(f"  {name:26} {detail}")

    transport = make_transport(offline)
    if verbose:
        print(f"\n{'OFFLINE (fixtures)' if offline else 'LIVE (sec.gov)'} pipeline\n")

    # 0. registry + taxonomy + signal definitions
    edgar.register(db)
    stage("register_source", source="sec")
    stage("seed_taxonomy", tags=seed_taxonomy(db))
    stage("sync_signals", signals=sync_definitions(db))
    register_model(db)

    # 1. security master -> entities, aliases, identifiers, securities
    r = edgar.TickerMapCollector(db, transport, tickers=tickers).run()
    stage("collect.ticker_map", **r.as_dict())
    if r.status == "failed":
        return report

    resolver = EntityResolver(db)
    entity_ids = []
    for t in tickers:
        res = resolver.resolve(t, identifiers={"ticker": t}, entity_type="PUBLIC_COMPANY")
        stage("resolve", ticker=t, entity=res.entity_id, method=res.method,
              score=res.score, status=res.status)
        if res.resolved:
            entity_ids.append(res.entity_id)
    if not entity_ids:
        stage("abort", reason="no entities resolved")
        return report

    # 2. filings + XBRL facts per company
    for eid in entity_ids:
        cik = db.one("SELECT value FROM entity_identifiers WHERE entity_id=? AND "
                     "scheme='cik' LIMIT 1", (eid,))
        if not cik:
            continue
        rs = edgar.SubmissionsCollector(db, transport, cik["value"]).run()
        stage("collect.submissions", cik=cik["value"], **rs.as_dict())
        rf = edgar.CompanyFactsCollector(db, transport, cik["value"]).run()
        stage("collect.company_facts", cik=cik["value"], **rf.as_dict())

        # 3. primary documents -> sections
        rd = FilingDocumentCollector(db, transport, entity_id=eid, limit=5).run()
        stage("collect.documents", **rd.as_dict())

    # 4. tagging over extracted sections (temporal observations)
    tagger = Tagger(db)
    tagged, observations = 0, 0
    for sec in db.query(
            "SELECT fs.filing_id, fs.section, fs.body, f.entity_id, f.filed_at, "
            "f.period_end, sr.id AS source_record_id FROM filing_sections fs "
            "JOIN sec_filings f ON f.id = fs.filing_id "
            "JOIN source_records sr ON sr.id = ("
            "  SELECT id FROM source_records WHERE kind='filing_document' "
            "  AND source_url = f.doc_url LIMIT 1)"):
        hits = tagger.tag_document(
            entity_id=sec["entity_id"], text=sec["body"],
            source_record_id=sec["source_record_id"],
            observed_at=sec["filed_at"], effective_at=sec.get("period_end"))
        tagged += 1
        observations += len(hits)
    db.commit()
    stage("tagging", sections=tagged, tag_observations=observations)

    # 5. filing diffs (what changed vs the prior comparable filing)
    diffs = 0
    for f in db.query("SELECT id FROM sec_filings WHERE form IN ('10-K','10-Q') "
                      "ORDER BY filed_at DESC"):
        diffs += diff_filing(db, f["id"])["written"]
    stage("filing_diffs", changes=diffs)

    # 6. signals + composite score
    for sid in REGISTRY:
        good, errors = compute_for_entities(db, sid, entity_ids)
        persist(db, good)
        stage(f"signal.{sid}", observations=len(good), errors=len(errors))
    for eid in entity_ids:
        sc = score_entity(db, eid)
        persist_score(db, sc)
        stage("score", entity=eid, composite=sc["composite"], coverage=sc["coverage"])

    report["entities"] = entity_ids
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the end-to-end ingest pipeline")
    ap.add_argument("--tickers", nargs="+", default=["NVDA"])
    ap.add_argument("--db", default=os.environ.get("MI_DATABASE_URL",
                                                   "sqlite:///data/market-intel.db"))
    ap.add_argument("--live", action="store_true",
                    help="hit sec.gov instead of fixtures (needs MI_USER_AGENT)")
    ap.add_argument("--json", action="store_true", help="emit the run report as JSON")
    args = ap.parse_args(argv)

    offline = not args.live
    if offline:
        os.environ["MI_OFFLINE"] = "1"
    with database.connect(args.db) as db:
        report = run(db, [t.upper() for t in args.tickers], offline=offline,
                     verbose=not args.json)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        failed = [s for s in report["stages"] if s.get("status") == "failed"]
        print(f"\n{'FAILED: ' + failed[0].get('error', '') if failed else 'pipeline OK'}")
    return 1 if any(s.get("status") == "failed" for s in report["stages"]) else 0


if __name__ == "__main__":
    sys.exit(main())

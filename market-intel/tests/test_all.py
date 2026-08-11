"""Offline test suite — no network, no paid APIs, no installed dependencies.

    python3 tests/test_all.py            (or: make test)

Every external call is served by FixtureTransport, so these run identically in
CI, in a sandbox, and on a laptop with the wifi off.
"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.api import handlers                                          # noqa: E402
from collectors.common.transport import FixtureTransport, HttpTransport, RateLimiter  # noqa: E402
from collectors.sec import edgar                                       # noqa: E402
from collectors.sec.documents import html_to_text, split_sections      # noqa: E402
from packages import database                                          # noqa: E402
from packages.database.repositories import norm_name, slugify          # noqa: E402
from packages.entity_resolution import EntityResolver, canonical_entity_id  # noqa: E402
from packages.scoring_engine import score_entity                       # noqa: E402
from packages.shared.errors import CollectorError                      # noqa: E402
from packages.shared.provenance import content_hash, source_id         # noqa: E402
from packages.shared.timeutil import iso, parse_ts                     # noqa: E402
from packages.signal_engine import (percentiles, squash, zscores,      # noqa: E402
                                    _quarterly, pct_change)
from packages.tag_engine import Tagger, seed_taxonomy, tag_timeseries, top_tags  # noqa: E402
from pipelines.enrichment.filing_diff import diff_sections, sentences  # noqa: E402
from pipelines.run_pipeline import FIXTURE_MAP, FIXTURES, run          # noqa: E402


def mem_db():
    return database.connect("sqlite:///:memory:")


def fixture_transport():
    return FixtureTransport(FIXTURES, FIXTURE_MAP)


# --------------------------------------------------------------- primitives --
class SharedTests(unittest.TestCase):
    def test_source_id_is_stable_and_key_based(self):
        a = source_id("sec", "filing", "0001045810", "0001045810-26-000075")
        b = source_id("sec", "filing", "0001045810", "0001045810-26-000075")
        self.assertEqual(a, b)
        self.assertNotEqual(a, source_id("sec", "filing", "0001045810", "other"))

    def test_content_hash_detects_payload_change(self):
        self.assertEqual(content_hash({"a": 1}), content_hash({"a": 1}))
        self.assertNotEqual(content_hash({"a": 1}), content_hash({"a": 2}))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(ValueError):
            iso(datetime(2026, 1, 1))          # look-ahead bias starts here
        self.assertTrue(iso(datetime(2026, 1, 1, tzinfo=timezone.utc)).endswith("+00:00"))

    def test_parse_ts_accepts_z_suffix(self):
        self.assertEqual(parse_ts("2026-01-01T00:00:00Z").tzinfo, timezone.utc)

    def test_norm_name_strips_legal_suffixes(self):
        self.assertEqual(norm_name("Apple Inc."), norm_name("Apple"))
        self.assertEqual(norm_name("NVIDIA CORP"), "nvidia")
        self.assertEqual(norm_name("The Kroger Co."), "kroger")

    def test_slugify(self):
        self.assertEqual(slugify("Artificial Intelligence!"), "artificial-intelligence")


class DatabaseTests(unittest.TestCase):
    def test_migrate_creates_core_tables(self):
        with mem_db() as db:
            tables = {r["name"] for r in db.query(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ("entities", "source_records", "entity_tags", "signal_observations",
                  "relationships", "filing_facts", "scores"):
            self.assertIn(t, tables)

    def test_upsert_is_idempotent(self):
        with mem_db() as db:
            for _ in range(3):
                db.upsert("tags", {"id": "tag_x", "name": "X", "slug": "x",
                                   "created_at": "2026-01-01"}, ["id"])
            self.assertEqual(db.scalar("SELECT COUNT(*) FROM tags"), 1)

    def test_upsert_updates_changed_columns(self):
        with mem_db() as db:
            db.upsert("tags", {"id": "t", "name": "A", "slug": "a",
                               "created_at": "x"}, ["id"])
            db.upsert("tags", {"id": "t", "name": "B", "slug": "a",
                               "created_at": "x"}, ["id"])
            self.assertEqual(db.scalar("SELECT name FROM tags WHERE id='t'"), "B")


# --------------------------------------------------------------- transport ---
class TransportTests(unittest.TestCase):
    def test_fixture_transport_serves_recorded_payloads(self):
        t = fixture_transport()
        payload = t.get_json(edgar.SEC_TICKERS_URL)
        self.assertIn("0", payload)
        self.assertEqual(t.calls, [edgar.SEC_TICKERS_URL])

    def test_missing_fixture_raises_collector_error(self):
        with self.assertRaises(CollectorError):
            fixture_transport().get("https://example.com/nope")

    def test_http_transport_demands_contact_user_agent(self):
        with self.assertRaises(ValueError):
            HttpTransport("MarketIntel/1.0")          # SEC requires a contact
        HttpTransport("MarketIntel/1.0 (me@example.com)")

    def test_rate_limiter_enforces_minimum_interval(self):
        import time
        rl = RateLimiter(per_second=50)
        t0 = time.monotonic()
        rl.wait(); rl.wait()
        self.assertGreaterEqual(time.monotonic() - t0, 0.019)


# -------------------------------------------------------------- collectors ---
class TickerMapTests(unittest.TestCase):
    def test_ingests_entities_identifiers_and_securities(self):
        with mem_db() as db:
            edgar.register(db)
            r = edgar.TickerMapCollector(db, fixture_transport(), tickers=["NVDA"]).run()
            self.assertEqual(r.status, "ok")
            self.assertEqual(r.written, 1)
            eid = canonical_entity_id("cik", "0001045810")
            self.assertEqual(db.scalar("SELECT name FROM entities WHERE id=?", (eid,)),
                             "NVIDIA CORP")
            schemes = {r["scheme"] for r in db.query(
                "SELECT scheme FROM entity_identifiers WHERE entity_id=?", (eid,))}
            self.assertEqual(schemes, {"cik", "ticker"})
            self.assertEqual(db.scalar("SELECT ticker FROM securities LIMIT 1"), "NVDA")

    def test_validate_tolerates_scalar_metadata_keys(self):
        """REGRESSION: payloads can carry scalar meta keys next to row objects;
        validating against values()[0] blew up with a TypeError."""
        c = edgar.TickerMapCollector(None, None)
        doc = {"payload": {"_demo": True, "_note": "x",
                           "0": {"cik_str": 1, "ticker": "A", "title": "A Inc"}}}
        self.assertEqual(c.validate(doc), [])

    def test_validate_rejects_rowless_payload(self):
        c = edgar.TickerMapCollector(None, None)
        self.assertTrue(c.validate({"payload": {"_demo": True}}))
        self.assertTrue(c.validate({"payload": {}}))

    def test_rerun_does_not_duplicate(self):
        with mem_db() as db:
            edgar.register(db)
            for _ in range(2):
                edgar.TickerMapCollector(db, fixture_transport(), tickers=["NVDA"]).run()
            self.assertEqual(db.scalar("SELECT COUNT(*) FROM entities"), 1)
            self.assertEqual(db.scalar("SELECT COUNT(*) FROM source_records"), 1)


class SubmissionsTests(unittest.TestCase):
    def _ingest(self, db):
        edgar.register(db)
        edgar.TickerMapCollector(db, fixture_transport(), tickers=["NVDA"]).run()
        return edgar.SubmissionsCollector(db, fixture_transport(), "1045810").run()

    def test_parses_column_oriented_filings(self):
        with mem_db() as db:
            r = self._ingest(db)
            self.assertEqual(r.status, "ok")
            forms = [x["form"] for x in db.query(
                "SELECT form FROM sec_filings ORDER BY filed_at DESC")]
            self.assertEqual(forms, ["10-Q", "10-K", "8-K", "8-K", "10-Q"])

    def test_builds_archive_document_urls(self):
        with mem_db() as db:
            self._ingest(db)
            url = db.scalar("SELECT doc_url FROM sec_filings WHERE form='10-K'")
            self.assertTrue(url.startswith("https://www.sec.gov/Archives/edgar/data/1045810/"))
            self.assertNotIn("-", url.rsplit("/", 2)[1])   # accession stripped of dashes

    def test_records_former_names_as_aliases(self):
        with mem_db() as db:
            self._ingest(db)
            kinds = db.query("SELECT alias, kind FROM entity_aliases WHERE kind='former_name'")
            self.assertTrue(any("NVIDIA CORP/CA" == k["alias"] for k in kinds))

    def test_form_filter(self):
        with mem_db() as db:
            edgar.register(db)
            edgar.TickerMapCollector(db, fixture_transport(), tickers=["NVDA"]).run()
            edgar.SubmissionsCollector(db, fixture_transport(), "1045810",
                                       forms=["8-K"]).run()
            self.assertEqual(db.scalar("SELECT COUNT(*) FROM sec_filings"), 2)


class CompanyFactsTests(unittest.TestCase):
    def test_extracts_xbrl_facts_with_periods(self):
        with mem_db() as db:
            edgar.register(db)
            edgar.TickerMapCollector(db, fixture_transport(), tickers=["NVDA"]).run()
            r = edgar.CompanyFactsCollector(db, fixture_transport(), "1045810").run()
            self.assertEqual(r.status, "ok")
            self.assertGreater(r.written, 30)
            row = db.one("SELECT * FROM filing_facts WHERE concept='GrossProfit' "
                         "ORDER BY period_end DESC LIMIT 1")
            self.assertEqual(row["unit"], "USD")
            self.assertTrue(row["period_start"] < row["period_end"])
            self.assertIsNotNone(row["source_record_id"])   # provenance required


# ------------------------------------------------------------- documents ----
class DocumentTests(unittest.TestCase):
    def test_html_to_text_drops_script_and_style(self):
        text = html_to_text("<html><style>.a{color:red}</style><p>Hello</p>"
                            "<script>var x=1</script><p>World</p></html>")
        self.assertIn("Hello", text)
        self.assertNotIn("color:red", text)
        self.assertNotIn("var x", text)

    def test_split_sections_prefers_body_over_table_of_contents(self):
        body = "Risk language. " * 40
        text = ("TABLE OF CONTENTS Item 1A. Risk Factors ... "
                "Item 1A. Risk Factors " + body)
        sections = dict((k, v) for k, _h, v in
                        [(k, h, b) for k, h, b in split_sections(text)])
        self.assertIn("item_1a_risk_factors", sections)
        self.assertIn("Risk language", sections["item_1a_risk_factors"])

    def test_unmatched_document_is_labelled_document_not_guessed(self):
        out = split_sections("Some filing text with no item headings at all.")
        self.assertEqual(out[0][0], "document")


# ------------------------------------------------------ entity resolution ---
class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.db = mem_db()
        edgar.register(self.db)
        edgar.TickerMapCollector(self.db, fixture_transport()).run()
        self.r = EntityResolver(self.db)

    def tearDown(self):
        self.db.close()

    def test_identifier_match_is_authoritative(self):
        res = self.r.resolve("literally anything", identifiers={"ticker": "NVDA"})
        self.assertTrue(res.resolved)
        self.assertEqual(res.score, 1.0)
        self.assertEqual(res.method, "identifier:ticker")

    def test_cik_match_ignores_leading_zeros(self):
        self.assertTrue(self.r.resolve("x", identifiers={"cik": "1045810"}).resolved)
        self.assertTrue(self.r.resolve("x", identifiers={"cik": "0001045810"}).resolved)

    def test_alias_match_handles_legal_suffix(self):
        res = self.r.resolve("Apple", entity_type="PUBLIC_COMPANY")
        self.assertTrue(res.resolved)
        self.assertEqual(res.method, "alias")

    def test_close_but_distinct_name_is_not_auto_merged(self):
        res = self.r.resolve("Apple Hospitality", entity_type="PUBLIC_COMPANY")
        self.assertFalse(res.resolved)
        self.assertIn(res.status, ("ambiguous", "unresolved"))

    def test_ambiguous_match_is_queued_for_review(self):
        """Two different companies sharing a name must NEVER be merged silently —
        the resolver returns ambiguous and queues both for human review."""
        for i in (1, 2):
            eid = f"ent_dup{i}"
            self.db.upsert("entities", {"id": eid, "type": "PUBLIC_COMPANY",
                                        "name": f"Acme Holdings {i}", "slug": f"acme-{i}",
                                        "created_at": "x", "updated_at": "x"}, ["id"])
            self.db.insert_ignore("entity_aliases", {
                "entity_id": eid, "alias": "Acme", "alias_norm": "acme",
                "kind": "name", "confidence": 1.0}, ["entity_id", "alias_norm", "kind"])
        self.db.commit()
        res = self.r.resolve("Acme", entity_type="PUBLIC_COMPANY")
        self.assertEqual(res.status, "ambiguous")
        self.assertIsNone(res.entity_id)
        self.assertEqual(len(res.candidates), 2)
        self.assertTrue(self.r.pending_reviews())

    def test_unknown_mention_resolves_to_nothing(self):
        res = self.r.resolve("Zzzqqx Industries", entity_type="PUBLIC_COMPANY")
        self.assertFalse(res.resolved)
        self.assertIsNone(res.entity_id)

    def test_entity_id_is_deterministic(self):
        self.assertEqual(canonical_entity_id("cik", "1045810"),
                         canonical_entity_id("cik", "0001045810"))


# ------------------------------------------------------------- tag engine ---
class TagEngineTests(unittest.TestCase):
    def setUp(self):
        self.db = mem_db()
        seed_taxonomy(self.db)
        self.t = Tagger(self.db)
        # entity_tags has FKs to entities + source_records; satisfy them so the
        # test exercises tagging rather than referential integrity.
        self.db.upsert("entities", {"id": "e1", "type": "PUBLIC_COMPANY", "name": "E1",
                                    "slug": "e1", "created_at": "2026-01-01",
                                    "updated_at": "2026-01-01"}, ["id"])
        self.db.upsert("data_sources", {"id": "test", "name": "test", "category": "test"},
                       ["id"])
        for sid in ("src1", "s1", "s2"):
            self.db.upsert("source_records", {
                "id": sid, "source_id": "test", "kind": "doc", "payload": "{}",
                "content_hash": "h", "ingested_at": "2026-01-01"}, ["id"])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_seed_builds_hierarchy(self):
        parent = self.db.scalar("SELECT parent_id FROM tags WHERE slug='gpus'")
        self.assertEqual(parent, "tag_artificial-intelligence")

    def test_matches_alias_with_word_boundaries(self):
        hits = {h["tag_id"] for h in self.t.scan(
            "Our GPU products accelerate artificial intelligence workloads.")}
        self.assertIn("tag_gpus", hits)
        self.assertIn("tag_artificial-intelligence", hits)

    def test_does_not_match_inside_other_words(self):
        """'AI' must not fire on 'aim', 'said', 'chain'."""
        hits = {h["tag_id"] for h in self.t.scan(
            "We aim to said the chain, plaintiff air maintenance.")}
        self.assertNotIn("tag_artificial-intelligence", hits)

    def test_short_uppercase_alias_is_case_sensitive(self):
        self.assertFalse(any(h["tag_id"] == "tag_gpus"
                             for h in self.t.scan("the gpu-free legacy stack")))

    def test_case_variant_aliases_do_not_double_count(self):
        """REGRESSION: a tag's display name and a lowercase alias are the same
        surface form; compiling both counted every mention twice."""
        hits = self.t.scan("artificial intelligence " * 3)
        ai = next(h for h in hits if h["tag_id"] == "tag_artificial-intelligence")
        self.assertEqual(ai["frequency"], 3)

    def test_uppercase_alias_survives_deduplication(self):
        self.assertTrue(any(h["tag_id"] == "tag_gpus"
                            for h in self.t.scan("our GPU roadmap")))

    def test_frequency_and_evidence_are_recorded(self):
        hits = self.t.scan("data center " * 5 + " and more text here to dilute.")
        dc = next(h for h in hits if h["tag_id"] == "tag_data-centers")
        self.assertEqual(dc["frequency"], 5)
        self.assertIn("data center", dc["evidence"])
        self.assertGreater(dc["relevance"], 0)

    def test_observations_are_temporal_and_deduplicated(self):
        for _ in range(2):     # same document twice must not double-count
            self.t.tag_document(entity_id="e1", text="artificial intelligence " * 4,
                                source_record_id="src1", observed_at="2026-01-15")
        self.db.commit()
        self.assertEqual(self.db.scalar(
            "SELECT COUNT(*) FROM entity_tags WHERE entity_id='e1'"), 1)

    def test_timeseries_buckets_by_month(self):
        self.t.tag_document(entity_id="e1", text="artificial intelligence " * 3,
                            source_record_id="s1", observed_at="2026-01-15")
        self.t.tag_document(entity_id="e1", text="artificial intelligence " * 9,
                            source_record_id="s2", observed_at="2026-02-15")
        self.db.commit()
        series = tag_timeseries(self.db, "e1", "tag_artificial-intelligence")
        self.assertEqual([s["period"] for s in series], ["2026-01", "2026-02"])
        self.assertEqual([s["mentions"] for s in series], [3, 9])

    def test_top_tags_ranks_by_mentions(self):
        self.t.tag_document(entity_id="e1", text="GPU GPU GPU robotics",
                            source_record_id="s1", observed_at="2026-01-01")
        self.db.commit()
        self.assertEqual(top_tags(self.db, "e1")[0]["tag_id"], "tag_gpus")


# ---------------------------------------------------------- signal engine ---
class SignalMathTests(unittest.TestCase):
    def test_zscores_need_a_real_sample(self):
        self.assertEqual(zscores([1.0, 2.0]), [0.0, 0.0])       # too few
        self.assertEqual(zscores([5.0, 5.0, 5.0]), [0.0, 0.0, 0.0])  # zero variance

    def test_zscores_centre_the_distribution(self):
        z = zscores([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(sum(z), 0.0, places=9)
        self.assertLess(z[0], 0)
        self.assertGreater(z[-1], 0)

    def test_percentiles_and_squash_bounds(self):
        self.assertEqual(percentiles([1, 2, 3])[0], 0.0)
        self.assertTrue(0 < squash(0.5) < 1)
        self.assertEqual(squash(None), None)

    def test_pct_change_guards_zero_denominator(self):
        self.assertIsNone(pct_change(5, 0))
        self.assertEqual(pct_change(150, 100), 0.5)

    def test_quarterly_filter_excludes_annual_periods(self):
        """REGRESSION GUARD: mixing an FY total into a quarterly series
        manufactures a fake +300% acceleration."""
        rows = [{"period_start": "2025-01-01", "period_end": "2025-03-31"},
                {"period_start": "2025-01-01", "period_end": "2025-12-31"}]
        self.assertEqual(len(_quarterly(rows)), 1)


class SignalComputeTests(unittest.TestCase):
    def setUp(self):
        self.db = mem_db()
        self.report = run(self.db, ["NVDA"], offline=True, verbose=False)
        self.eid = self.report["entities"][0]

    def tearDown(self):
        self.db.close()

    def test_per_tag_signals_are_stored_separately(self):
        """REGRESSION: the unique key lacked subject_id, so nine per-tag
        topic_acceleration rows collapsed into one."""
        n = self.db.scalar("SELECT COUNT(*) FROM signal_observations "
                           "WHERE signal_id='topic_acceleration'")
        self.assertGreater(n, 3)
        subjects = self.db.query("SELECT DISTINCT subject_id FROM signal_observations "
                                 "WHERE signal_id='topic_acceleration'")
        self.assertEqual(len(subjects), n)

    def test_revenue_acceleration_is_computed_with_evidence(self):
        row = self.db.one("SELECT * FROM signal_observations "
                          "WHERE signal_id='revenue_acceleration'")
        self.assertIsNotNone(row)
        evidence = json.loads(row["evidence"])
        self.assertIn("growth_latest", evidence["detail"])

    def test_backtest_cutoff_uses_knowable_date_not_period_end(self):
        row = self.db.one("SELECT observed_at, ingested_at FROM signal_observations "
                          "WHERE signal_id='revenue_acceleration'")
        self.assertGreaterEqual(row["ingested_at"], row["observed_at"])

    def test_pipeline_is_idempotent(self):
        before = self.db.scalar("SELECT COUNT(*) FROM source_records")
        run(self.db, ["NVDA"], offline=True, verbose=False)
        self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM source_records"), before)


class ScoringTests(unittest.TestCase):
    def test_missing_categories_are_excluded_not_zeroed(self):
        with mem_db() as db:
            db.upsert("entities", {"id": "e1", "type": "PUBLIC_COMPANY", "name": "E",
                                   "slug": "e", "created_at": "x", "updated_at": "x"},
                      ["id"])
            s = score_entity(db, "e1")
            self.assertIsNone(s["composite"])       # no data -> no score, not 0
            self.assertEqual(s["coverage"], 0.0)

    def test_coverage_reported_with_score(self):
        with mem_db() as db:
            report = run(db, ["NVDA"], offline=True, verbose=False)
            s = score_entity(db, report["entities"][0])
            self.assertIsNotNone(s["composite"])
            self.assertGreater(s["coverage"], 0)
            self.assertLessEqual(s["composite"], 100)


# --------------------------------------------------------------- diffing ----
class FilingDiffTests(unittest.TestCase):
    def test_sentences_ignores_fragments(self):
        self.assertEqual(sentences("Short. Tiny."), [])

    def test_detects_added_and_removed_language(self):
        prev = ("We depend on a limited number of foundry partners for wafer supply. "
                "Competition in the semiconductor industry remains intense worldwide.")
        cur = ("We depend on a limited number of foundry partners for wafer supply. "
               "New export restrictions may materially reduce revenue in some regions.")
        kinds = {k for k, _e, _s in diff_sections(cur, prev)}
        self.assertIn("added", kinds)
        self.assertIn("removed", kinds)

    def test_rewording_is_modified_not_add_plus_remove(self):
        prev = "We depend on a limited number of foundry partners for our wafer supply."
        cur = "We depend on a limited number of foundry partners for wafer supply today."
        out = diff_sections(cur, prev)
        self.assertEqual([k for k, _e, _s in out], ["modified"])


# ------------------------------------------------------------------- API ----
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = mem_db()
        cls.report = run(cls.db, ["NVDA"], offline=True, verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def get(self, path, params=None):
        return handlers.dispatch(self.db, "GET", path, params or {})

    def test_health_reports_counts_and_demo_flag(self):
        status, body = self.get("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertGreater(body["counts"]["entities"], 0)
        self.assertTrue(body["data"]["contains_demo_data"])   # fixtures are labelled

    def test_stock_detail_and_unknown_ticker(self):
        status, body = self.get("/api/v1/stocks/NVDA")
        self.assertEqual(status, 200)
        self.assertEqual(body["security"]["ticker"], "NVDA")
        self.assertEqual(self.get("/api/v1/stocks/ZZZZ")[0], 404)

    def test_financials_returns_series_with_provenance(self):
        _s, body = self.get("/api/v1/stocks/NVDA/financials")
        self.assertTrue(body["concepts"])
        first = body["series"][body["concepts"][0]][0]
        self.assertIn("source_record_id", first)

    def test_tags_include_path_and_timeseries(self):
        _s, body = self.get("/api/v1/stocks/NVDA/tags")
        self.assertGreater(body["count"], 0)
        self.assertTrue(body["tags"][0]["path"])
        self.assertTrue(body["tags"][0]["timeseries"])

    def test_signals_evidence_is_parsed_json(self):
        _s, body = self.get("/api/v1/stocks/NVDA/signals")
        self.assertGreater(body["count"], 0)
        self.assertIsInstance(body["signals"][0]["evidence"], dict)

    def test_score_carries_the_not_backtested_disclaimer(self):
        _s, body = self.get("/api/v1/stocks/NVDA/score")
        self.assertIn("not been backtested", body["disclaimer"].lower()
                      .replace("not backtested", "not been backtested"))

    def test_filing_changes_grouped_by_section(self):
        _s, body = self.get("/api/v1/stocks/NVDA/filing-changes")
        self.assertGreater(body["total_changes"], 0)
        self.assertIn("item_1a_risk_factors", body["sections"])

    def test_themes_and_theme_detail(self):
        _s, body = self.get("/api/v1/themes")
        self.assertGreater(body["count"], 10)
        status, detail = self.get("/api/v1/themes/gpus")
        self.assertEqual(status, 200)
        self.assertEqual(detail["path"][:2], ["Technology", "Artificial Intelligence"])
        self.assertEqual(self.get("/api/v1/themes/not-a-theme")[0], 404)

    def test_search_matches_alias_and_requires_query(self):
        _s, body = self.get("/api/v1/search", {"q": "nvidia"})
        self.assertTrue(body["entities"])
        self.assertEqual(self.get("/api/v1/search", {"q": ""})[0], 400)

    def test_screener_filters_by_tag(self):
        _s, hit = self.get("/api/v1/screener", {"tag": "gpus"})
        _s2, miss = self.get("/api/v1/screener", {"tag": "glp-1"})
        self.assertGreater(hit["count"], 0)
        self.assertEqual(miss["count"], 0)

    def test_screener_rejects_unknown_filters(self):
        status, body = self.get("/api/v1/screener", {"pe_ratio": "10"})
        self.assertEqual(status, 400)
        self.assertIn("pe_ratio", body["error"])

    def test_data_health_lists_collectors(self):
        _s, body = self.get("/api/v1/data-health")
        self.assertTrue(body["collectors"])
        self.assertTrue(any(c["collector"] == "sec.ticker_map" for c in body["collectors"]))

    def test_unknown_route_is_404(self):
        self.assertEqual(self.get("/api/v1/nope")[0], 404)


# ------------------------------------------------------------ end-to-end ----
class PipelineE2ETests(unittest.TestCase):
    def test_full_slice_source_to_score(self):
        with mem_db() as db:
            report = run(db, ["NVDA"], offline=True, verbose=False)
            stages = {s["name"]: s for s in report["stages"]}
            self.assertEqual(stages["collect.ticker_map"]["status"], "ok")
            self.assertEqual(stages["collect.submissions"]["status"], "ok")
            self.assertEqual(stages["collect.company_facts"]["status"], "ok")
            self.assertEqual(stages["collect.documents"]["status"], "ok")
            self.assertGreater(stages["tagging"]["tag_observations"], 20)
            self.assertGreater(stages["filing_diffs"]["changes"], 0)
            self.assertIsNotNone(stages["score"]["composite"])
            # provenance: no derived row may exist without a raw record behind it
            orphans = db.scalar(
                "SELECT COUNT(*) FROM entity_tags et LEFT JOIN source_records sr "
                "ON sr.id = et.source_record_id WHERE sr.id IS NULL")
            self.assertEqual(orphans, 0)

    def test_collector_failure_is_isolated(self):
        """A dead source records a failed run; it does not raise into the caller
        or stop the other collectors."""
        with mem_db() as db:
            edgar.register(db)
            broken = FixtureTransport(FIXTURES, {})     # no fixtures at all
            r = edgar.TickerMapCollector(db, broken).run()
            self.assertEqual(r.status, "failed")
            self.assertIsNotNone(r.error)
            run_row = db.one("SELECT status, error FROM ingestion_runs WHERE id=?",
                             (r.run_id,))
            self.assertEqual(run_row["status"], "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)

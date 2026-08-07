"""
Offline test suite for the Search Console puller (api/gsc.py + _gsc_pull.py).

All network I/O is mocked — runs in any sandbox, no credentials needed.

Run:  python3 _gsc_tests.py
"""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, "api")
import gsc  # noqa: E402

sys.path.insert(0, ".")
import _gsc_pull  # noqa: E402


def api_rows(triples, dims=1):
    """Build API-shaped rows: (keys, clicks, impressions, position)."""
    out = []
    for keys, clicks, impr, pos in triples:
        keys = keys if isinstance(keys, list) else [keys]
        out.append({"keys": keys, "clicks": clicks, "impressions": impr,
                    "ctr": (clicks / impr) if impr else 0.0, "position": pos})
    return out


QUERY_ROWS = api_rows([
    ("roof anchor certification miami", 40, 800, 2.4),
    ("roof anchor certification", 12, 500, 6.8),      # striking distance
    ("walking working surfaces osha", 1, 300, 12.1),  # striking distance
    ("davit arm inspection", 0, 120, 18.0),           # striking distance
    ("lagala construction", 30, 90, 1.2),             # top-10, healthy CTR
    ("osha 1910.28 compliance", 2, 400, 3.1),         # top-10, poor CTR -> gap
])

PAGE_ROWS = api_rows([
    ("https://wwslgc.collaborativeconceptsfl.com/miami-roof-anchor-certification", 40, 800, 2.4),
    ("https://wwslgc.collaborativeconceptsfl.com/fort-lauderdale-roof-anchor-certification", 8, 200, 7.5),
    ("https://wwslgc.collaborativeconceptsfl.com/west-palm-beach-roof-anchor-certification", 5, 150, 9.1),
    ("https://wwslgc.collaborativeconceptsfl.com/", 20, 600, 4.0),   # no city
])


class RecordTests(unittest.TestCase):
    def test_to_records_names_dimensions(self):
        recs = gsc.to_records(QUERY_ROWS, ["query"])
        self.assertEqual(recs[0]["query"], "roof anchor certification miami")
        self.assertEqual(recs[0]["clicks"], 40)
        self.assertEqual(recs[0]["impressions"], 800)

    def test_multi_dimension(self):
        rows = api_rows([(["miami", "/page"], 3, 10, 5.0)])
        recs = gsc.to_records(rows, ["query", "page"])
        self.assertEqual(recs[0]["query"], "miami")
        self.assertEqual(recs[0]["page"], "/page")

    def test_missing_fields_default_to_zero(self):
        recs = gsc.to_records([{"keys": ["x"]}], ["query"])
        self.assertEqual(recs[0]["clicks"], 0)
        self.assertEqual(recs[0]["position"], 0.0)

    def test_totals_position_is_impression_weighted(self):
        recs = gsc.to_records(api_rows([("a", 0, 1000, 2.0), ("b", 0, 10, 50.0)]), ["query"])
        t = gsc.totals(recs)
        self.assertEqual(t["impressions"], 1010)
        # a plain mean would be 26.0; weighting keeps it near the high-volume row
        self.assertLess(t["position"], 3.0)

    def test_totals_ctr_and_empty(self):
        t = gsc.totals(gsc.to_records(QUERY_ROWS, ["query"]))
        self.assertAlmostEqual(t["ctr"], 85 / 2210, places=5)
        self.assertEqual(gsc.totals([])["clicks"], 0)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.q = gsc.to_records(QUERY_ROWS, ["query"])
        self.p = gsc.to_records(PAGE_ROWS, ["page"])

    def test_top_sorts_desc(self):
        self.assertEqual(gsc.top(self.q, "clicks", 2)[0]["query"],
                         "roof anchor certification miami")

    def test_striking_distance_window(self):
        hits = {r["query"] for r in gsc.striking_distance(self.q)}
        self.assertIn("roof anchor certification", hits)       # pos 6.8
        self.assertIn("walking working surfaces osha", hits)   # pos 12.1
        self.assertNotIn("roof anchor certification miami", hits)  # pos 2.4, already top-3
        self.assertNotIn("lagala construction", hits)          # pos 1.2

    def test_striking_distance_respects_min_impressions(self):
        thin = gsc.to_records(api_rows([("rare term", 0, 5, 8.0)]), ["query"])
        self.assertEqual(gsc.striking_distance(thin), [])

    def test_striking_distance_upside_is_ranked(self):
        out = gsc.striking_distance(self.q)
        self.assertEqual(out, sorted(out, key=lambda r: r["upside_clicks"], reverse=True))
        self.assertGreater(out[0]["upside_clicks"], 0)

    def test_ctr_gaps_flags_underclicked_top10(self):
        gaps = {r["query"] for r in gsc.ctr_gaps(self.q)}
        self.assertIn("osha 1910.28 compliance", gaps)   # pos 3.1 but 0.5% CTR
        self.assertNotIn("lagala construction", gaps)    # pos 1.2, 33% CTR

    def test_ctr_gaps_ignores_page_two(self):
        deep = gsc.to_records(api_rows([("deep", 0, 900, 15.0)]), ["query"])
        self.assertEqual(gsc.ctr_gaps(deep), [])

    def test_expected_ctr_monotonic_decay(self):
        self.assertGreater(gsc.expected_ctr(1), gsc.expected_ctr(3))
        self.assertGreater(gsc.expected_ctr(3), gsc.expected_ctr(10))
        self.assertGreater(gsc.expected_ctr(10), gsc.expected_ctr(30))
        self.assertGreaterEqual(gsc.expected_ctr(99), 0.002)

    def test_compare_movers_and_position_direction(self):
        prev = gsc.to_records(api_rows([
            ("roof anchor certification miami", 10, 400, 5.0),   # improved 5.0 -> 2.4
            ("gone query", 25, 500, 3.0),
        ]), ["query"])
        movers = gsc.compare(self.q, prev, "query")
        top = movers[0]
        self.assertEqual(top["query"], "roof anchor certification miami")
        self.assertEqual(top["clicks_delta"], 30)
        self.assertGreater(top["position_delta"], 0)  # positive = moved UP the page
        new = [m for m in movers if m["is_new"]]
        self.assertTrue(any(m["query"] == "osha 1910.28 compliance" for m in new))

    def test_compare_surfaces_queries_that_dropped_out(self):
        prev = gsc.to_records(api_rows([("vanished term", 22, 300, 2.0)]), ["query"])
        movers = gsc.compare(self.q, prev, "query")
        lost = [m for m in movers if m["is_lost"]]
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0]["query"], "vanished term")
        self.assertEqual(lost[0]["clicks_delta"], -22)   # the biggest loss on the page
        self.assertEqual(movers[-1]["query"], "vanished term")  # sorts to the bottom

    def test_compare_ignores_thin_dropped_rows(self):
        prev = gsc.to_records(api_rows([("noise", 0, 3, 40.0)]), ["query"])
        self.assertEqual([m for m in gsc.compare(self.q, prev, "query") if m["is_lost"]], [])

    def test_compare_skips_thin_rows(self):
        thin = gsc.to_records(api_rows([("tiny", 0, 2, 9.0)]), ["query"])
        self.assertEqual(gsc.compare(thin, [], "query"), [])


class GeoTests(unittest.TestCase):
    def test_city_of_matches_longest_slug(self):
        self.assertEqual(gsc.city_of("/west-palm-beach-roof-anchor-certification"), "west-palm-beach")
        self.assertEqual(gsc.city_of("/north-palm-beach-roof-anchor-certification"), "north-palm-beach")
        self.assertEqual(gsc.city_of("/miami-roof-anchor-certification"), "miami")
        self.assertEqual(gsc.city_of("/roof-anchor-certification"), "")

    def test_city_of_handles_query_text(self):
        self.assertEqual(gsc.city_of("fort lauderdale roof anchor"), "fort-lauderdale")

    def test_by_city_rollup(self):
        cities = gsc.by_city(gsc.to_records(PAGE_ROWS, ["page"]))
        self.assertEqual(cities[0]["city"], "miami")
        self.assertEqual(cities[0]["county"], "Miami-Dade")
        self.assertEqual(len(cities), 3)  # the non-city homepage row is excluded

    def test_by_county_aggregates_cities(self):
        counties = {c["county"]: c for c in gsc.by_county(gsc.to_records(PAGE_ROWS, ["page"]))}
        self.assertEqual(counties["Miami-Dade"]["impressions"], 800)
        self.assertEqual(counties["Broward"]["clicks"], 8)
        self.assertNotIn("Martin", counties)   # no Martin page exists yet

    def test_cross_permits_flags_coverage_gap(self):
        counties = gsc.by_county(gsc.to_records(PAGE_ROWS, ["page"]))
        rows = {r["county"]: r for r in gsc.cross_permits(counties, {"Martin": 120, "Broward": 300})}
        self.assertTrue(rows["Martin"]["gap"])        # permits, zero search presence
        self.assertFalse(rows["Broward"]["gap"])
        self.assertEqual(rows["Broward"]["impr_per_permit"], round(200 / 300, 2))
        self.assertIsNone(rows["Miami-Dade"]["impr_per_permit"])  # no permit count given

    def test_permit_counts_from_csv(self):
        csv_text = "permit,county\nA,Broward\nB,Broward\nC,Martin\n"
        self.assertEqual(gsc.permit_counts_from_csv(csv_text), {"Broward": 2, "Martin": 1})
        self.assertEqual(gsc.permit_counts_from_csv(""), {})


class DateTests(unittest.TestCase):
    def test_date_range_respects_lag(self):
        start, end = gsc.date_range(28, end=date(2026, 8, 1))
        self.assertEqual(end, date(2026, 8, 1))
        self.assertEqual((end - start).days, 27)

    def test_previous_range_is_adjacent_same_length(self):
        start, end = date(2026, 7, 5), date(2026, 8, 1)
        ps, pe = gsc.previous_range(start, end)
        self.assertEqual(pe, date(2026, 7, 4))
        self.assertEqual((pe - ps).days, (end - start).days)


class AuthTests(unittest.TestCase):
    def test_missing_credentials_reported_by_name_only(self):
        a = gsc.Auth.from_env({"GSC_CLIENT_ID": "public-id", "GSC_CLIENT_SECRET": "s3cret"})
        problems = a.configured()
        self.assertTrue(any("GSC_REFRESH_TOKEN" in p for p in problems))
        self.assertFalse(any("s3cret" in p for p in problems))

    def test_no_credentials_at_all(self):
        self.assertIn("no credentials", gsc.Auth.from_env({}).configured()[0])

    def test_service_account_from_inline_json(self):
        sa = json.dumps({"client_email": "bot@x.iam.gserviceaccount.com", "private_key": "KEY"})
        a = gsc.Auth.from_env({"GSC_SERVICE_ACCOUNT_JSON": sa})
        self.assertEqual(a.configured(), [])

    def test_service_account_from_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"client_email": "bot@x", "private_key": "KEY"}, f)
            path = f.name
        try:
            self.assertEqual(gsc.Auth.from_env({"GSC_SERVICE_ACCOUNT_JSON": path}).configured(), [])
        finally:
            os.unlink(path)

    def test_token_is_cached_until_expiry(self):
        a = gsc.Auth(client_id="i", client_secret="s", refresh_token="r")
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"access_token": "tok", "expires_in": 3600}
        with mock.patch("gsc.requests.post", return_value=resp) as post:
            self.assertEqual(a.token(), "tok")
            self.assertEqual(a.token(), "tok")
            self.assertEqual(post.call_count, 1)

    def test_token_failure_raises_with_status(self):
        a = gsc.Auth(client_id="i", client_secret="s", refresh_token="r")
        resp = mock.Mock(status_code=400, text='{"error":"invalid_grant"}')
        with mock.patch("gsc.requests.post", return_value=resp):
            with self.assertRaises(gsc.GSCError) as ctx:
                a.token()
        self.assertIn("invalid_grant", str(ctx.exception))


class FakeSession:
    """Records requests and replays queued JSON responses."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def post(self, url, json=None, timeout=None, headers=None):
        self.calls.append(json)
        page = self.pages.pop(0)
        r = mock.Mock(status_code=page.get("status", 200), text=page.get("text", ""))
        r.json = lambda p=page: {"rows": p.get("rows", [])}
        return r

    def get(self, url, timeout=None, headers=None):
        r = mock.Mock(status_code=200)
        r.json = lambda: {"siteEntry": [{"siteUrl": "https://a.example/"},
                                        {"siteUrl": "sc-domain:b.example"}]}
        return r


class ClientTests(unittest.TestCase):
    def _client(self, session):
        auth = gsc.Auth(client_id="i", client_secret="s", refresh_token="r")
        auth._token, auth._expiry = "tok", 1e12
        return gsc.SearchConsole(auth, session=session)

    def test_query_sends_expected_payload(self):
        s = FakeSession([{"rows": QUERY_ROWS}])
        rows = self._client(s).query("https://x.example/", date(2026, 7, 1), date(2026, 7, 28))
        self.assertEqual(len(rows), 6)
        sent = s.calls[0]
        self.assertEqual(sent["startDate"], "2026-07-01")
        self.assertEqual(sent["dimensions"], ["query"])
        self.assertEqual(sent["dataState"], "final")

    def test_query_paginates_until_short_page(self):
        full = api_rows([(f"q{i}", 1, 10, 5.0) for i in range(3)])
        s = FakeSession([{"rows": full}, {"rows": full}, {"rows": full[:1]}])
        rows = self._client(s).query("https://x.example/", date(2026, 7, 1), date(2026, 7, 2),
                                     row_limit=3)
        self.assertEqual(len(rows), 7)
        self.assertEqual([c["startRow"] for c in s.calls], [0, 3, 6])

    def test_query_retries_on_429_then_succeeds(self):
        s = FakeSession([{"status": 429, "text": "quota"}, {"rows": QUERY_ROWS}])
        with mock.patch("gsc.time.sleep"):
            rows = self._client(s).query("https://x.example/", date(2026, 7, 1), date(2026, 7, 2))
        self.assertEqual(len(rows), 6)

    def test_query_gives_up_on_403_immediately(self):
        s = FakeSession([{"status": 403, "text": "forbidden"}])
        with mock.patch("gsc.time.sleep"):
            with self.assertRaises(gsc.GSCError) as ctx:
                self._client(s).query("https://x.example/", date(2026, 7, 1), date(2026, 7, 2))
        self.assertIn("403", str(ctx.exception))
        self.assertEqual(len(s.calls), 1)   # no retry on a permission error

    def test_site_url_is_encoded_in_path(self):
        s = FakeSession([{"rows": []}])
        captured = {}
        real_post = s.post

        def spy(url, **kw):
            captured["url"] = url
            return real_post(url, **kw)
        s.post = spy
        self.assertEqual(self._client(s).query("https://x.example/", date(2026, 7, 1),
                                               date(2026, 7, 2)), [])
        self.assertIn("https%3A%2F%2Fx.example%2F", captured["url"])

    def test_sites_list(self):
        self.assertEqual(self._client(FakeSession([])).sites(),
                         ["https://a.example/", "sc-domain:b.example"])


class ReportTests(unittest.TestCase):
    def _data(self, with_permits=True):
        q = gsc.to_records(QUERY_ROWS, ["query"])
        p = gsc.to_records(PAGE_ROWS, ["page"])
        prev = gsc.to_records(api_rows([("roof anchor certification miami", 10, 400, 5.0)]), ["query"])
        d = {"totals": gsc.totals(q), "totals_prev": gsc.totals(prev),
             "top_queries": gsc.top(q), "top_pages": gsc.top(p),
             "striking": gsc.striking_distance(q), "ctr_gaps": gsc.ctr_gaps(q),
             "movers": gsc.compare(q, prev, "query"),
             "cities": gsc.by_city(p), "counties": gsc.by_county(p)}
        if with_permits:
            d["permits"] = gsc.cross_permits(d["counties"], {"Martin": 50, "Broward": 300})
        return d

    def test_report_contains_key_sections(self):
        md = gsc.render_report("https://x.example/", date(2026, 7, 1), date(2026, 7, 28),
                               self._data())
        for section in ("## Totals", "## Top queries", "## Striking distance",
                        "## CTR gaps", "## City pages", "## Search demand vs permit volume"):
            self.assertIn(section, md)
        self.assertIn("⚠️ no coverage", md)   # Martin has permits, no page

    def test_report_without_permits_or_comparison(self):
        d = self._data(with_permits=False)
        d.pop("totals_prev")
        md = gsc.render_report("https://x.example/", date(2026, 7, 1), date(2026, 7, 28), d)
        self.assertNotIn("Search demand vs permit volume", md)
        self.assertIn("| Clicks |", md)

    def test_report_never_leaks_secrets(self):
        md = gsc.render_report("https://x.example/", date(2026, 7, 1), date(2026, 7, 28),
                               self._data())
        for bad in ("private_key", "refresh_token", "Bearer ", "client_secret"):
            self.assertNotIn(bad, md)

    def test_csv_roundtrip(self):
        out = gsc.to_csv(gsc.to_records(QUERY_ROWS, ["query"]),
                         ["query", "clicks", "impressions", "ctr", "position"])
        self.assertTrue(out.startswith("query,clicks,impressions,ctr,position"))
        self.assertEqual(len(out.strip().splitlines()), 7)
        self.assertEqual(gsc.to_csv([]), "")


class CLITests(unittest.TestCase):
    def _client(self, pages):
        auth = gsc.Auth(client_id="i", client_secret="s", refresh_token="r")
        auth._token, auth._expiry = "tok", 1e12
        return gsc.SearchConsole(auth, session=FakeSession(pages))

    def test_build_assembles_all_slices(self):
        client = self._client([{"rows": QUERY_ROWS}, {"rows": PAGE_ROWS}, {"rows": QUERY_ROWS}])
        data = _gsc_pull.build(client, "https://x.example/", 28, end=date(2026, 8, 1))
        for k in ("totals", "top_queries", "top_pages", "striking", "ctr_gaps",
                  "cities", "counties", "movers", "totals_prev"):
            self.assertIn(k, data)
        self.assertEqual(data["end"], date(2026, 8, 1))

    def test_build_with_permits_csv(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("permit,county\n1,Martin\n2,Martin\n")
            path = f.name
        try:
            client = self._client([{"rows": QUERY_ROWS}, {"rows": PAGE_ROWS}, {"rows": []}])
            data = _gsc_pull.build(client, "https://x.example/", 7, end=date(2026, 8, 1),
                                   permits_csv=path)
        finally:
            os.unlink(path)
        martin = [r for r in data["permits"] if r["county"] == "Martin"][0]
        self.assertEqual(martin["permits"], 2)
        self.assertTrue(martin["gap"])

    def test_write_out_creates_report_and_csvs(self):
        client = self._client([{"rows": QUERY_ROWS}, {"rows": PAGE_ROWS}, {"rows": []}])
        data = _gsc_pull.build(client, "https://wwslgc.example/", 7, end=date(2026, 8, 1))
        with tempfile.TemporaryDirectory() as d:
            report, paths = _gsc_pull.write_out(data, d)
            names = sorted(os.path.basename(p) for p in paths)
        self.assertIn("gsc-wwslgc.example-2026-08-01.md", names)
        self.assertIn("gsc-wwslgc.example-2026-08-01-queries.csv", names)
        self.assertIn("# Search Console", report)

    def test_main_exits_2_without_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_gsc_pull.main(["--days", "7"]), 2)

    def test_main_lists_sites(self):
        auth = gsc.Auth(client_id="i", client_secret="s", refresh_token="r")
        auth._token, auth._expiry = "tok", 1e12
        with mock.patch.dict(os.environ, {"GSC_CLIENT_ID": "i", "GSC_CLIENT_SECRET": "s",
                                          "GSC_REFRESH_TOKEN": "r"}, clear=True), \
             mock.patch.object(gsc.Auth, "from_env", return_value=auth), \
             mock.patch.object(gsc.SearchConsole, "sites",
                               return_value=["https://a.example/"]):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = _gsc_pull.main(["--list"])
        self.assertEqual(rc, 0)
        self.assertIn("https://a.example/", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)

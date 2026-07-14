"""
Offline test suite for the SoFlo Permit Leads engine (api/permits.py).

All network I/O is mocked — these tests run in any sandbox. They cover:
  schema auto-mapping, date/value coercion, the tagging engine, ArcGIS
  item resolution, query fallback behavior, Hub DCAT discovery, the full
  /api/permits/* endpoints (search filters, demo fallback, CSV export).

Run:  python3 _permits_tests.py
"""

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, "api")
import permits  # noqa: E402


def _iso_days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _epoch_ms_days_ago(n):
    return int((datetime.now(timezone.utc) - timedelta(days=n)).timestamp() * 1000)


class TagEngineTests(unittest.TestCase):
    CASES = [
        ("RE-ROOF SHINGLE 24SQ", "roofing"),
        ("Remove and replace tile roof", "roofing"),
        ("INSTALL SOLAR PV 10KW", "solar"),
        ("A/C CHANGEOUT 4 TON", "hvac"),
        ("HVAC changeout with new ducts", "hvac"),
        ("NEW SWIMMING POOL WITH SPA", "pool_spa"),
        ("SEAWALL CAP REPLACEMENT", "dock_seawall"),
        ("INSTALL BOAT LIFT AND DOCK", "dock_seawall"),
        ("22KW STANDBY GENERATOR", "generator"),
        ("IMPACT WINDOWS 12 OPENINGS", "impact_shutters"),
        ("HURRICANE SHUTTERS", "impact_shutters"),
        ("REPLACE WATER HEATER 50 GAL", "water_heater"),
        ("INSTALL EV CHARGER IN GARAGE", "ev_charger"),
        ("TOTAL DEMOLITION OF STRUCTURE", "demolition"),
        ("NEW SINGLE FAMILY RESIDENCE", "new_construction"),
        ("KITCHEN REMODEL NEW CABINETS", "kitchen_bath"),
        ("WOOD FENCE 6FT", "fence"),
        ("TENANT IMPROVEMENT BUILD-OUT", "remodel"),
        ("MASTER SUITE ADDITION 480 SF", "addition"),
        ("PAVER DRIVEWAY", "driveway_paving"),
        ("FIRE SPRINKLER MODIFICATION", "fire"),
        ("ELECTRICAL PANEL UPGRADE 200 AMP", "electrical"),
        ("WHOLE HOUSE RE-PIPE", "plumbing"),
    ]

    def test_tag_cases(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertIn(expected, permits.tag_permit(text))

    def test_no_tags_for_unrelated(self):
        self.assertEqual(permits.tag_permit("MISC ADMINISTRATIVE CORRECTION"), [])

    def test_tag_catalog_matches_rules(self):
        keys = [k for k, _, _ in permits.TAG_RULES]
        self.assertEqual(len(keys), len(set(keys)), "duplicate tag keys")


class CoercionTests(unittest.TestCase):
    def test_epoch_ms(self):
        ms = _epoch_ms_days_ago(2)
        self.assertEqual(permits._epoch_to_iso(ms), _iso_days_ago(2))

    def test_epoch_seconds(self):
        s = int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp())
        self.assertEqual(permits._epoch_to_iso(s), _iso_days_ago(3))

    def test_iso_string_passthrough(self):
        self.assertEqual(permits._epoch_to_iso("2026-07-01T10:00:00"), "2026-07-01")

    def test_numeric_string(self):
        ms = str(_epoch_ms_days_ago(1))
        self.assertEqual(permits._epoch_to_iso(ms), _iso_days_ago(1))

    def test_garbage(self):
        self.assertIsNone(permits._epoch_to_iso("not a date"))
        self.assertIsNone(permits._epoch_to_iso(None))
        self.assertIsNone(permits._epoch_to_iso(0))
        self.assertIsNone(permits._epoch_to_iso(42))  # too small to be an epoch

    def test_to_float(self):
        self.assertEqual(permits._to_float("$1,234.56"), 1234.56)
        self.assertIsNone(permits._to_float(None))
        self.assertIsNone(permits._to_float("abc"))
        self.assertEqual(permits._to_float(250000), 250000.0)


class FieldMappingTests(unittest.TestCase):
    def test_mdc_style_schema(self):
        fields = [
            {"name": "PERMIT_NUMBER", "type": "esriFieldTypeString"},
            {"name": "SCOPE_OF_WORK", "type": "esriFieldTypeString"},
            {"name": "SITE_ADDR", "type": "esriFieldTypeString"},
            {"name": "ISSUED_DATE", "type": "esriFieldTypeDate"},
            {"name": "STATUS", "type": "esriFieldTypeString"},
            {"name": "PERMIT_TYPE", "type": "esriFieldTypeString"},
            {"name": "ESTIMATED_VALUE", "type": "esriFieldTypeDouble"},
        ]
        m = permits.map_fields(fields)
        self.assertEqual(m["permit_number"], "PERMIT_NUMBER")
        self.assertEqual(m["description"], "SCOPE_OF_WORK")
        self.assertEqual(m["address"], "SITE_ADDR")
        self.assertEqual(m["issue_date"], "ISSUED_DATE")
        self.assertEqual(m["value"], "ESTIMATED_VALUE")

    def test_camelcase_schema(self):
        fields = [
            {"name": "PermitNum", "type": "esriFieldTypeString"},
            {"name": "WorkDescription", "type": "esriFieldTypeString"},
            {"name": "FullAddress", "type": "esriFieldTypeString"},
            {"name": "DateIssued", "type": "esriFieldTypeDate"},
            {"name": "JobValue", "type": "esriFieldTypeDouble"},
            {"name": "ContractorName", "type": "esriFieldTypeString"},
        ]
        m = permits.map_fields(fields)
        self.assertEqual(m["permit_number"], "PermitNum")
        self.assertEqual(m["description"], "WorkDescription")
        self.assertEqual(m["address"], "FullAddress")
        self.assertEqual(m["issue_date"], "DateIssued")
        self.assertEqual(m["value"], "JobValue")
        self.assertEqual(m["contractor"], "ContractorName")

    def test_date_field_priority_prefers_typed_dates(self):
        fields = [
            {"name": "ISSUED", "type": "esriFieldTypeString"},  # decoy: string typed
            {"name": "ISSUE_DT", "type": "esriFieldTypeDate"},
            {"name": "APPLIED_DT", "type": "esriFieldTypeDate"},
        ]
        m = permits.map_fields(fields)
        self.assertEqual(m["issue_date"], "ISSUE_DT")
        self.assertEqual(m["applied_date"], "APPLIED_DT")


class NormalizeTests(unittest.TestCase):
    def test_normalize_arcgis_feature(self):
        mapping = {"permit_number": "PN", "description": "DESC", "address": "ADDR",
                   "issue_date": "ISSUED", "value": "VAL"}
        src = {"id": "mdc", "county": "Miami-Dade"}
        feat = {"attributes": {"PN": "B-2026-1", "DESC": "RE-ROOF 20 SQ",
                               "ADDR": "1 MAIN ST", "ISSUED": _epoch_ms_days_ago(1),
                               "VAL": "15000"},
                "geometry": {"x": -80.19, "y": 25.77}}
        p = permits.normalize_feature(feat, mapping, src)
        self.assertEqual(p["permit_number"], "B-2026-1")
        self.assertEqual(p["issued_date"], _iso_days_ago(1))
        self.assertEqual(p["value"], 15000.0)
        self.assertIn("roofing", p["tags"])
        self.assertEqual(p["county"], "Miami-Dade")
        self.assertAlmostEqual(p["lon"], -80.19)
        self.assertEqual(p["appraiser_url"], permits.APPRAISER_SEARCH["Miami-Dade"])


class ArcGISAdapterTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    def test_resolve_item_service_root_picks_first_layer(self):
        def fake_get_json(url, params=None, timeout=None):
            if "content/items" in url:
                return {"url": "https://svc.example/arcgis/rest/services/Permits/FeatureServer"}
            if url.endswith("FeatureServer"):
                return {"layers": [{"id": 3, "name": "Permits"}]}
            raise AssertionError(f"unexpected url {url}")
        with mock.patch.object(permits, "_get_json", side_effect=fake_get_json):
            url = permits.resolve_item_to_layer("abc123")
        self.assertTrue(url.endswith("/FeatureServer/3"))

    def test_resolve_item_error(self):
        with mock.patch.object(permits, "_get_json",
                               return_value={"error": {"message": "Item does not exist"}}):
            with self.assertRaises(RuntimeError):
                permits.resolve_item_to_layer("bad")

    def test_query_layer_orderby_fallback(self):
        calls = []
        def fake_get_json(url, params=None, timeout=None):
            calls.append(dict(params))
            if "orderByFields" in params:
                return {"error": {"message": "order by not supported"}}
            return {"features": [{"attributes": {"A": 1}}]}
        with mock.patch.object(permits, "_get_json", side_effect=fake_get_json):
            feats = permits.query_layer("https://x/FeatureServer/0", order_field="D")
        self.assertEqual(len(feats), 1)
        self.assertEqual(len(calls), 2)  # first with orderBy, retry without

    def test_query_layer_hard_error(self):
        with mock.patch.object(permits, "_get_json",
                               return_value={"error": {"message": "boom"}}):
            with self.assertRaises(RuntimeError):
                permits.query_layer("https://x/FeatureServer/0")


class HubDiscoveryTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    FEED = {"dataset": [
        {"title": "Building Permits Issued", "description": "permits",
         "landingPage": "https://hub/x",
         "distribution": [
             {"accessURL": "https://hub/csv"},
             {"accessURL": "https://svc.example/arcgis/rest/services/BP/FeatureServer/0"}]},
        {"title": "Well Permits", "description": "wells",
         "distribution": [
             {"accessURL": "https://svc.example/arcgis/rest/services/Well/FeatureServer/0"}]},
        {"title": "Parks", "description": "no permits here",
         "distribution": [
             {"accessURL": "https://svc.example/arcgis/rest/services/Parks/FeatureServer/0"}]},
        {"title": "Development Permits", "description": "dev activity",
         "distribution": [
             {"accessURL": "https://svc.example/arcgis/rest/services/Dev/FeatureServer"}]},
    ]}

    def test_discovery_filters_and_ranks(self):
        with mock.patch.object(permits, "_get_json", return_value=self.FEED):
            found = permits.discover_hub_permit_layers("https://data.example.gov")
        titles = [f["title"] for f in found]
        self.assertIn("Building Permits Issued", titles)
        self.assertIn("Development Permits", titles)
        self.assertNotIn("Well Permits", titles)   # negative filter
        self.assertNotIn("Parks", titles)          # not permit-ish
        self.assertEqual(titles[0], "Building Permits Issued")  # ranked first
        # service-root URL got /0 appended
        dev = [f for f in found if f["title"] == "Development Permits"][0]
        self.assertTrue(dev["layer_url"].endswith("/FeatureServer/0"))

    def test_discovery_feed_unreachable_raises(self):
        with mock.patch.object(permits, "_get_json", side_effect=Exception("net down")):
            with self.assertRaises(RuntimeError):
                permits.discover_hub_permit_layers("https://dead.example.gov")


class FetchSourceTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    def _fake_layer_world(self, url, params=None, timeout=None):
        """A fake ArcGIS universe with one working layer."""
        if url.endswith("/query"):
            return {"features": [
                {"attributes": {"PERMITNO": f"F-{i}", "DESCRIPTION": "RE-ROOF",
                                "ADDRESS": f"{i} OCEAN DR",
                                "ISSUEDDATE": _epoch_ms_days_ago(i)},
                 "geometry": {"x": -80.1, "y": 26.1}} for i in range(3)]}
        # layer metadata
        return {"name": "Permits", "fields": [
            {"name": "PERMITNO", "type": "esriFieldTypeString"},
            {"name": "DESCRIPTION", "type": "esriFieldTypeString"},
            {"name": "ADDRESS", "type": "esriFieldTypeString"},
            {"name": "ISSUEDDATE", "type": "esriFieldTypeDate"},
        ]}

    def test_arcgis_layer_source_ok(self):
        src = {"id": "t", "county": "Broward", "label": "T", "kind": "arcgis_layer",
               "layer_urls": ["https://x/MapServer/0"]}
        with mock.patch.object(permits, "_get_json", side_effect=self._fake_layer_world):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "ok")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["county"], "Broward")
        self.assertIn("roofing", rows[0]["tags"])

    def test_layer_failover_to_second_url(self):
        def flaky(url, params=None, timeout=None):
            if "bad" in url:
                raise Exception("500 server error")
            return self._fake_layer_world(url, params, timeout)
        src = {"id": "t", "county": "Broward", "label": "T", "kind": "arcgis_layer",
               "layer_urls": ["https://bad/MapServer/0", "https://good/MapServer/0"]}
        with mock.patch.object(permits, "_get_json", side_effect=flaky):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "ok")
        self.assertIn("good", info["layer_url"])

    def test_all_layers_fail(self):
        src = {"id": "t", "county": "Broward", "label": "T", "kind": "arcgis_layer",
               "layer_urls": ["https://bad/MapServer/0"]}
        with mock.patch.object(permits, "_get_json", side_effect=Exception("down")):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "error")
        self.assertEqual(rows, [])

    def test_arcgis_item_falls_back_to_discovery(self):
        """When pinned item IDs fail, a source with hub_sites should discover
        the current permit layer from the county's catalog and use it."""
        good_layer = "https://svc.example/arcgis/rest/services/BP/FeatureServer/0"
        feed = {"dataset": [
            {"title": "Building Permits", "description": "permits",
             "distribution": [{"accessURL": good_layer}]}]}

        def world(url, params=None, timeout=None):
            if "content/items" in url:
                raise Exception("410 item removed")           # pinned items dead
            if url.endswith(".json") and "feed" in url or url.endswith("data.json"):
                return feed
            if "dcat" in url:
                return feed
            if url.endswith("/query"):
                return {"features": [{"attributes": {"PERMITNO": "X-1",
                        "DESCRIPTION": "SOLAR PV", "ISSUEDDATE": _epoch_ms_days_ago(1)}}]}
            return {"name": "BP", "fields": [
                {"name": "PERMITNO", "type": "esriFieldTypeString"},
                {"name": "DESCRIPTION", "type": "esriFieldTypeString"},
                {"name": "ISSUEDDATE", "type": "esriFieldTypeDate"}]}

        src = {"id": "mdc", "county": "Miami-Dade", "label": "MDC",
               "kind": "arcgis_item", "item_ids": ["deadbeef"],
               "hub_sites": ["https://gis-mdc.opendata.arcgis.com"]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "ok")
        self.assertEqual(len(rows), 1)
        self.assertIn("solar", rows[0]["tags"])
        self.assertIn("discovered", info)

    def test_layer_without_permit_fields_is_rejected(self):
        def world(url, params=None, timeout=None):
            if url.endswith("/query"):
                return {"features": [{"attributes": {"SHAPE_AREA": 1.0, "OBJECTID": 2}}]}
            return {"name": "Parcels", "fields": [
                {"name": "SHAPE_AREA", "type": "esriFieldTypeDouble"},
                {"name": "OBJECTID", "type": "esriFieldTypeOID"}]}
        src = {"id": "t", "county": "Broward", "label": "T", "kind": "arcgis_layer",
               "layer_urls": ["https://x/FeatureServer/0"]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "error")
        self.assertIn("permit fields", info["error"])

    def test_hub_discover_no_dataset(self):
        src = {"id": "t", "county": "Martin", "label": "T", "kind": "hub_discover",
               "hub_sites": ["https://data.example.gov"]}
        with mock.patch.object(permits, "_get_json", return_value={"dataset": []}):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "no_dataset")

    def test_hub_discover_catalogs_unreachable_is_error(self):
        src = {"id": "t", "county": "Martin", "label": "T", "kind": "hub_discover",
               "hub_sites": ["https://dead.example.gov"]}
        with mock.patch.object(permits, "_get_json", side_effect=Exception("net down")):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "error")
        self.assertIn("net down", info["error"])


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from flask import Flask
        cls.app = Flask(__name__)
        permits.register_permits_routes(cls.app)
        cls.client = cls.app.test_client()

    def setUp(self):
        permits._cache.clear()

    def _live_permits(self):
        return [
            {"source_id": "mdc", "county": "Miami-Dade", "permit_number": "M-1",
             "type": "BLDG", "status": "ISSUED", "description": "RE-ROOF 20SQ",
             "address": "1 MAIN ST", "city": "Miami", "zip": "33130",
             "issued_date": _iso_days_ago(2), "applied_date": None, "value": 20000.0,
             "contractor": "ROOFCO", "owner": None, "lat": None, "lon": None,
             "tags": ["roofing"], "appraiser_url": "x"},
            {"source_id": "mdc", "county": "Miami-Dade", "permit_number": "M-2",
             "type": "ELEC", "status": "ISSUED", "description": "SOLAR PV 8KW",
             "address": "2 MAIN ST", "city": "Miami", "zip": "33130",
             "issued_date": _iso_days_ago(50), "applied_date": None, "value": 30000.0,
             "contractor": "SUNCO", "owner": None, "lat": None, "lon": None,
             "tags": ["solar"], "appraiser_url": "x"},
            {"source_id": "ftl", "county": "Broward", "permit_number": "B-1",
             "type": "POOL", "status": "ISSUED", "description": "NEW POOL",
             "address": "3 BEACH RD", "city": "Fort Lauderdale", "zip": "33301",
             "issued_date": _iso_days_ago(5), "applied_date": None, "value": 60000.0,
             "contractor": "POOLCO", "owner": None, "lat": None, "lon": None,
             "tags": ["pool_spa"], "appraiser_url": "x"},
        ]

    def _patch_live(self):
        rows = self._live_permits()
        def fake_fetch(source, record_count=2000):
            mine = [p for p in rows if p["source_id"] == source["id"]]
            status = "ok" if mine else "empty"
            return mine, {"id": source["id"], "county": source["county"],
                          "label": source.get("label"), "status": status,
                          "count": len(mine)}
        return mock.patch.object(permits, "fetch_source", side_effect=fake_fetch)

    def test_search_basic(self):
        with self._patch_live():
            r = self.client.get("/api/permits/search?days=30")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["demo"])
        nums = [p["permit_number"] for p in data["permits"]]
        self.assertIn("M-1", nums)
        self.assertIn("B-1", nums)
        self.assertNotIn("M-2", nums)  # 50 days old > 30-day window
        # newest first
        self.assertEqual(nums[0], "M-1")

    def test_search_filter_county(self):
        with self._patch_live():
            r = self.client.get("/api/permits/search?county=broward&days=90")
        data = r.get_json()
        self.assertEqual({p["county"] for p in data["permits"]}, {"Broward"})

    def test_search_filter_tag_value_q(self):
        with self._patch_live():
            r = self.client.get("/api/permits/search?days=90&tags=solar")
            self.assertEqual([p["permit_number"] for p in r.get_json()["permits"]], ["M-2"])
            permits._cache.clear()
            r = self.client.get("/api/permits/search?days=90&min_value=50000")
            self.assertEqual([p["permit_number"] for p in r.get_json()["permits"]], ["B-1"])
            permits._cache.clear()
            r = self.client.get("/api/permits/search?days=90&q=roofco")
            self.assertEqual([p["permit_number"] for p in r.get_json()["permits"]], ["M-1"])

    def test_search_demo_fallback_when_all_sources_fail(self):
        def dead_fetch(source, record_count=2000):
            return [], {"id": source["id"], "county": source["county"],
                        "label": source.get("label"), "status": "error",
                        "count": 0, "error": "unreachable"}
        with mock.patch.object(permits, "fetch_source", side_effect=dead_fetch):
            r = self.client.get("/api/permits/search?days=90")
        data = r.get_json()
        self.assertTrue(data["demo"])
        self.assertGreater(data["count"], 0)
        self.assertEqual({p["source_id"] for p in data["permits"]}, {"demo"})
        # all four counties represented in the sample set
        self.assertEqual(set(p["county"] for p in data["permits"]),
                         set(permits.COUNTIES))

    def test_search_forced_demo(self):
        r = self.client.get("/api/permits/search?demo=1&days=90&county=martin")
        data = r.get_json()
        self.assertTrue(data["demo"])
        self.assertEqual({p["county"] for p in data["permits"]}, {"Martin"})

    def test_tags_endpoint(self):
        r = self.client.get("/api/permits/tags")
        data = r.get_json()
        keys = [t["key"] for t in data["tags"]]
        self.assertIn("roofing", keys)
        self.assertIn("dock_seawall", keys)

    def test_sources_endpoint(self):
        r = self.client.get("/api/permits/sources")
        data = r.get_json()
        ids = [s["id"] for s in data["sources"]]
        self.assertEqual(set(ids), {"mdc", "ftl", "pbc", "martin"})
        self.assertEqual(data["counties"], permits.COUNTIES)

    def test_csv_export(self):
        with self._patch_live():
            r = self.client.get("/api/permits/export.csv?days=90")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.content_type)
        body = r.get_data(as_text=True)
        lines = body.strip().splitlines()
        self.assertEqual(len(lines), 4)  # header + 3 rows
        self.assertTrue(lines[0].startswith("issued_date,county,city,permit_number"))
        self.assertIn("RE-ROOF 20SQ", body)

    def test_discover_rejects_bad_site(self):
        r = self.client.get("/api/permits/discover?site=http://evil.example.com")
        self.assertEqual(r.status_code, 400)

    def test_extra_sources_env_merge(self):
        extra = json.dumps([
            {"id": "ftl", "label": "OVERRIDDEN"},
            {"id": "hollywood", "county": "Broward", "label": "Hollywood",
             "kind": "arcgis_layer", "layer_urls": ["https://h/MapServer/0"]},
        ])
        with mock.patch.dict("os.environ", {"PERMITS_EXTRA_SOURCES": extra}):
            sources = permits.load_sources()
        by_id = {s["id"]: s for s in sources}
        self.assertEqual(by_id["ftl"]["label"], "OVERRIDDEN")
        self.assertIn("hollywood", by_id)

    def test_bad_extra_sources_env_ignored(self):
        with mock.patch.dict("os.environ", {"PERMITS_EXTRA_SOURCES": "{not json"}):
            sources = permits.load_sources()
        self.assertEqual(len(sources), len(permits.DEFAULT_SOURCES))


class DemoDataTests(unittest.TestCase):
    def test_demo_covers_all_counties_and_tags(self):
        rows = permits.demo_permits()
        self.assertGreaterEqual(len(rows), 20)
        self.assertEqual(set(r["county"] for r in rows), set(permits.COUNTIES))
        tagged = [r for r in rows if r["tags"]]
        self.assertGreater(len(tagged), len(rows) * 0.8,
                           "most demo rows should carry project tags")
        for r in rows:
            self.assertIsNotNone(r["issued_date"])
            self.assertIsNotNone(r["value"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

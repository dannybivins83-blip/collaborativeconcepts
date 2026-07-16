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

    def test_violation_tags_no_false_positives(self):
        # these ordinary permits must NOT be tagged as violations
        for text in ["WORK COMPLETED UNDER MASTER PERMIT #123",
                     "SCOPE OF WORK PER PERMIT DRAWINGS",
                     "STRUCTURAL ADDITION 400 SF MASTER SUITE",
                     "NEW STRUCTURAL STEEL FOR COMMERCIAL BLDG"]:
            tags = permits.tag_permit(text)
            self.assertNotIn("no_permit", tags, text)
            self.assertNotIn("unsafe_structure", tags, text)

    def test_violation_tags_true_positives(self):
        self.assertIn("no_permit", permits.tag_permit("UNPERMITTED ADDITION"))
        self.assertIn("no_permit", permits.tag_permit("WORK WITHOUT PERMIT"))
        self.assertIn("unsafe_structure", permits.tag_permit("UNSAFE STRUCTURE - ROOF COLLAPSED"))
        self.assertIn("unsafe_structure", permits.tag_permit("DILAPIDATED / CONDEMNED BUILDING"))

    def test_reroof_tag_precision(self):
        # full replacement / anchor-disturbing work -> reroof
        for txt in ["RE-ROOF EXISTING FLAT ROOF TPO", "ROOF REPLACEMENT - TILE",
                    "TEAR OFF AND REROOF SHINGLE", "REPLACE EXISTING ROOF",
                    "ROOF RECOVER MODIFIED BITUMEN", "NEW ROOF INSTALLATION"]:
            with self.subTest(txt=txt):
                self.assertIn("reroof", permits.tag_permit(txt))
        # minor repairs are NOT reroofs (but are still general roofing leads)
        for txt in ["ROOF REPAIR", "ROOF LEAK REPAIR", "REPAIR 3 CRACKED TILES",
                    "ROOF INSPECTION ONLY"]:
            with self.subTest(txt=txt):
                self.assertNotIn("reroof", permits.tag_permit(txt))
        self.assertIn("roofing", permits.tag_permit("ROOF LEAK REPAIR"))

    def test_reroof_leads_shape(self):
        # run_reroof_leads returns lead-shaped rows with a pitch, using demo data
        res = permits.run_reroof_leads({"demo": "1", "counties": "Miami-Dade,Broward"})
        self.assertTrue(res["ok"])
        self.assertIn("leads", res)
        for lead in res["leads"]:
            self.assertTrue(lead.get("address"))
            self.assertIn("1910.27(b)", lead["pitch"])

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


class FieldInferenceTests(unittest.TestCase):
    def _feats(self, dicts):
        return [{"attributes": d} for d in dicts]

    def test_infers_address_and_description_when_names_opaque(self):
        # Miami-Dade-style: cryptic column names the synonym table won't catch.
        fields = [
            {"name": "PERMITNUMBER", "type": "esriFieldTypeString"},
            {"name": "COL_A", "type": "esriFieldTypeString"},   # address
            {"name": "COL_B", "type": "esriFieldTypeString"},   # description
            {"name": "FOLIO", "type": "esriFieldTypeDouble"},   # id, NOT value
            {"name": "ISSUINGDATE", "type": "esriFieldTypeDate"},
        ]
        feats = self._feats([
            {"PERMITNUMBER": "2026-1", "COL_A": "2740 SW 27TH AVE",
             "COL_B": "RE-ROOF: REMOVE EXISTING SHINGLES INSTALL NEW GAF TIMBERLINE 24 SQ",
             "FOLIO": 3040120010010, "ISSUINGDATE": 1},
            {"PERMITNUMBER": "2026-2", "COL_A": "815 CATALONIA AVE",
             "COL_B": "A/C CHANGEOUT 4 TON SPLIT SYSTEM LIKE FOR LIKE",
             "FOLIO": 3041220020020, "ISSUINGDATE": 2},
            {"PERMITNUMBER": "2026-3", "COL_A": "1020 WEST AVE",
             "COL_B": "IMPACT WINDOWS AND DOORS REPLACEMENT 22 OPENINGS HURRICANE RATED",
             "FOLIO": 3042320030030, "ISSUINGDATE": 3},
        ])
        base = permits.map_fields(fields)
        refined = permits.refine_mapping_with_samples(base, fields, feats)
        self.assertEqual(refined["address"], "COL_A")
        self.assertEqual(refined["description"], "COL_B")
        # FOLIO must NOT be chosen as value (it's a 13-digit id)
        self.assertNotEqual(refined.get("value"), "FOLIO")

    def test_rejects_implausible_value_and_picks_money_column(self):
        fields = [
            {"name": "FOLIO", "type": "esriFieldTypeDouble"},        # 205,180,000-ish
            {"name": "EST_VALUE", "type": "esriFieldTypeDouble"},    # real dollars
            {"name": "DESC", "type": "esriFieldTypeString"},
        ]
        feats = self._feats([
            {"FOLIO": 205180000, "EST_VALUE": 18500, "DESC": "NEW ROOF INSTALL"},
            {"FOLIO": 496600000, "EST_VALUE": 8900, "DESC": "AC CHANGEOUT UNIT"},
            {"FOLIO": 811300000, "EST_VALUE": 265000, "DESC": "COMMERCIAL BUILDOUT"},
        ])
        # simulate a bad name-based pick where FOLIO got grabbed as value
        bad = {"value": "FOLIO"}
        refined = permits.refine_mapping_with_samples(bad, fields, feats)
        self.assertEqual(refined["value"], "EST_VALUE")

    def test_drops_value_when_no_plausible_numeric(self):
        fields = [
            {"name": "OBJECTID", "type": "esriFieldTypeOID"},
            {"name": "FOLIO", "type": "esriFieldTypeDouble"},
            {"name": "DESC", "type": "esriFieldTypeString"},
        ]
        feats = self._feats([
            {"OBJECTID": 1, "FOLIO": 3040120010010, "DESC": "REROOF"},
            {"OBJECTID": 2, "FOLIO": 3041220020020, "DESC": "POOL"},
        ])
        refined = permits.refine_mapping_with_samples({"value": "FOLIO"}, fields, feats)
        self.assertIsNone(refined.get("value"))  # better nothing than $3-trillion

    def test_keeps_good_name_based_mapping(self):
        fields = [
            {"name": "SCOPE_OF_WORK", "type": "esriFieldTypeString"},
            {"name": "SITE_ADDR", "type": "esriFieldTypeString"},
            {"name": "ESTIMATED_VALUE", "type": "esriFieldTypeDouble"},
        ]
        feats = self._feats([
            {"SCOPE_OF_WORK": "RE-ROOF SHINGLE 24 SQUARES TOTAL",
             "SITE_ADDR": "123 MAIN ST", "ESTIMATED_VALUE": 20000},
        ])
        base = permits.map_fields(fields)
        refined = permits.refine_mapping_with_samples(base, fields, feats)
        self.assertEqual(refined["description"], "SCOPE_OF_WORK")
        self.assertEqual(refined["address"], "SITE_ADDR")
        self.assertEqual(refined["value"], "ESTIMATED_VALUE")

    def test_empty_features_is_safe(self):
        fields = [{"name": "X", "type": "esriFieldTypeString"}]
        self.assertEqual(permits.refine_mapping_with_samples({"a": "b"}, fields, []),
                         {"a": "b"})


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


class FloridaGuardTests(unittest.TestCase):
    def test_out_of_state_zip_dropped(self):
        self.assertTrue(permits._out_of_florida({"zip": "23456"}))   # Virginia Beach
        self.assertTrue(permits._out_of_florida({"zip": "90210"}))   # CA
        self.assertFalse(permits._out_of_florida({"zip": "33133"}))  # Miami
        self.assertFalse(permits._out_of_florida({"zip": "34994"}))  # Stuart

    def test_out_of_state_geometry_dropped(self):
        self.assertTrue(permits._out_of_florida({"lat": 36.85, "lon": -76.0}))   # VA Beach
        self.assertFalse(permits._out_of_florida({"lat": 25.77, "lon": -80.19}))  # Miami

    def test_unknown_location_is_kept(self):
        self.assertFalse(permits._out_of_florida({"address": "900 SE OCEAN BLVD"}))
        self.assertFalse(permits._out_of_florida({}))

    def test_search_filters_out_of_state_rows(self):
        from flask import Flask
        app = Flask(__name__)
        permits.register_permits_routes(app)
        client = app.test_client()
        rows = [
            {"source_id": "ftl", "county": "Broward", "permit_number": "FL-1",
             "description": "RE-ROOF", "address": "1 SE 1 ST", "city": "Fort Lauderdale",
             "zip": "33301", "issued_date": _iso_days_ago(2), "value": 1000.0,
             "tags": ["roofing"], "appraiser_url": "x"},
            {"source_id": "ftl", "county": "Broward", "permit_number": "VB-1",
             "description": "POOL FENCE", "address": "2509 PRINCESS ANNE RD",
             "city": "Virginia Beach", "zip": "23456", "issued_date": _iso_days_ago(1),
             "value": 2000.0, "tags": ["pool_spa"], "appraiser_url": "x"},
        ]
        def fake_fetch(source, record_count=2000, start_ms=None, end_ms=None):
            mine = [p for p in rows if p["source_id"] == source["id"]]
            return mine, {"id": source["id"], "county": source["county"],
                          "status": "ok" if mine else "empty", "count": len(mine)}
        permits._cache.clear()
        with mock.patch.object(permits, "fetch_source", side_effect=fake_fetch):
            data = client.get("/api/permits/search?county=broward&days=90").get_json()
        nums = [p["permit_number"] for p in data["permits"]]
        self.assertIn("FL-1", nums)
        self.assertNotIn("VB-1", nums)          # Virginia Beach dropped
        self.assertEqual(data["dropped_out_of_state"], 1)


class CodeViolationsTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    def _energov_world(self, captured):
        """Mock the Miami-Dade EnerGov code-violations layer."""
        def world(url, params=None, timeout=None):
            p = params or {}
            if url.endswith("/query"):
                captured.append(p.get("where", ""))
                return {"features": [
                    {"attributes": {"CASE_NUM": "CE2026-001", "PROBLEM_DESC": "UNSAFE STRUCTURE - ROOF",
                                    "STAT_DESC": "Open", "ADDRESS": "123 NW 5 ST",
                                    "FOLIO": "0132340010010", "CASE_DATE": _epoch_ms_days_ago(5)},
                     "geometry": {"x": 900000.5, "y": 500000.2}}]}  # State Plane!
            return {"name": "Code Violations", "fields": [
                {"name": "CASE_NUM", "type": "esriFieldTypeString"},
                {"name": "PROBLEM_DESC", "type": "esriFieldTypeString"},
                {"name": "STAT_DESC", "type": "esriFieldTypeString"},
                {"name": "ADDRESS", "type": "esriFieldTypeString"},
                {"name": "FOLIO", "type": "esriFieldTypeString"},
                {"name": "CASE_DATE", "type": "esriFieldTypeDouble"}]}
        return world

    def test_field_map_and_open_filter_and_category(self):
        src = [s for s in permits.DEFAULT_SOURCES if s["id"] == "mdc_violations"][0]
        captured = []
        with mock.patch.object(permits, "_get_json", side_effect=self._energov_world(captured)):
            rows, info = permits.fetch_source(dict(src), start_ms=1_700_000_000_000,
                                              end_ms=1_800_000_000_000)
        self.assertEqual(info["status"], "ok")
        r = rows[0]
        self.assertEqual(r["permit_number"], "CE2026-001")       # CASE_NUM via field_map
        self.assertEqual(r["description"], "UNSAFE STRUCTURE - ROOF")
        self.assertEqual(r["status"], "Open")
        self.assertEqual(r["category"], "violation")
        self.assertIn("unsafe_structure", r["tags"])
        self.assertIn("roofing", r["tags"])
        # the open-case filter was ANDed into the server query
        self.assertTrue(any("CASE_STATUS IN ('1','4','6','8','9')" in w for w in captured))

    def test_state_plane_geometry_is_dropped_not_treated_as_latlon(self):
        src = [s for s in permits.DEFAULT_SOURCES if s["id"] == "mdc_violations"][0]
        with mock.patch.object(permits, "_get_json", side_effect=self._energov_world([])):
            rows, _ = permits.fetch_source(dict(src), start_ms=1, end_ms=None)
        # 900000/500000 are not valid lon/lat -> nulled, so the FL guard keeps the row
        self.assertIsNone(rows[0]["lat"])
        self.assertIsNone(rows[0]["lon"])
        self.assertFalse(permits._out_of_florida(rows[0]))

    def test_and_where_helper(self):
        self.assertEqual(permits._and_where("1=1", "A > 1"), "A > 1")
        self.assertEqual(permits._and_where("S IN (1)", "1=1"), "S IN (1)")
        self.assertEqual(permits._and_where("S IN (1)", "D > 5"), "(S IN (1)) AND (D > 5)")

    def test_base_where_applied_when_no_date(self):
        captured = []
        def world(url, params=None, timeout=None):
            captured.append((params or {}).get("where", ""))
            return {"features": [{"attributes": {"A": 1}}]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            permits.query_layer("https://x/MapServer/86",
                                base_where="CASE_STATUS IN ('1','4')")
        self.assertTrue(all("CASE_STATUS" in w for w in captured))

    def test_category_filter_endpoint(self):
        from flask import Flask
        app = Flask(__name__)
        permits.register_permits_routes(app)
        client = app.test_client()
        rows = [
            {"source_id": "mdc", "county": "Miami-Dade", "category": "permit",
             "permit_number": "P-1", "description": "RE-ROOF", "issued_date": _iso_days_ago(2),
             "value": 1000.0, "tags": ["roofing"]},
            {"source_id": "mdc_violations", "county": "Miami-Dade", "category": "violation",
             "permit_number": "V-1", "description": "UNSAFE STRUCTURE", "issued_date": _iso_days_ago(3),
             "value": None, "tags": ["unsafe_structure"]},
        ]
        def fake_fetch(source, record_count=2000, start_ms=None, end_ms=None):
            mine = [p for p in rows if p["source_id"] == source["id"]]
            return mine, {"id": source["id"], "county": source["county"],
                          "status": "ok" if mine else "empty", "count": len(mine)}
        with mock.patch.object(permits, "fetch_source", side_effect=fake_fetch):
            permits._cache.clear()
            allrows = client.get("/api/permits/search?county=miami-dade&days=90").get_json()
            permits._cache.clear()
            viol = client.get("/api/permits/search?county=miami-dade&days=90&category=violation").get_json()
        self.assertEqual({p["permit_number"] for p in allrows["permits"]}, {"P-1", "V-1"})
        self.assertEqual([p["permit_number"] for p in viol["permits"]], ["V-1"])


class WindowTests(unittest.TestCase):
    NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

    def test_default_is_30_days(self):
        s, e, label = permits.compute_window({}, self.NOW)
        self.assertEqual((self.NOW - s).days, 30)
        self.assertEqual(label, "last 30 days")

    def test_days(self):
        s, e, label = permits.compute_window({"days": "7"}, self.NOW)
        self.assertEqual((self.NOW - s).days, 7)

    def test_months(self):
        s, e, label = permits.compute_window({"months": "6"}, self.NOW)
        self.assertEqual((s.year, s.month, s.day), (2026, 1, 14))
        self.assertEqual(label, "last 6 months")

    def test_months_crossing_year_boundary(self):
        s, _, _ = permits.compute_window({"months": "9"}, self.NOW)
        self.assertEqual((s.year, s.month), (2025, 10))

    def test_years(self):
        s, _, label = permits.compute_window({"years": "2"}, self.NOW)
        self.assertEqual(s.year, 2024)
        self.assertEqual(label, "last 2 years")

    def test_specific_year(self):
        s, e, label = permits.compute_window({"year": "2023"}, self.NOW)
        self.assertEqual(s.strftime("%Y-%m-%d"), "2023-01-01")
        self.assertEqual(e.strftime("%Y-%m-%d"), "2023-12-31")
        self.assertEqual(label, "2023")

    def test_current_year_clamped_to_now(self):
        s, e, _ = permits.compute_window({"year": "2026"}, self.NOW)
        self.assertEqual(e, self.NOW)  # not Dec 31 in the future

    def test_explicit_start_end(self):
        s, e, _ = permits.compute_window({"start": "2022-03-01", "end": "2022-06-30"}, self.NOW)
        self.assertEqual(s.strftime("%Y-%m-%d"), "2022-03-01")
        self.assertEqual(e.strftime("%Y-%m-%d"), "2022-06-30")

    def test_future_year_clamped(self):
        s, e, _ = permits.compute_window({"year": "3000"}, self.NOW)
        self.assertLessEqual(s.year, self.NOW.year)


class DateQueryTests(unittest.TestCase):
    def test_server_side_date_where_and_pagination(self):
        calls = []
        def world(url, params=None, timeout=None):
            calls.append(dict(params or {}))
            p = params or {}
            if p.get("returnCountOnly"):
                # accept the first (TIMESTAMP) dialect
                return {"count": 10} if "TIMESTAMP" in p.get("where", "") else {"error": {"message": "bad"}}
            offset = int(p.get("resultOffset") or 0)
            if offset == 0:
                return {"features": [{"attributes": {"A": i}} for i in range(2000)],
                        "exceededTransferLimit": True}
            return {"features": [{"attributes": {"A": 9001}}]}  # second page
        with mock.patch.object(permits, "_get_json", side_effect=world):
            feats = permits.query_layer("https://x/FeatureServer/0", order_field="D",
                                        date_field="D", start_ms=1_600_000_000_000,
                                        end_ms=1_700_000_000_000, max_records=4000)
        self.assertEqual(len(feats), 2001)  # paginated across two pages
        used = [c for c in calls if not c.get("returnCountOnly")][0]["where"]
        self.assertIn("TIMESTAMP", used)   # server-side date filter applied

    def test_zero_row_date_filter_falls_back_to_unfiltered(self):
        """Regression: a date WHERE that is ACCEPTED but matches 0 rows (dialect
        or type mismatch) must fall through to the unfiltered newest-first pull,
        not report the layer as empty."""
        def world(url, params=None, timeout=None):
            p = params or {}
            where = p.get("where", "")
            if where != "1=1":
                return {"features": []}          # filter matches nothing
            return {"features": [{"attributes": {"PN": "A-1"}},
                                 {"attributes": {"PN": "A-2"}}]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            feats = permits.query_layer("https://x/FeatureServer/0", order_field="D",
                                        date_field="D", start_ms=1_600_000_000_000,
                                        end_ms=1_700_000_000_000)
        self.assertEqual(len(feats), 2)  # did NOT report empty

    def test_date_where_falls_back_to_unfiltered(self):
        def world(url, params=None, timeout=None):
            p = params or {}
            if p.get("returnCountOnly"):
                return {"error": {"message": "no date sql"}}  # all dialects rejected
            if p.get("where") != "1=1":
                return {"error": {"message": "still bad"}}
            return {"features": [{"attributes": {"A": 1}}]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            feats = permits.query_layer("https://x/FeatureServer/0", date_field="D",
                                        start_ms=1_600_000_000_000)
        self.assertEqual(len(feats), 1)  # gracefully fell back to where=1=1


class HubDatasetResolveTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    def test_resolves_dataset_id_to_layer_url(self):
        resp = {"data": {"attributes": {
            "url": "https://svc.example/arcgis/rest/services/BP/FeatureServer",
            "layer": {"id": 0}}}}
        with mock.patch.object(permits, "_get_json", return_value=resp):
            url = permits.resolve_hub_dataset_id("abc123_0")
        self.assertEqual(url, "https://svc.example/arcgis/rest/services/BP/FeatureServer/0")

    def test_layer_id_from_suffix_when_missing(self):
        resp = {"data": {"attributes": {
            "url": "https://svc.example/arcgis/rest/services/BP/FeatureServer"}}}
        with mock.patch.object(permits, "_get_json", return_value=resp):
            url = permits.resolve_hub_dataset_id("abc123_3")
        self.assertTrue(url.endswith("/FeatureServer/3"))

    def test_no_service_url_returns_none(self):
        with mock.patch.object(permits, "_get_json", return_value={"data": {"attributes": {}}}):
            self.assertIsNone(permits.resolve_hub_dataset_id("abc_0"))


class BlocklistTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    def test_known_false_positive_orgs_blocked(self):
        for bad in [
            "https://services6.arcgis.com/ONZht79c8QWuX759/arcgis/rest/services/Building_Permits/FeatureServer/0",
            "https://gis.palmbayflorida.org/arcgis/rest/services/GrowthManagement/BuildingPermits/FeatureServer/0",
            "https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/building_permits/FeatureServer/0",
        ]:
            self.assertTrue(permits._is_blocked(bad), bad)
        self.assertFalse(permits._is_blocked(
            "https://gis.fortlauderdale.gov/arcgis/rest/services/BuildingPermitTracker/BuildingPermitTracker/MapServer/0"))

    def test_blocked_layer_skipped_in_fetch(self):
        good = "https://gis.example/arcgis/rest/services/BP/FeatureServer/0"
        def world(url, params=None, timeout=None):
            if "ONZht79c8QWuX759" in url:
                raise AssertionError("blocked layer must never be requested")
            if url.endswith("/query"):
                p = params or {}
                if p.get("returnCountOnly"):
                    return {"count": 1}
                return {"features": [{"attributes": {
                    "PERMITNUMBER": "G-1", "DESCRIPTION": "REROOF",
                    "ISSUEDDATE": _epoch_ms_days_ago(1)}}]}
            return {"name": "BP", "fields": [
                {"name": "PERMITNUMBER", "type": "esriFieldTypeString"},
                {"name": "DESCRIPTION", "type": "esriFieldTypeString"},
                {"name": "ISSUEDDATE", "type": "esriFieldTypeDate"}]}
        src = {"id": "t", "county": "Broward", "label": "T", "kind": "arcgis_layer",
               "layer_urls": [
                   "https://services6.arcgis.com/ONZht79c8QWuX759/arcgis/rest/services/Building_Permits/FeatureServer/0",
                   good]}
        with mock.patch.object(permits, "_get_json", side_effect=world):
            rows, info = permits.fetch_source(src)
        self.assertEqual(info["status"], "ok")
        self.assertEqual(info["layer_url"], good)
        self.assertEqual(rows[0]["permit_number"], "G-1")


class HubV3DiscoveryTests(unittest.TestCase):
    def setUp(self):
        permits._cache.clear()

    RESP = {"data": [
        {"id": "aaaa_0", "attributes": {
            "name": "Building Permit", "source": "Miami-Dade County",
            "url": "https://svc.example/arcgis/rest/services/BP/FeatureServer",
            "layer": {"id": 0}}},
        {"id": "bbbb_2", "attributes": {
            "name": "Building Permits", "orgName": "City of Raleigh",  # wrong county
            "url": "https://svc.example/arcgis/rest/services/RAL/FeatureServer"}},
        {"id": "cccc_0", "attributes": {
            "name": "Well Permits", "source": "Miami-Dade",           # negative filter
            "url": "https://svc.example/arcgis/rest/services/Well/FeatureServer"}},
    ]}

    def test_county_gating_and_layer_url(self):
        with mock.patch.object(permits, "_get_json", return_value=self.RESP):
            found = permits.discover_via_hub_search("building permit",
                                                    permits.COUNTY_TOKENS["Miami-Dade"])
        self.assertEqual(len(found), 1)  # Raleigh + Well filtered out
        self.assertTrue(found[0]["layer_url"].endswith("/FeatureServer/0"))
        self.assertEqual(found[0]["title"], "Building Permit")

    def test_miami_dade_recovers_via_v3_when_items_dead(self):
        """The real-world MDC failure: items restricted/removed + DCAT malformed.
        v3 search should still find the layer and the source goes green."""
        def world(url, params=None, timeout=None):
            if "Building_Permits/FeatureServer" in url:
                raise Exception("pinned layer 503")            # direct layer down
            if "content/items" in url:
                raise Exception("You do not have permissions")
            if "hub.arcgis.com/api/v3" in url:
                return self.RESP
            if "dcat" in url or url.endswith("data.json"):
                raise Exception("Expecting ',' delimiter")  # malformed feed
            if url.endswith("/query"):
                p = params or {}
                if p.get("returnCountOnly"):
                    return {"count": 3}
                return {"features": [{"attributes": {
                    "PERMITNUMBER": "MDC-1", "DESCRIPTION": "NEW POOL",
                    "ISSUINGDATE": _epoch_ms_days_ago(3)}}]}
            return {"name": "BP", "fields": [
                {"name": "PERMITNUMBER", "type": "esriFieldTypeString"},
                {"name": "DESCRIPTION", "type": "esriFieldTypeString"},
                {"name": "ISSUINGDATE", "type": "esriFieldTypeDate"}]}
        mdc = [s for s in permits.DEFAULT_SOURCES if s["id"] == "mdc"][0]
        with mock.patch.object(permits, "_get_json", side_effect=world):
            rows, info = permits.fetch_source(dict(mdc), start_ms=1, end_ms=None)
        self.assertEqual(info["status"], "ok")
        self.assertEqual(rows[0]["permit_number"], "MDC-1")
        self.assertIn("pool_spa", rows[0]["tags"])


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
        def fake_fetch(source, record_count=2000, start_ms=None, end_ms=None):
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

    def test_no_demo_when_source_ok_but_zero_rows(self):
        """A source that succeeds but honestly returns 0 rows must NOT be masked
        with fabricated demo data (regression: 'open violations last 7 days')."""
        def ok_empty(source, record_count=2000, start_ms=None, end_ms=None):
            return [], {"id": source["id"], "county": source["county"],
                        "label": source.get("label"), "status": "ok", "count": 0}
        with mock.patch.object(permits, "fetch_source", side_effect=ok_empty):
            r = self.client.get("/api/permits/search?county=miami-dade&days=7")
        data = r.get_json()
        self.assertFalse(data["demo"])       # no fabricated rows
        self.assertEqual(data["count"], 0)   # truthful empty

    def test_search_demo_fallback_when_all_sources_fail(self):
        def dead_fetch(source, record_count=2000, start_ms=None, end_ms=None):
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
        self.assertEqual(set(ids),
                         {"mdc", "mdc_violations", "ftl", "boca", "broward_uninc",
                          "pbc", "martin", "martin_dev"})
        self.assertEqual(data["counties"], permits.COUNTIES)
        # every county still represented by at least one source
        counties = {s["county"] for s in data["sources"]}
        self.assertEqual(counties, set(permits.COUNTIES))

    def test_csv_export(self):
        with self._patch_live():
            r = self.client.get("/api/permits/export.csv?days=90")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.content_type)
        body = r.get_data(as_text=True)
        lines = body.strip().splitlines()
        self.assertEqual(len(lines), 4)  # header + 3 rows
        self.assertTrue(lines[0].startswith("issued_date,category,county,city,permit_number"))
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
            if r["category"] == "permit":
                self.assertIsNotNone(r["value"])  # violations have no job value

    def test_demo_includes_violations(self):
        rows = permits.demo_permits()
        vios = [r for r in rows if r["category"] == "violation"]
        self.assertGreaterEqual(len(vios), 3)
        self.assertTrue(any("unsafe_structure" in r["tags"] for r in vios))
        self.assertTrue(any("no_permit" in r["tags"] for r in vios))


if __name__ == "__main__":
    unittest.main(verbosity=2)

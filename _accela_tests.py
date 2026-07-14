"""
Offline tests for the Accela Citizen Access scraper (api/accela.py).

The live network handshake against aca-prod.accela.com can't run in this
sandbox, but every PARSING/EXTRACTION step is deterministic and tested here
against a realistic ACA HTML fixture, plus the full scrape flow with the
network mocked. Run: python3 _accela_tests.py
"""

import sys
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, "api")
import accela  # noqa: E402


# A trimmed-but-realistic Accela ACA "General Search" page + results grid.
SEARCH_PAGE = """
<html><body>
<form method="post" action="./CapHome.aspx?module=Building&TabName=Building" id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" value="/wEPDwUKabc123" />
<input type="hidden" name="__VIEWSTATEGENERATOR" value="CA0B0334" />
<input type="hidden" name="__EVENTVALIDATION" value="/wEdAAxyz789" />
<input type="hidden" name="__EVENTTARGET" value="" />
<input type="hidden" name="__EVENTARGUMENT" value="" />
<span>General Search</span>
<input name="ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate"
       id="ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate" type="text" />
<input name="ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate"
       id="ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate" type="text" />
<input type="submit" name="ctl00$PlaceHolderMain$btnNewSearch"
       value="Search" id="ctl00_PlaceHolderMain_btnNewSearch" />
</form></body></html>
"""

RESULTS_PAGE = """
<html><body>
<form method="post" id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" value="/wEPDwUKresults" />
<input type="hidden" name="__VIEWSTATEGENERATOR" value="CA0B0334" />
<input type="hidden" name="__EVENTVALIDATION" value="/wEdAAresults" />
<table class="ACA_GridView">
  <tr><th>Date</th><th>Record Number</th><th>Record Type</th>
      <th>Project Name</th><th>Address</th><th>Status</th></tr>
  <tr><td>07/10/2026</td><td>BLD-2026-00123</td><td>Building Residential</td>
      <td>RE-ROOF SHINGLE 24 SQ</td><td>900 SE OCEAN BLVD, STUART</td><td>Issued</td></tr>
  <tr><td>07/09/2026</td><td>BLD-2026-00124</td><td>Building Residential</td>
      <td>NEW SWIMMING POOL AND SPA</td><td>2201 SW MAPP RD, PALM CITY</td><td>Issued</td></tr>
  <tr><td>07/08/2026</td><td>BLD-2026-00125</td><td>Building Mechanical</td>
      <td>A/C CHANGEOUT 4 TON</td><td>35 SW FLAGLER AVE, STUART</td><td>Finaled</td></tr>
</table>
<a href="javascript:__doPostBack(&#39;ctl00$PlaceHolderMain$dgvPermitList$gdvPermitList&#39;,&#39;Page$2&#39;)">2</a>
</form></body></html>
"""

RESULTS_PAGE_2 = """
<html><body><form id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" value="/wEPDwpage2" />
<input type="hidden" name="__EVENTVALIDATION" value="/wEdpage2" />
<table class="ACA_GridView">
  <tr><th>Date</th><th>Record Number</th><th>Record Type</th>
      <th>Project Name</th><th>Address</th><th>Status</th></tr>
  <tr><td>07/07/2026</td><td>BLD-2026-00126</td><td>Building Residential</td>
      <td>IMPACT WINDOWS 12 OPENINGS</td><td>8735 SE BRIDGE RD, HOBE SOUND</td><td>Issued</td></tr>
</table>
</form></body></html>
"""


class HiddenFieldTests(unittest.TestCase):
    def test_extracts_aspnet_state(self):
        f = accela.extract_hidden_fields(SEARCH_PAGE)
        self.assertEqual(f["__VIEWSTATE"], "/wEPDwUKabc123")
        self.assertEqual(f["__VIEWSTATEGENERATOR"], "CA0B0334")
        self.assertIn("__EVENTVALIDATION", f)
        self.assertEqual(f["__EVENTTARGET"], "")


class FieldDiscoveryTests(unittest.TestCase):
    def test_finds_date_inputs_by_pattern(self):
        s = accela.find_input_name(SEARCH_PAGE, "StartDate")
        e = accela.find_input_name(SEARCH_PAGE, "EndDate")
        self.assertIn("txtGSStartDate", s)
        self.assertIn("txtGSEndDate", e)

    def test_ignores_hidden_and_submit_inputs(self):
        # __VIEWSTATE is hidden; must not be returned as a date field
        self.assertIsNone(accela.find_input_name(SEARCH_PAGE, "VIEWSTATE"))

    def test_finds_search_submit_trigger(self):
        kind, name, value = accela.find_search_trigger(SEARCH_PAGE)
        self.assertEqual(kind, "submit")
        self.assertIn("btnNewSearch", name)
        self.assertEqual(value, "Search")


class TableParseTests(unittest.TestCase):
    def test_parses_results_grid(self):
        rows = accela.parse_result_rows(RESULTS_PAGE)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["Record Number"], "BLD-2026-00123")
        self.assertEqual(rows[0]["Address"], "900 SE OCEAN BLVD, STUART")

    def test_ignores_non_result_tables(self):
        html = ("<table><tr><th>Nav</th></tr><tr><td>Home</td></tr></table>"
                + RESULTS_PAGE)
        rows = accela.parse_result_rows(html)
        self.assertEqual(len(rows), 3)  # picked the permit grid, not the nav table

    def test_pagination_targets(self):
        targets = accela.find_pagination_targets(RESULTS_PAGE)
        self.assertTrue(any(p == "Page$2" for _, p in targets))

    def test_no_table_is_safe(self):
        self.assertEqual(accela.parse_result_rows("<html>nothing</html>"), [])


class MappingTests(unittest.TestCase):
    def test_maps_columns_to_canonical(self):
        rows = accela.parse_result_rows(RESULTS_PAGE)
        m = accela.map_row(rows[0])
        self.assertEqual(m["permit_number"], "BLD-2026-00123")
        self.assertEqual(m["issued_date"], "07/10/2026")
        self.assertEqual(m["description"], "RE-ROOF SHINGLE 24 SQ")
        self.assertEqual(m["address"], "900 SE OCEAN BLVD, STUART")
        self.assertEqual(m["status"], "Issued")

    def test_date_parsing(self):
        self.assertEqual(accela._parse_aca_date("07/10/2026"), "2026-07-10")
        self.assertEqual(accela._parse_aca_date("7/9/26"), "2026-07-09")
        self.assertIsNone(accela._parse_aca_date("n/a"))


class ScrapeFlowTests(unittest.TestCase):
    def _mock_session(self, get_html, post_htmls):
        posts = list(post_htmls)

        class R:
            def __init__(self, text):
                self.status_code = 200
                self.text = text

        sess = mock.MagicMock()
        sess.get.return_value = R(get_html)
        sess.post.side_effect = [R(h) for h in posts]
        return sess

    def test_full_scrape_two_pages(self):
        sess = self._mock_session(SEARCH_PAGE, [RESULTS_PAGE, RESULTS_PAGE_2])
        with mock.patch.object(accela, "_session", return_value=sess):
            rows, diag = accela.scrape_accela(
                "MARTINCO",
                datetime(2026, 6, 1, tzinfo=timezone.utc),
                datetime(2026, 7, 14, tzinfo=timezone.utc))
        self.assertIsNone(diag.get("error"))
        self.assertEqual(len(rows), 4)             # 3 + 1 across two pages
        self.assertEqual(diag["pages"], 2)
        self.assertEqual(rows[0]["permit_number"], "BLD-2026-00123")
        self.assertEqual(rows[0]["issued_date"], "2026-07-10")
        # the POST carried the discovered date fields + search trigger
        first_post = sess.post.call_args_list[0]
        data = first_post.kwargs.get("data") or first_post.args[1]
        self.assertTrue(any("StartDate" in k for k in data))
        self.assertTrue(any("btnNewSearch" in k for k in data))

    def test_scrape_reports_missing_date_fields(self):
        page = "<html><form><input type=hidden name=__VIEWSTATE value=x></form></html>"
        sess = self._mock_session(page, [])
        with mock.patch.object(accela, "_session", return_value=sess):
            rows, diag = accela.scrape_accela(
                "MARTINCO", datetime(2026, 6, 1, tzinfo=timezone.utc),
                datetime(2026, 7, 14, tzinfo=timezone.utc))
        self.assertEqual(rows, [])
        self.assertIn("date-range inputs", diag["error"])

    def test_scrape_handles_http_error(self):
        class R:
            status_code = 500
            text = ""
        sess = mock.MagicMock()
        sess.get.return_value = R()
        with mock.patch.object(accela, "_session", return_value=sess):
            rows, diag = accela.scrape_accela(
                "MARTINCO", datetime(2026, 6, 1, tzinfo=timezone.utc),
                datetime(2026, 7, 14, tzinfo=timezone.utc))
        self.assertEqual(rows, [])
        self.assertIn("500", diag["error"])

    def test_scrape_never_raises_on_exception(self):
        sess = mock.MagicMock()
        sess.get.side_effect = RuntimeError("boom")
        with mock.patch.object(accela, "_session", return_value=sess):
            rows, diag = accela.scrape_accela(
                "MARTINCO", datetime(2026, 6, 1, tzinfo=timezone.utc),
                datetime(2026, 7, 14, tzinfo=timezone.utc))
        self.assertEqual(rows, [])
        self.assertIn("boom", diag["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

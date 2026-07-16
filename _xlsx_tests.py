"""
Offline tests for the XLSX-index permit source (api/xlsx_source.py) — used for
City of Boca Raton's published permit spreadsheets. Network mocked; xlsx parsing
runs against a real in-memory workbook. Run: python3 _xlsx_tests.py
"""

import io
import sys
import unittest
from datetime import datetime
from unittest import mock

sys.path.insert(0, "api")
import xlsx_source  # noqa: E402

INDEX_HTML = """
<html><body>
<h1>Applied/Issued Permits</h1>
<ul>
  <li><a href="/DocumentCenter/View/50001/AppliedPermits_2026-07-01-xlsx">AppliedPermits_2026-07-01.xlsx</a></li>
  <li><a href="/DocumentCenter/View/50000/AppliedPermits_2026-06-01-xlsx">AppliedPermits_2026-06-01.xlsx</a></li>
  <li><a href="/DocumentCenter/View/49900/IssuedPermits_2026-07-01-xlsx">IssuedPermits_2026-07-01.xlsx</a></li>
  <li><a href="/DocumentCenter/View/40000/AppliedPermits_2022-01-03-xlsx">AppliedPermits_2022-01-03.xlsx</a></li>
  <li><a href="/Home/Contact">Contact Us</a></li>
  <li><a href="/DocumentCenter/View/123/Zoning-Map-pdf">Zoning Map.pdf</a></li>
</ul>
</body></html>
"""


def _make_xlsx(headers, rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class LinkExtractionTests(unittest.TestCase):
    def test_extracts_permit_xlsx_links_only(self):
        links = xlsx_source.extract_xlsx_links(INDEX_HTML, "https://www.myboca.us/2487/AppliedIssued-Permits")
        texts = [l["text"] for l in links]
        self.assertIn("AppliedPermits_2026-07-01.xlsx", texts)
        self.assertIn("IssuedPermits_2026-07-01.xlsx", texts)
        self.assertNotIn("Contact Us", texts)          # no "permit" in it
        self.assertNotIn("Zoning Map.pdf", texts)       # not a permit file
        self.assertEqual(len(links), 4)

    def test_absolutizes_and_dates(self):
        links = xlsx_source.extract_xlsx_links(INDEX_HTML, "https://www.myboca.us/2487/AppliedIssued-Permits")
        first = [l for l in links if "2026-07-01" in l["text"] and l["kind"] == "applied"][0]
        self.assertTrue(first["url"].startswith("https://www.myboca.us/DocumentCenter/View/50001/"))
        self.assertEqual(first["date"], datetime(2026, 7, 1))
        self.assertEqual(first["kind"], "applied")
        issued = [l for l in links if l["kind"] == "issued"][0]
        self.assertIn("Issued", issued["text"])


class FileSelectionTests(unittest.TestCase):
    def test_picks_recent_files_in_window(self):
        links = xlsx_source.extract_xlsx_links(INDEX_HTML, "https://www.myboca.us/x")
        chosen = xlsx_source._pick_files(links, datetime(2026, 6, 1), datetime(2026, 7, 31), max_files=4)
        dates = sorted(l["date"] for l in chosen)
        self.assertIn(datetime(2026, 7, 1), dates)
        self.assertIn(datetime(2026, 6, 1), dates)
        self.assertNotIn(datetime(2022, 1, 3), dates)   # far outside window
        # newest-first ordering
        self.assertEqual(chosen[0]["date"], max(l["date"] for l in chosen))

    def test_caps_file_count(self):
        links = xlsx_source.extract_xlsx_links(INDEX_HTML, "https://www.myboca.us/x")
        chosen = xlsx_source._pick_files(links, datetime(2020, 1, 1), datetime(2027, 1, 1), max_files=2)
        self.assertLessEqual(len(chosen), 2)


class XlsxParseTests(unittest.TestCase):
    def test_parses_and_maps_columns(self):
        content = _make_xlsx(
            ["Permit Number", "Address", "Work Description", "Applied Date", "Status",
             "Permit Type", "Contractor Name", "Valuation"],
            [["B26-001", "100 NE 1 AVE", "RE-ROOF SHINGLE 20SQ", datetime(2026, 7, 1),
              "Issued", "Building", "ABC ROOFING", 18000],
             ["B26-002", "200 SW 2 ST", "NEW POOL", "2026-07-02", "Applied",
              "Pool", "BLUE POOLS", "$52,000"]])
        rows, headers = xlsx_source.parse_xlsx(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["permit_number"], "B26-001")
        self.assertEqual(rows[0]["address"], "100 NE 1 AVE")
        self.assertEqual(rows[0]["description"], "RE-ROOF SHINGLE 20SQ")
        self.assertEqual(rows[0]["applied_date"], "2026-07-01")   # datetime -> iso
        self.assertEqual(rows[0]["contractor"], "ABC ROOFING")
        self.assertEqual(rows[1]["value"], "$52,000")

    def test_skips_blank_and_headerless(self):
        content = _make_xlsx(["Permit Number", "Address"],
                             [[None, None], ["B1", "1 MAIN ST"], ["", ""]])
        rows, _ = xlsx_source.parse_xlsx(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["permit_number"], "B1")

    def test_garbage_bytes_safe(self):
        rows, headers = xlsx_source.parse_xlsx(b"not a real xlsx")
        self.assertEqual(rows, [])
        self.assertEqual(headers, [])


class FetchFlowTests(unittest.TestCase):
    def _mock_session(self, index_html, file_bytes):
        class R:
            def __init__(self, text=None, content=None, code=200):
                self.status_code = code
                self.text = text or ""
                self.content = content or b""
        sess = mock.MagicMock()
        def get(url, timeout=None):
            if "AppliedIssued-Permits" in url:
                return R(text=index_html)
            return R(content=file_bytes)
        sess.get.side_effect = get
        return sess

    def test_full_fetch(self):
        content = _make_xlsx(
            ["Permit #", "Site Address", "Description", "Issue Date", "Status"],
            [["B26-100", "500 E PALMETTO PARK RD", "IMPACT WINDOWS 10 OPENINGS",
              datetime(2026, 7, 5), "Issued"]])
        sess = self._mock_session(INDEX_HTML, content)
        with mock.patch.object(xlsx_source, "_session", return_value=sess):
            rows, diag = xlsx_source.fetch_xlsx_index(
                "https://www.myboca.us/2487/AppliedIssued-Permits",
                datetime(2026, 6, 1), datetime(2026, 7, 31))
        self.assertIsNone(diag.get("error"))
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]["permit_number"], "B26-100")
        self.assertEqual(rows[0]["issue_date"], "2026-07-05")
        self.assertTrue(diag["files_chosen"])

    def test_index_http_error(self):
        class R:
            status_code = 404
            text = ""
        sess = mock.MagicMock()
        sess.get.return_value = R()
        with mock.patch.object(xlsx_source, "_session", return_value=sess):
            rows, diag = xlsx_source.fetch_xlsx_index(
                "https://www.myboca.us/2487/AppliedIssued-Permits",
                datetime(2026, 6, 1), datetime(2026, 7, 31))
        self.assertEqual(rows, [])
        self.assertIn("404", diag["error"])

    def test_never_raises(self):
        sess = mock.MagicMock()
        sess.get.side_effect = RuntimeError("boom")
        with mock.patch.object(xlsx_source, "_session", return_value=sess):
            rows, diag = xlsx_source.fetch_xlsx_index(
                "https://www.myboca.us/x", datetime(2026, 6, 1), datetime(2026, 7, 31))
        self.assertEqual(rows, [])
        self.assertIn("boom", diag["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

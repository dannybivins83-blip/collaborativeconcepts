"""
Offline tests for the Click2Gov adapter (api/click2gov.py). No network — a fake
session serves fixture HTML that mirrors a real Click2GovBP "Select Permit" page
(CSRF hidden field + address search form) and a results table. Run:
    python3 _click2gov_tests.py
"""
import sys
import unittest

sys.path.insert(0, "api")
import click2gov  # noqa: E402

# --- fixtures -------------------------------------------------------------
SEARCH_PAGE = """
<html><body>
<form name="searchForm" method="post" action="permitSearchResults.html">
  <input type="hidden" name="OWASP_CSRFTOKEN" value="ABCD-1234-EF56-7890">
  <input type="hidden" name="searchType" value="address">
  <label>Application Number</label>
  <input type="text" name="applicationNumber" id="applicationNumber">
  <label>Street Number</label>
  <input type="text" name="streetNumber" id="streetNumber">
  <label>Street Name</label>
  <input type="text" name="streetName" id="streetName">
  <label>Parcel Number</label>
  <input type="text" name="parcelNumber" id="parcelNumber">
  <input type="submit" name="btnSearch" value="Search">
</form>
</body></html>
"""

RESULTS_PAGE = """
<html><body>
<table>
  <tr><th>Permit Number</th><th>Type</th><th>Address</th>
      <th>Status</th><th>Issue Date</th><th>Description</th></tr>
  <tr><td>SOLR-22-0456</td><td>Solar</td><td>810 N A ST</td>
      <td>Issued</td><td>03/14/2023</td><td>ROOF MOUNT PV 8KW</td></tr>
</table>
</body></html>
"""

EMPTY_RESULTS = """
<html><body><p>No records found matching your search.</p></body></html>
"""


class FakeResp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status


class FakeSession:
    """Serves the search page on GET and a configurable page on POST."""
    def __init__(self, post_page=RESULTS_PAGE):
        self.post_page = post_page
        self.cookies = []
        self.headers = {}
        self.posted = None

    def get(self, url, timeout=None):
        return FakeResp(SEARCH_PAGE)

    def post(self, url, data=None, timeout=None, headers=None):
        self.posted = {"url": url, "data": data}
        return FakeResp(self.post_page)


class ParseFormTests(unittest.TestCase):
    def test_discovers_fields_and_action(self):
        form = click2gov.parse_search_form(SEARCH_PAGE)
        self.assertEqual(form["action"], "permitSearchResults.html")
        self.assertEqual(form["method"], "post")
        self.assertEqual(form["address_fields"]["num"], "streetNumber")
        self.assertEqual(form["address_fields"]["street"], "streetName")
        # hidden fields are carried
        self.assertIn("searchType", form["fields"])

    def test_csrf_extracted(self):
        tok = click2gov._find_csrf(SEARCH_PAGE, FakeSession())
        self.assertEqual(tok, "ABCD-1234-EF56-7890")

    def test_no_form(self):
        self.assertIsNone(click2gov.parse_search_form("<html><body>nope</body></html>"))


class AbsUrlTests(unittest.TestCase):
    def test_relative(self):
        u = click2gov._abs_url("https://byb2-egov.aspgov.com", "/Click2GovBP",
                               "permitSearchResults.html")
        self.assertEqual(u, "https://byb2-egov.aspgov.com/Click2GovBP/permitSearchResults.html")

    def test_root_relative(self):
        u = click2gov._abs_url("https://x.aspgov.com", "/Click2GovBP", "/Click2GovBP/go.html")
        self.assertEqual(u, "https://x.aspgov.com/Click2GovBP/go.html")

    def test_split_street(self):
        self.assertEqual(click2gov._split_street("810 N A ST"), ("810", "N A ST"))
        self.assertEqual(click2gov._split_street("N A ST"), ("", "N A ST"))


class LookupTests(unittest.TestCase):
    def test_lookup_hit(self):
        rows, diag = click2gov.lookup_address(
            "https://byb2-egov.aspgov.com", "810", "N A ST",
            session=FakeSession(RESULTS_PAGE))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["permit_number"], "SOLR-22-0456")
        self.assertEqual(rows[0]["address"], "810 N A ST")
        self.assertEqual(diag["mapped"], 1)

    def test_lookup_posts_address_into_discovered_field(self):
        sess = FakeSession(RESULTS_PAGE)
        click2gov.lookup_address("https://byb2-egov.aspgov.com", "810", "N A ST",
                                 session=sess)
        self.assertEqual(sess.posted["data"]["streetName"], "N A ST")
        self.assertEqual(sess.posted["data"]["streetNumber"], "810")
        self.assertEqual(sess.posted["data"]["OWASP_CSRFTOKEN"], "ABCD-1234-EF56-7890")

    def test_lookup_miss(self):
        rows, diag = click2gov.lookup_address(
            "https://x.aspgov.com", "999", "NOWHERE RD",
            session=FakeSession(EMPTY_RESULTS))
        self.assertEqual(rows, [])
        self.assertEqual(diag["rows_parsed"], 0)

    def test_never_raises_on_error(self):
        class Boom:
            cookies = []
            headers = {}
            def get(self, *a, **k):
                raise click2gov.requests.RequestException("down")
        rows, diag = click2gov.lookup_address("https://x", "1", "MAIN ST", session=Boom())
        self.assertEqual(rows, [])
        self.assertIn("error", diag)


class LookupManyTests(unittest.TestCase):
    def test_batch_respects_max(self):
        # patch _session so the batch uses our fake
        orig = click2gov._session
        click2gov._session = lambda: FakeSession(RESULTS_PAGE)
        try:
            addrs = [{"address": "%d N A ST" % i} for i in range(10)]
            results, diag = click2gov.lookup_many(
                "https://byb2-egov.aspgov.com", addrs, max_lookups=3)
        finally:
            click2gov._session = orig
        self.assertEqual(len(results), 3)
        self.assertEqual(diag["stopped"], "max_lookups")
        self.assertTrue(all(r["matched"] for r in results))


if __name__ == "__main__":
    unittest.main(verbosity=2)

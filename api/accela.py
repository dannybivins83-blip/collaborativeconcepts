"""
Accela Citizen Access (ACA) scraper.

For jurisdictions that publish building permits ONLY through the Accela ASP.NET
portal (e.g. Martin County = MARTINCO) with no GIS/API feed. ACA is a WebForms
app, so this:
  1. GETs the Building "General Search" page and harvests the ASP.NET hidden
     fields (__VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATION, ...).
  2. Discovers the date-range inputs and the search trigger BY PATTERN (matching
     field names/labels), not by hardcoded ASP.NET control IDs — so it survives
     the ID drift between ACA versions.
  3. POSTs a date-range search and parses the results GridView, mapping columns
     by header text.
  4. Follows result pagination (a capped number of __doPostBack pages).

This is best-effort and inherently fragile (portal HTML changes, disclaimer
gates, per-search caps). It NEVER raises — it returns (rows, diagnostics) so the
caller can surface exactly what happened. Standard library + requests only.
"""

import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

UA = "CollaborativeConcepts-PermitLeads/1.0 (+https://collaborativeconceptsfl.com)"
ACA_BASE = "https://aca-prod.accela.com"
TIMEOUT = 8
MAX_PAGES = 3
DEFAULT_DEADLINE = 18   # seconds — hard wall-clock cap so a slow portal can't
                        # eat the whole serverless budget (was unbounded ~135s)


# --------------------------------------------------------------------------
# HTML helpers (stdlib only)
# --------------------------------------------------------------------------
_HIDDEN_RX = re.compile(
    r'<input[^>]*type=["\']hidden["\'][^>]*>', re.I)
_ATTR_NAME_RX = re.compile(r'\bname=["\']([^"\']+)["\']', re.I)
_ATTR_VALUE_RX = re.compile(r'\bvalue=["\']([^"\']*)["\']', re.I)
_ATTR_ID_RX = re.compile(r'\bid=["\']([^"\']+)["\']', re.I)


def extract_hidden_fields(html):
    """All <input type=hidden> as {name: value} — the ASP.NET state blob."""
    out = {}
    for tag in _HIDDEN_RX.findall(html or ""):
        nm = _ATTR_NAME_RX.search(tag)
        if not nm:
            continue
        val = _ATTR_VALUE_RX.search(tag)
        out[nm.group(1)] = val.group(1) if val else ""
    return out


def find_input_name(html, *keywords):
    """Name of the first text/date input whose name or id contains ALL of the
    given keywords (case-insensitive). Used to locate the date fields without
    knowing the exact ASP.NET control id."""
    for tag in re.findall(r'<input[^>]*>', html or "", re.I):
        if re.search(r'type=["\'](hidden|submit|image|checkbox|radio)["\']', tag, re.I):
            continue
        nm = _ATTR_NAME_RX.search(tag)
        if not nm:
            continue
        hay = (nm.group(1) + " " + (_ATTR_ID_RX.search(tag).group(1)
                                    if _ATTR_ID_RX.search(tag) else "")).lower()
        if all(k.lower() in hay for k in keywords):
            return nm.group(1)
    return None


def find_search_trigger(html):
    """Locate the search submit control. Returns ('submit', name, value) for a
    submit button, or ('postback', target) for a __doPostBack link/anchor."""
    # 1) a submit/image button whose name/value looks like Search
    for tag in re.findall(r'<input[^>]*>', html or "", re.I):
        if not re.search(r'type=["\'](submit|image)["\']', tag, re.I):
            continue
        nm = _ATTR_NAME_RX.search(tag)
        val = _ATTR_VALUE_RX.search(tag)
        blob = tag.lower()
        if nm and ("search" in blob):
            return ("submit", nm.group(1), val.group(1) if val else "Search")
    # 2) an anchor doing __doPostBack('<target>', ...) with Search-ish text
    for m in re.finditer(r'href=["\']javascript:__doPostBack\(&#39;([^&]+)&#39;'
                         r'|href=["\']javascript:__doPostBack\(\'([^\']+)\'', html or "", re.I):
        target = m.group(1) or m.group(2)
        if target and re.search(r'search|btnnewsearch|btnsearch', target, re.I):
            return ("postback", target)
    return (None, None, None) if True else None


class _TableCollector(HTMLParser):
    """Collect every table as a list of rows (each row a list of cell texts)."""
    def __init__(self):
        super().__init__()
        self.tables = []
        self._stack = []          # nested table rows
        self._cur_rows = None
        self._cur_row = None
        self._cur_cell = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append(self._cur_rows)
            self._cur_rows = []
        elif tag == "tr" and self._cur_rows is not None:
            self._cur_row = []
        elif tag in ("td", "th") and self._cur_row is not None:
            self._cur_cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cur_cell is not None:
            self._cur_row.append(" ".join("".join(self._cur_cell).split()))
            self._cur_cell = None
        elif tag == "tr" and self._cur_row is not None:
            self._cur_rows.append(self._cur_row)
            self._cur_row = None
        elif tag == "table" and self._cur_rows is not None:
            self.tables.append(self._cur_rows)
            self._cur_rows = self._stack.pop() if self._stack else None

    def handle_data(self, data):
        if self._cur_cell is not None:
            self._cur_cell.append(data)


_HEADER_HINTS = re.compile(r"date|record|permit|address|status|type|description|project", re.I)


def parse_result_rows(html):
    """Find the results table and return a list of {header: value} dicts.
    Picks the table whose header row has the most permit-like column names."""
    parser = _TableCollector()
    try:
        parser.feed(html or "")
    except Exception:
        return []
    best, best_score = None, 0
    for rows in parser.tables:
        if len(rows) < 2:
            continue
        header = rows[0]
        score = sum(1 for h in header if _HEADER_HINTS.search(h or "")) + \
            (len(rows) * 0.01)  # tie-break toward larger tables
        if score > best_score and any(_HEADER_HINTS.search(h or "") for h in header):
            best, best_score = rows, score
    if not best:
        return []
    header = [h.strip() for h in best[0]]
    out = []
    for row in best[1:]:
        if len(row) < 2 or all(not c for c in row):
            continue
        rec = {}
        for i, cell in enumerate(row):
            key = header[i] if i < len(header) and header[i] else f"col{i}"
            rec[key] = cell
        out.append(rec)
    return out


def find_pagination_targets(html):
    """__doPostBack targets for result pages (Page$2, Page$3, ...), deduped."""
    targets = []
    for m in re.finditer(r'__doPostBack\((?:&#39;|\')([^&\']+)(?:&#39;|\'),\s*'
                         r'(?:&#39;|\')(Page\$\d+)(?:&#39;|\')', html or "", re.I):
        pair = (m.group(1), m.group(2))
        if pair not in targets:
            targets.append(pair)
    return targets


# --------------------------------------------------------------------------
# Column mapping (results GridView -> canonical permit fields)
# --------------------------------------------------------------------------
_COL_MAP = [
    ("issued_date", re.compile(r"date", re.I)),
    ("permit_number", re.compile(r"record\s*#|record\s*num|permit\s*#|permit\s*num|record\b", re.I)),
    ("type", re.compile(r"record\s*type|permit\s*type|\btype\b", re.I)),
    ("description", re.compile(r"description|project\s*name|short\s*notes|\bproject\b", re.I)),
    ("address", re.compile(r"address", re.I)),
    ("status", re.compile(r"status", re.I)),
]


def map_row(rec):
    """Map one results-row dict (keyed by header text) to canonical fields."""
    out = {}
    for canon, rx in _COL_MAP:
        if canon in out:
            continue
        for header, value in rec.items():
            if rx.search(header or ""):
                out[canon] = value
                break
    return out


def _parse_aca_date(s):
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None


# --------------------------------------------------------------------------
# The scrape flow
# --------------------------------------------------------------------------
def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Accept": "text/html,application/xhtml+xml",
                      "Accept-Language": "en-US,en;q=0.9"})
    return s


def scrape_accela(agency, start_date, end_date, module="Building",
                  base=ACA_BASE, max_pages=MAX_PAGES, deadline=DEFAULT_DEADLINE):
    """Search an Accela ACA agency's General Search by date range.

    start_date/end_date: datetime (any tz). deadline: hard wall-clock seconds
    cap. Returns (rows, diag) where rows are canonical permit dicts and diag
    records exactly what happened at each step. Never raises.
    """
    import time as _time
    _start = _time.time()

    def _over_budget():
        return (_time.time() - _start) > deadline

    diag = {"agency": agency, "steps": [], "pages": 0}
    sess = _session()
    search_url = (f"{base}/{agency}/Cap/CapHome.aspx"
                  f"?module={module}&TabName={module}")
    sd = start_date.strftime("%m/%d/%Y")
    ed = end_date.strftime("%m/%d/%Y")

    try:
        if _over_budget():
            diag["error"] = "deadline exceeded before search"
            return [], diag
        r = sess.get(search_url, timeout=TIMEOUT)
        diag["steps"].append(f"GET search page: {r.status_code}")
        if r.status_code != 200:
            diag["error"] = f"search page HTTP {r.status_code}"
            return [], diag
        html = r.text
        if re.search(r"sign\s*in|log\s*in|username", html[:4000], re.I) and \
                not re.search(r"general\s*search|search\s*for", html, re.I):
            diag["error"] = "portal appears to require sign-in for search"
            return [], diag

        fields = extract_hidden_fields(html)
        start_field = find_input_name(html, "StartDate") or find_input_name(html, "GSStartDate")
        end_field = find_input_name(html, "EndDate") or find_input_name(html, "GSEndDate")
        diag["fields_found"] = {"start": start_field, "end": end_field,
                                "hidden_count": len(fields)}
        if not start_field or not end_field:
            diag["error"] = "could not locate date-range inputs on search form"
            return [], diag

        form = dict(fields)
        form[start_field] = sd
        form[end_field] = ed
        trigger = find_search_trigger(html)
        if trigger[0] == "submit":
            form[trigger[1]] = trigger[2]
            diag["steps"].append(f"submit via {trigger[1]}")
        elif trigger[0] == "postback":
            form["__EVENTTARGET"] = trigger[1]
            form["__EVENTARGUMENT"] = ""
            diag["steps"].append(f"postback target {trigger[1]}")
        else:
            # last resort: many ACA builds accept the well-known button name
            form["ctl00$PlaceHolderMain$btnNewSearch"] = "Search"
            diag["steps"].append("submit via default btnNewSearch")

        rows = []
        seen_pages = set()
        r = sess.post(search_url, data=form, timeout=TIMEOUT)
        diag["steps"].append(f"POST search: {r.status_code}")
        if r.status_code != 200:
            diag["error"] = f"search POST HTTP {r.status_code}"
            return [], diag
        html = r.text
        page_rows = parse_result_rows(html)
        rows.extend(page_rows)
        diag["pages"] = 1
        diag["first_page_rows"] = len(page_rows)

        # pagination
        for _ in range(max_pages - 1):
            if _over_budget():
                diag["steps"].append("stopped paginating: deadline")
                break
            targets = [t for t in find_pagination_targets(html) if t[1] not in seen_pages]
            if not targets:
                break
            tgt, page = targets[0]
            seen_pages.add(page)
            form = extract_hidden_fields(html)
            form["__EVENTTARGET"] = tgt
            form["__EVENTARGUMENT"] = page
            r = sess.post(search_url, data=form, timeout=TIMEOUT)
            if r.status_code != 200:
                break
            html = r.text
            pr = parse_result_rows(html)
            if not pr:
                break
            rows.extend(pr)
            diag["pages"] += 1

        # map + normalize
        permits = []
        for rec in rows:
            m = map_row(rec)
            issued = _parse_aca_date(m.get("issued_date"))
            desc = (m.get("description") or "").strip()
            ptype = (m.get("type") or "").strip()
            permits.append({
                "permit_number": (m.get("permit_number") or "").strip() or None,
                "type": ptype or None,
                "status": (m.get("status") or "").strip() or None,
                "description": desc or None,
                "address": (m.get("address") or "").strip() or None,
                "issued_date": issued,
                "applied_date": None,
                "value": None,        # ACA search grid rarely exposes job value
                "contractor": None,
                "raw": rec,
            })
        diag["parsed"] = len(permits)
        if not permits and not diag.get("error"):
            diag["error"] = ("search returned no parseable rows — the date range may "
                             "exceed the portal's per-search limit, or the results grid "
                             "structure differs from expected")
        return permits, diag
    except requests.Timeout:
        diag["error"] = "timeout contacting Accela portal"
        return [], diag
    except Exception as e:
        diag["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        return [], diag

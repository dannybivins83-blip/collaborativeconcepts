"""
Click2Gov Building Permit (Click2GovBP / CentralSquare, *-egov.aspgov.com) adapter.

Some Florida cities — Boynton Beach among them — publish permits ONLY through
Click2Gov, which (unlike Tyler EnerGov Civic Access) has **no date-range or
permit-type search**. Its "Select Permit" screen only looks a permit up by
Application #, Address, or Parcel, behind a per-session OWASP CSRF token. So
Click2Gov can never be a bulk lead feed — it is a **per-address lookup** only,
used to answer "does THIS address have a permit on record?" (the address-matcher
use case).

Design, given the contract can't be pinned down offline:
  1. GET the search page to establish the session cookie + OWASP_CSRFTOKEN.
  2. Discover the search <form>'s action, method, and field names BY PARSING THE
     LIVE PAGE (not hardcoded control names) — Click2Gov field ids drift between
     deployments, and self-hosted variants use a per-city context path.
  3. Fill the address fields it actually found (house number + street name),
     carry the CSRF token + every hidden field, and POST.
  4. Parse the results table generically, mapping columns by header text (reuses
     the Accela GridView parser).

Like the Accela adapter this NEVER raises — it returns (rows, diagnostics) so the
caller can see exactly what happened. That diagnostics payload is deliberately
verbose (form action, discovered field names, status codes, table headers) so
the endpoint can be validated and corrected from a single live run on Vercel,
which this container's egress policy prevents doing here. Stdlib + requests only.
"""

import re
import time

import requests

try:  # reuse the Accela HTML helpers (same ASP.NET-style parsing problem)
    from accela import (parse_result_rows, map_row, extract_hidden_fields,
                        _ATTR_NAME_RX, _ATTR_ID_RX, _ATTR_VALUE_RX)
except ImportError:  # pragma: no cover - import path differs under Vercel
    from api.accela import (parse_result_rows, map_row, extract_hidden_fields,
                            _ATTR_NAME_RX, _ATTR_ID_RX, _ATTR_VALUE_RX)

UA = "CollaborativeConcepts-PermitLeads/1.0 (+https://collaborativeconceptsfl.com)"
TIMEOUT = 8
DEFAULT_DEADLINE = 18          # wall-clock cap for a whole batch (serverless-safe)
DEFAULT_PATH = "/Click2GovBP"  # Tyler-hosted default; self-hosted cities override
SEARCH_PAGE = "selectpermit.html"

_FORM_RX = re.compile(r"<form\b[^>]*>.*?</form>", re.I | re.S)
_FORM_ACTION_RX = re.compile(r'\baction=["\']([^"\']*)["\']', re.I)
_FORM_METHOD_RX = re.compile(r'\bmethod=["\']([^"\']*)["\']', re.I)
_FIELD_RX = re.compile(r"<(input|select|textarea)\b[^>]*>", re.I)
_TYPE_RX = re.compile(r'\btype=["\']([^"\']+)["\']', re.I)
_CSRF_NAME = "OWASP_CSRFTOKEN"


def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Accept": "text/html,application/xhtml+xml",
                      "Accept-Language": "en-US,en;q=0.9"})
    return s


def _field_hay(tag):
    """lower-cased name + id of a field tag, for keyword matching."""
    nm = _ATTR_NAME_RX.search(tag)
    idm = _ATTR_ID_RX.search(tag)
    return ((nm.group(1) if nm else "") + " " + (idm.group(1) if idm else "")).lower()


def parse_search_form(html):
    """Parse the search page into a form descriptor:
       {action, method, fields:{name:value}, names:[...], address_fields:{...}}.
    Discovers which field is the house number vs. the street name by keyword, so
    it survives per-deployment control renaming. Returns None if no form found."""
    forms = _FORM_RX.findall(html or "")
    if not forms:
        return None
    # pick the form that contains the most address-ish fields
    best, best_score = None, -1
    for f in forms:
        score = len(re.findall(r"street|address|parcel|permit|applic", f, re.I))
        if score > best_score:
            best, best_score = f, score
    form = best
    am = _FORM_ACTION_RX.search(form)
    action = am.group(1) if am else ""
    mm = _FORM_METHOD_RX.search(form)
    method = (mm.group(1) if mm else "post").lower()

    fields, names = {}, []
    num_field = street_field = dir_field = None
    for tag in re.findall(r"<(?:input|select|textarea)\b[^>]*>", form, re.I):
        nm = _ATTR_NAME_RX.search(tag)
        if not nm:
            continue
        name = nm.group(1)
        ftype = (_TYPE_RX.search(tag).group(1).lower() if _TYPE_RX.search(tag) else "text")
        if ftype in ("submit", "image", "button", "reset"):
            continue
        val = _ATTR_VALUE_RX.search(tag)
        fields[name] = val.group(1) if val else ""
        names.append(name)
        hay = _field_hay(tag)
        # classify the address inputs by keyword (first match wins). "number"
        # only counts WITH street/house/addr context — a bare "applicationNumber"
        # or "parcelNumber" must not be mistaken for the house number.
        if num_field is None and re.search(
                r"(st(reet)?.?(num|no|nbr)|house.?(num|no)|addr.?(num|no)|\bstnum\b|\bhousenum)", hay):
            num_field = name
        elif street_field is None and re.search(r"(st(reet)?.?name|streetname|\bstreet\b|\baddress\b|addr)", hay):
            street_field = name
        elif dir_field is None and re.search(r"(dir(ection)?|prefix|predir)", hay):
            dir_field = name
    return {
        "action": action, "method": method, "fields": fields, "names": names,
        "address_fields": {"num": num_field, "street": street_field, "dir": dir_field},
    }


def _find_csrf(html, session):
    """CSRF token from (a) a hidden OWASP_CSRFTOKEN field, (b) a query param in a
    link, or (c) a cookie of the same name."""
    m = re.search(r'name=["\']%s["\'][^>]*value=["\']([^"\']+)["\']' % _CSRF_NAME, html or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']%s["\']' % _CSRF_NAME, html or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r'%s=([A-Z0-9\-]{8,})' % _CSRF_NAME, html or "", re.I)
    if m:
        return m.group(1)
    for c in session.cookies:
        if c.name and _CSRF_NAME.lower() in c.name.lower():
            return c.value
    return None


def _abs_url(host, path, action):
    """Resolve a form action (absolute, root-relative, or relative) to a URL."""
    host = host.rstrip("/")
    if not action:
        return host + path.rstrip("/") + "/" + SEARCH_PAGE
    if action.startswith("http"):
        return action
    if action.startswith("/"):
        return host + action
    return host + path.rstrip("/") + "/" + action.lstrip("/")


def _split_street(street):
    """'810 N A ST' or 'N A ST' -> (num, rest). Number optional."""
    s = (street or "").strip()
    m = re.match(r"\s*(\d+)\s+(.*)", s)
    if m:
        return m.group(1), m.group(2).strip()
    return "", s


def lookup_address(host, num, street, path=DEFAULT_PATH, session=None,
                   form=None, deadline=None):
    """Look one address up in a Click2Gov BP portal.
    host: e.g. 'https://byb2-egov.aspgov.com'. num/street: house number + street.
    Returns (rows, diag). rows are raw {header:value} dicts + canonical fields."""
    started = time.time()
    diag = {"host": host, "path": path, "num": num, "street": street, "steps": []}
    s = session or _session()
    try:
        if form is None:
            page_url = host.rstrip("/") + path.rstrip("/") + "/" + SEARCH_PAGE
            r = s.get(page_url, timeout=TIMEOUT)
            diag["steps"].append({"get": page_url, "status": r.status_code})
            if r.status_code >= 400:
                diag["error"] = "search page HTTP %d" % r.status_code
                return [], diag
            html = r.text
            form = parse_search_form(html)
            diag["csrf_found"] = bool(_find_csrf(html, s))
            if not form:
                diag["error"] = "no search form on page"
                return [], diag
            form["_csrf"] = _find_csrf(html, s)
            diag["form_action"] = form["action"]
            diag["form_fields"] = form["names"]
            diag["address_fields"] = form["address_fields"]

        af = form["address_fields"]
        if not af.get("street"):
            diag["error"] = "could not locate a street field in the form"
            return [], diag

        payload = dict(form["fields"])   # keep hidden/default fields
        if form.get("_csrf"):
            payload[_CSRF_NAME] = form["_csrf"]
        payload[af["street"]] = street
        if af.get("num") and num:
            payload[af["num"]] = num
        post_url = _abs_url(host, path, form["action"])
        diag["steps"].append({"post": post_url, "street_field": af["street"],
                              "num_field": af.get("num")})
        if deadline and time.time() - started > deadline:
            diag["error"] = "deadline before post"
            return [], diag
        pr = s.post(post_url, data=payload, timeout=TIMEOUT,
                    headers={"Referer": host.rstrip("/") + path.rstrip("/") + "/" + SEARCH_PAGE})
        diag["steps"].append({"post_status": pr.status_code})
        if pr.status_code >= 400:
            diag["error"] = "search POST HTTP %d" % pr.status_code
            return [], diag
        rows = parse_result_rows(pr.text)
        diag["rows_parsed"] = len(rows)
        out = []
        for rec in rows:
            mapped = map_row(rec)
            if not any(mapped.values()):
                continue
            mapped["_raw"] = rec
            out.append(mapped)
        diag["mapped"] = len(out)
        return out, diag
    except requests.RequestException as e:
        diag["error"] = "request error: %s" % str(e)[:160]
        return [], diag
    except Exception as e:                       # never raise into the engine
        diag["error"] = "unexpected: %s" % str(e)[:160]
        return [], diag


def lookup_many(host, addresses, path=DEFAULT_PATH, deadline=DEFAULT_DEADLINE,
                max_lookups=60):
    """Look up a batch of addresses reusing one session (one CSRF/form fetch).
    addresses: list of dicts with 'num'+'street' or a combined 'address' string.
    Returns (results, diag). results: [{input, matched, permits, error?}].
    Bounded by BOTH max_lookups and the wall-clock deadline (serverless-safe)."""
    started = time.time()
    s = _session()
    diag = {"host": host, "path": path, "requested": len(addresses),
            "max_lookups": max_lookups, "deadline": deadline}
    # prime the session: fetch the form + CSRF once, reuse for every lookup
    form = None
    page_url = host.rstrip("/") + path.rstrip("/") + "/" + SEARCH_PAGE
    try:
        r = s.get(page_url, timeout=TIMEOUT)
        diag["prime_status"] = r.status_code
        if r.status_code < 400:
            form = parse_search_form(r.text)
            if form:
                form["_csrf"] = _find_csrf(r.text, s)
                diag["form_action"] = form["action"]
                diag["form_fields"] = form["names"]
                diag["address_fields"] = form["address_fields"]
                diag["csrf_found"] = bool(form.get("_csrf"))
    except Exception as e:
        diag["prime_error"] = str(e)[:160]

    results, done, hit_deadline = [], 0, False
    for item in addresses:
        if done >= max_lookups:
            diag["stopped"] = "max_lookups"
            break
        if time.time() - started > deadline:
            hit_deadline = True
            diag["stopped"] = "deadline"
            break
        if item.get("num") or item.get("street"):
            num, street = str(item.get("num", "")), item.get("street", "")
        else:
            num, street = _split_street(item.get("address", ""))
        rows, d = lookup_address(host, num, street, path=path, session=s,
                                 form=form, deadline=deadline - (time.time() - started))
        done += 1
        entry = {"input": item, "matched": bool(rows), "permits": rows}
        if d.get("error"):
            entry["error"] = d["error"]
        results.append(entry)
    diag["looked_up"] = done
    diag["hit_deadline"] = hit_deadline
    return results, diag

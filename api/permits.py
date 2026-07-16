"""
SoFlo Permit Leads — BatchData-style building-permit lead engine for
Martin, Palm Beach, Broward, and Miami-Dade counties.

Architecture (mirrors what BatchData sells, scoped to South Florida):
  1. INGEST   — per-county adapters pull recent permits from public GIS
                endpoints (ArcGIS FeatureServer/MapServer layers, resolved at
                runtime from ArcGIS Online item IDs or discovered from ArcGIS
                Hub DCAT catalogs).
  2. NORMALIZE— schemas differ per jurisdiction, so field names are
                auto-mapped against synonym tables using the layer's own
                metadata (no hardcoded schemas to go stale).
  3. TAG      — regex project-tagging engine (roofing, solar, HVAC, pool,
                seawall/dock, impact windows, generator, EV charger, ...).
  4. SERVE    — /api/permits/* JSON endpoints + CSV export consumed by the
                /permits dashboard. Owner lookup is linked out to each
                county's property appraiser (free), and the CSV is shaped so
                it can be uploaded straight to a skip-trace service.

Resilience: every source can fail independently; results report per-source
status. If ALL live sources fail (or ?demo=1), a clearly-flagged bundled
sample dataset is served so the dashboard always renders.

Config override without a deploy:
  PERMITS_EXTRA_SOURCES  JSON list of source dicts, merged over defaults
                         (match by "id" to replace; new ids are appended).

No new dependencies: flask + requests only.
"""

import csv
import io
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone

import requests

UA = "CollaborativeConcepts-PermitLeads/1.0 (+https://collaborativeconceptsfl.com)"
HTTP_TIMEOUT = 8           # per outbound request, seconds
SOURCE_BUDGET = 12         # per-source total budget, seconds
REQUEST_BUDGET = 45        # whole fan-out budget (must stay under vercel maxDuration=60)
CACHE_TTL_RESULTS = 600    # search results, seconds
CACHE_TTL_META = 12 * 3600 # layer metadata / item resolution / discovery

COUNTIES = ["Martin", "Palm Beach", "Broward", "Miami-Dade"]

# --------------------------------------------------------------------------
# Source registry
# --------------------------------------------------------------------------
# kind:
#   arcgis_item     resolve ArcGIS Online item id -> feature service URL
#   arcgis_layer    direct FeatureServer/MapServer layer URL
#   hub_discover    scan ArcGIS Hub DCAT catalog(s) for a permits layer
DEFAULT_SOURCES = [
    {
        "id": "mdc",
        "county": "Miami-Dade",
        "label": "Miami-Dade County — Building Permits (countywide, 2yr+)",
        "kind": "arcgis_layer",
        # FIXED 2026-07-15 — this source was silently returning ZERO rows.
        # Root cause (verified live): the old open-data item ids
        # (f2181fb7e4ae46adbc633e478a607226 / 31cd319f45544648b59f0418aea60091)
        # are DEAD — Hub v3 -> 404 "Resource Not Found"; the ArcGIS sharing API
        # -> "Item does not exist or is inaccessible" / "no permissions". The
        # gis-mdc DCAT catalog now returns 0 datasets. Miami-Dade's live permit
        # feed is the MDPublisher service below (~140k permits, 2 prior yrs).
        #
        # The explicit field_map is REQUIRED, not cosmetic: MDC's schema uses
        # non-standard names, and the roof signal lives in
        # ApplicationTypeDescription ("RE-ROOF/REPAIR", 16.8k rows) +
        # DetailDescriptionComments. The name-based auto-mapper misses both, and
        # because tag_permit() runs over description+type, the "reroof" tag would
        # never fire -> no anchor-recert leads. Live-verified 2026-07-15.
        "layer_urls": [
            "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0",
        ],
        "field_map": {
            "permit_number": "PermitNumber",
            "issue_date": "PermitIssuedDate",
            "type": "ApplicationTypeDescription",   # carries "RE-ROOF/REPAIR" -> drives the reroof tag
            "description": "DetailDescriptionComments",
            "address": "PropertyAddress",
            "owner": "OwnerName",
            "contractor": "ContractorName",
            "value": "EstimatedValue",
        },
        "portal": "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0",
        "note": ("Live MDC permit feed (owner: MDPublisher). ResidentialCommercial='C' "
                 "isolates commercial/condo roofs — the anchor-recert buyers (~3.5k "
                 "commercial re-roofs in the last 18 months vs ~115 in Broward)."),
    },
    {
        # Miami-Dade RER EnerGov "Code Violations" (layer 86, 181,835 rows).
        # A DISTINCT lead category (open code cases / unsafe structures / liens),
        # NOT building permits. Filtered server-side to OPEN cases only. Endpoint
        # + schema + status codes live-verified 2026-07-15.
        "id": "mdc_violations",
        "county": "Miami-Dade",
        "category": "violation",
        "label": "Miami-Dade County — Code Violations (open cases, EnerGov)",
        "kind": "arcgis_layer",
        "layer_urls": [
            "https://gisweb.miamidade.gov/arcgis/rest/services/EnerGov/MD_LandMgtViewer/MapServer/86",
        ],
        # open cases = everything except 2 (Closed). 1=Open, 4=Lien, 6=Civil,
        # 8=Referred to Internal Compliance, 9=Active LP.
        "where_clause": "CASE_STATUS IN ('1','4','6','8','9')",
        "field_map": {
            "permit_number": "CASE_NUM",
            "issue_date": "CASE_DATE",     # epoch ms
            "status": "STAT_DESC",
            "description": "PROBLEM_DESC",
            "address": "ADDRESS",
            "owner": "FOLIO",              # parcel id — links to appraiser lookup
        },
        "portal": "https://gisweb.miamidade.gov/arcgis/rest/services/EnerGov/MD_LandMgtViewer/MapServer/86",
        "note": ("Open code-violation cases (unsafe structure, liens, unpermitted work). "
                 "Strong distressed-property / structural-repair leads. Filtered to open "
                 "cases; '1' Open + '4' Lien are the highest-intent set."),
    },
    {
        "id": "ftl",
        "county": "Broward",
        "label": "Broward — Fort Lauderdale Building Permit Tracker",
        "kind": "arcgis_layer",
        "layer_urls": [
            "https://gis.fortlauderdale.gov/arcgis/rest/services/BuildingPermitTracker/BuildingPermitTracker/MapServer/0",
        ],
        "portal": "https://gis.fortlauderdale.gov/arcgis/rest/services/BuildingPermitTracker/BuildingPermitTracker/MapServer/0",
        "note": "Broward issues permits per-municipality. Fort Lauderdale + unincorporated county are wired in; add more cities via PERMITS_EXTRA_SOURCES.",
    },
    {
        "id": "broward_uninc",
        "county": "Broward",
        "label": "Broward County — Building Permits (unincorporated + contract cities)",
        "kind": "arcgis_item",
        "item_ids": ["401f56339f9e49e6ac11efb91f191b4b"],
        "hub_sites": ["https://geohub-bcgis.opendata.arcgis.com"],
        "portal": "https://geohub-bcgis.opendata.arcgis.com/",
        "note": "Broward County Building Code Division (unincorporated areas + cities the county permits for).",
    },
    {
        "id": "pbc",
        "county": "Palm Beach",
        "label": "Palm Beach — open-data discovery (no public permit feed)",
        "kind": "hub_discover",
        "hub_sites": [
            "https://opendata2-pbcgov.opendata.arcgis.com",
            "https://gisportal-wpbgis.opendata.arcgis.com",
        ],
        "portal": "https://discover.pbc.gov/epzb.admin.webspa/",
        "note": ("Palm Beach County and its cities run permits through Accela/ePZB, "
                 "Click2Gov and similar portals — none publish issued permits as a "
                 "queryable GIS/API layer. Catalogs are scanned each run and will "
                 "auto-activate if one is ever published."),
    },
    {
        "id": "martin",
        "county": "Martin",
        "label": "Martin County — Building Permits (Accela portal)",
        "kind": "accela_aca",
        "agency": "MARTINCO",
        "module": "Building",
        "portal": "https://aca-prod.accela.com/MARTINCO/Cap/CapHome.aspx?module=Building&TabName=Building",
        "note": ("Scrapes Martin County's Accela Citizen Access portal (the county's "
                 "system of record) for issued building permits by date range. "
                 "Best-effort — portal HTML can change."),
    },
    {
        "id": "martin_dev",
        "county": "Martin",
        "label": "Martin County — Countywide Development Projects (Accela permits not public)",
        "kind": "arcgis_layer",
        # Martin building permits are Accela-only. Their open-data DOES publish
        # countywide development-review projects — real active construction
        # leads (has PERMIT_NUMBER + PROJECT_NAME + status), just not the full
        # issued-permit stream. Labeled honestly.
        "layer_urls": [
            "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/Proposed_Developments/MapServer/0",
        ],
        "hub_dataset_ids": ["154ce08f06cf4048936536ba490e5c90_0"],
        "hub_sites": ["https://data-mcgov.opendata.arcgis.com"],
        "portal": "https://data-mcgov.opendata.arcgis.com/datasets/mcgov::countywide-development-projects",
        "note": ("Martin County issued building permits live in Accela (aca-prod.accela.com/"
                 "MARTINCO) with no public GIS/API export. This layer is the county's "
                 "development-review projects — real construction activity, but not the "
                 "full permit stream."),
    },
]

# County property-appraiser search pages (free owner lookup — "layer 2").
APPRAISER_SEARCH = {
    "Miami-Dade": "https://www.miamidade.gov/Apps/PA/propertysearch/",
    "Broward": "https://web.bcpa.net/BcpaClient/",
    "Palm Beach": "https://pbcpao.gov/Property/Search",
    "Martin": "https://www.pa.martin.fl.us/tools/property-search",
}

# --------------------------------------------------------------------------
# Project tagging engine (regexes run over description + type text)
# --------------------------------------------------------------------------
TAG_RULES = [
    ("roofing",        "Roofing",            r"\bre-?roof|\broof(ing|\b)|shingle|roof\s*repl|tpo\b|torch\s*down|flat\s*roof|tile\s*roof|metal\s*roof"),
    # reroof = FULL roof replacement (tear-off/recover/new) — the work that
    # DISTURBS rooftop fall-protection anchors and voids their OSHA cert. Kept
    # separate from "roofing" (which also matches minor repairs) so it drives the
    # post-re-roof anchor-recertification lead list. See /api/permits/reroof.
    ("reroof",         "Re-Roof (full)",     r"\bre-?\s?roof|roof\s*(replac|re-?cover|recover|over\b)|replac\w*\s+(the\s+)?(existing\s+)?roof|tear[\s-]?off|\bnew\s+roof|roof\s+install"),
    ("solar",          "Solar",              r"solar|photovoltaic|\bpv\b"),
    ("hvac",           "HVAC / AC",          r"\bhvac\b|\ba/?c\b(?!\w)|air\s*cond|mini[-\s]?split|change\s*out|changeout|condenser|air\s*handler|duct"),
    ("pool_spa",       "Pool / Spa",         r"\bpool\b|\bspa\b|hot\s*tub|pool\s*heater|marcite|resurfac.*pool|pool.*resurfac"),
    ("electrical",     "Electrical",         r"electric|panel\s*(upgrade|change)|\bamp\s*service|rewire|meter\s*can|service\s*change"),
    ("plumbing",       "Plumbing",           r"plumb|re-?pipe|sewer|drain\s*line|backflow|water\s*line|water\s*main"),
    ("water_heater",   "Water Heater",       r"water\s*heater|tankless"),
    ("generator",      "Generator",          r"generator|standby\s*power|transfer\s*switch"),
    ("ev_charger",     "EV Charger",         r"\bev\b.*charg|electric\s*vehicle|car\s*charger|tesla\s*charger"),
    ("windows_doors",  "Windows / Doors",    r"window|door(?!\s*hanger)|slider|french\s*door|garage\s*door"),
    ("impact_shutters","Impact / Shutters",  r"impact|hurricane|shutter|storm\s*panel"),
    ("kitchen_bath",   "Kitchen / Bath",     r"kitchen|bath(room)?\s*(remodel|reno)|cabinet|counter\s*top"),
    ("remodel",        "Remodel / Interior", r"remodel|renovat|interior\s*alter|build[-\s]?out|buildout|tenant\s*improvement"),
    ("addition",       "Addition",           r"addition|\badd\b.*(room|bedroom|bath)|extend|enclos(e|ure)"),
    ("new_construction","New Construction",  r"new\s*(single|sfr|home|house|residence|construction|building|duplex|townhome)|\bnsfr\b"),
    ("demolition",     "Demolition",         r"\bdemo\b|demolition|tear\s*down"),
    ("fence",          "Fence",              r"\bfence|\bgate\b"),
    ("driveway_paving","Driveway / Paving",  r"driveway|paver|asphalt|concrete\s*(slab|drive|walk)|sidewalk"),
    ("dock_seawall",   "Dock / Seawall",     r"\bdock\b|seawall|sea\s*wall|boat\s*lift|davit|piling|bulkhead"),
    ("shed_garage",    "Shed / Garage",      r"\bshed\b|garage(?!\s*door)|carport|gazebo|pergola"),
    ("fire",           "Fire Systems",       r"fire\s*(alarm|sprinkler|suppression)"),
    ("sign",           "Signage",            r"\bsign\b|signage"),
    ("mechanical",     "Mechanical",         r"mechanical|exhaust\s*hood|ventilation"),
    ("landscape",      "Landscape / Tree",   r"landscap|irrigation|\btree\b"),
    ("commercial",     "Commercial",         r"commercial|office|retail|restaurant|warehouse"),
    # code-violation-oriented tags (high value for structural/WWS lead-gen)
    ("unsafe_structure","Unsafe Structure",  r"unsafe\s*(structure|building|condition)|structurally\s*(unsound|deficient|compromised)|\bunsound\b|collaps|dilapidat|derelict|condemn"),
    ("no_permit",      "Work w/o Permit",    r"without\s*(a\s*)?permit|\bunpermitted\b|expired\s*permit|no\s*permit\b|illegal\s*(construction|work|structure)"),
    ("property_maint", "Property Maintenance",r"maintenance|overgrow|debris|trash|junk|derelict|abandon|nuisance"),
]
_COMPILED_TAGS = [(key, label, re.compile(rx, re.I)) for key, label, rx in TAG_RULES]

# Field synonym tables for schema auto-mapping (normalized: uppercase, alnum only)
FIELD_SYNONYMS = {
    "permit_number": ["PERMITNUMBER", "PERMITNO", "PERMITNUM", "PERMIT", "PROCESSNUMBER",
                      "PROCNUM", "RECORDID", "CASENUMBER", "PERMITID", "FOLIONUMPERMIT",
                      "BLDGPERMITNO", "PERMITTRACKINGNUMBER"],
    "description":   ["DESCRIPTION", "WORKDESC", "WORKDESCRIPTION", "DESCR", "SCOPEOFWORK",
                      "SCOPE", "JOBDESC", "JOBDESCRIPTION", "PERMITDESC", "PROJDESC",
                      "PROJECTDESCRIPTION", "PROPOSEDUSE", "COMMENTS", "DETAIL", "PROJECTNAME"],
    "address":       ["ADDRESS", "SITEADDR", "SITEADDRESS", "FULLADDR", "FULLADDRESS",
                      "LOCATION", "STREETADDRESS", "PROPADDR", "PROPERTYADDRESS",
                      "JOBADDRESS", "ADDR", "SITEADDRESS1", "LOCATIONADDRESS", "STADDRESS"],
    "issue_date":    ["ISSUEDDATE", "ISSUEDATE", "DATEISSUED", "ISSUED", "PERMITISSUEDATE",
                      "ISSUEDDT", "ISSUEDT", "PERMITISSUEDDATE"],
    "applied_date":  ["APPLIEDDATE", "APPLICATIONDATE", "APPLYDATE", "DATEAPPLIED",
                      "SUBMITTED", "SUBMITTALDATE", "APPDATE", "CREATEDDATE", "FILEDDATE"],
    "status":        ["STATUS", "PERMITSTATUS", "STATUSDESC", "RECORDSTATUS", "STATUSDESCRIPTION",
                      "CURRENTSTATUS", "STATUSCURRENT"],
    "type":          ["PERMITTYPE", "TYPE", "WORKTYPE", "SUBTYPE", "CLASS", "PERMITCLASS",
                      "PERMITCATEGORY", "CATEGORY", "TYPEDESC", "PERMITTYPEDESC", "USECODE",
                      "APPLICATIONTYPE", "RECORDTYPE"],
    "contractor":    ["CONTRACTOR", "CONTRACTORNAME", "CONTNAME", "COMPANY", "COMPANYNAME",
                      "BUSINESSNAME", "GC", "GENERALCONTRACTOR", "CONTRACTORCOMPANY"],
    "value":         ["ESTIMATEDVALUE", "JOBVALUE", "VALUATION", "ESTVALUE", "VALUE",
                      "CONSTCOST", "JOBCOST", "CONSTRUCTIONCOST", "ESTIMATEDCOST",
                      "TOTALSQFTCOST", "DECLAREDVALUE", "PERMITVALUE", "TOTALJOBVALUE"],
    "owner":         ["OWNER", "OWNERNAME", "PROPOWNER", "PROPERTYOWNER", "OWNERSNAME"],
    "city":          ["CITY", "SITECITY", "MUNICIPALITY", "JURISDICTION", "TOWN"],
    "zip":           ["ZIP", "ZIPCODE", "SITEZIP", "POSTALCODE", "ZIP5"],
}
_DATEISH = re.compile(r"DATE|ISSUED|APPLIED|SUBMIT|FILED|FINAL|EXPIR", re.I)
_PERMIT_DATASET_RX = re.compile(r"permit", re.I)
_PERMIT_DATASET_NEG_RX = re.compile(
    r"well|environmental|derm|septic|tree\s|right[-\s]?of[-\s]?way|special\s*event|burn\b|alarm\s*permit", re.I)


def _norm_field(name):
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


# --------------------------------------------------------------------------
# Tiny TTL cache (persists across requests on a warm serverless instance)
# --------------------------------------------------------------------------
_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    return None


def _cache_put(key, value, ttl):
    with _cache_lock:
        _cache[key] = (time.time() + ttl, value)


def _session():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def _get_json(url, params=None, timeout=HTTP_TIMEOUT):
    r = _session().get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------
# Source config (defaults + env overrides)
# --------------------------------------------------------------------------
def load_sources():
    sources = [dict(s) for s in DEFAULT_SOURCES]
    raw = (os.environ.get("PERMITS_EXTRA_SOURCES") or "").strip()
    if raw:
        try:
            extra = json.loads(raw)
            if isinstance(extra, list):
                by_id = {s["id"]: s for s in sources}
                for item in extra:
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    if item["id"] in by_id:
                        by_id[item["id"]].update(item)
                    else:
                        sources.append(item)
        except Exception:
            pass  # bad env JSON must never take the API down
    return sources


# --------------------------------------------------------------------------
# ArcGIS adapters
# --------------------------------------------------------------------------
def resolve_item_to_layer(item_id):
    """ArcGIS Online item id -> first queryable layer URL."""
    ck = f"item:{item_id}"
    hit = _cache_get(ck)
    if hit:
        return hit
    meta = _get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}",
                     params={"f": "json"})
    if meta.get("error"):
        raise RuntimeError(f"arcgis item {item_id}: {meta['error'].get('message', 'error')}")
    url = (meta.get("url") or "").rstrip("/")
    if not url:
        raise RuntimeError(f"arcgis item {item_id} has no service url")
    if not re.search(r"/\d+$", url):  # service root -> pick first layer
        svc = _get_json(url, params={"f": "json"})
        layers = svc.get("layers") or svc.get("tables") or []
        if not layers:
            raise RuntimeError(f"service has no layers: {url}")
        url = f"{url}/{layers[0].get('id', 0)}"
    _cache_put(ck, url, CACHE_TTL_META)
    return url


def layer_metadata(layer_url):
    ck = f"meta:{layer_url}"
    hit = _cache_get(ck)
    if hit:
        return hit
    meta = _get_json(layer_url, params={"f": "json"})
    if meta.get("error"):
        raise RuntimeError(f"layer metadata error: {meta['error'].get('message', 'error')}")
    _cache_put(ck, meta, CACHE_TTL_META)
    return meta


def map_fields(fields):
    """Auto-map a layer's fields to our canonical schema via synonym tables."""
    by_norm, date_fields = {}, []
    for f in fields or []:
        name = f.get("name") or ""
        by_norm.setdefault(_norm_field(name), name)
        if f.get("type") == "esriFieldTypeDate":
            date_fields.append(name)

    mapping = {}
    for canon, synonyms in FIELD_SYNONYMS.items():
        for syn in synonyms:
            if syn in by_norm:
                mapping[canon] = by_norm[syn]
                break
        if canon not in mapping:  # substring fallback
            for norm, actual in by_norm.items():
                if any(syn in norm or norm in syn for syn in synonyms if len(syn) > 3):
                    mapping[canon] = actual
                    break

    # Dates must be real date fields when the layer has them typed.
    for canon, pref_rx in (("issue_date", r"ISSU"),
                           ("applied_date", r"APPL|SUBMIT|CREATE|FILE")):
        got = mapping.get(canon)
        if date_fields and (not got or got not in date_fields):
            pref = [n for n in date_fields if re.search(pref_rx, n, re.I)]
            if canon == "issue_date" and not pref:
                # any date field that isn't an applied/expiry-style date
                pref = [n for n in date_fields
                        if not re.search(r"APPL|SUBMIT|CREATE|FILE|EXPIR|FINAL", n, re.I)]
                pref = pref or date_fields
            if pref:
                mapping[canon] = pref[0]
    if mapping.get("applied_date") and mapping.get("applied_date") == mapping.get("issue_date"):
        mapping.pop("applied_date")
    return mapping


# --------------------------------------------------------------------------
# Content-based field inference — recovers fields when a layer's column NAMES
# don't match our synonyms (e.g. Miami-Dade), by reading the actual VALUES in
# a sample of records. This is what makes the mapper robust across the wildly
# different schemas each jurisdiction uses.
# --------------------------------------------------------------------------
_ADDR_RX = re.compile(r"^\s*\d{1,6}\s+[0-9A-Za-z].*"
                      r"(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|ln|lane|ct|court|"
                      r"way|pl|place|ter|terrace|cir|circle|hwy|highway|pkwy|trail|trl|"
                      r"\bnw\b|\bne\b|\bsw\b|\bse\b)\.?\s*", re.I)
_MONEY_NAME_RX = re.compile(r"cost|value|valuation|amount|estimate|job.?val|const|fee", re.I)
_ID_NAME_RX = re.compile(r"objectid|globalid|fid|folio|parcel|\bx\b|\by\b|lat|lon|"
                         r"longitude|latitude|zip|year|shape", re.I)
_TEXTY_STOP = re.compile(r"objectid|globalid|url|link|http", re.I)


def _field_type_map(fields):
    out = {}
    for f in fields or []:
        out[f.get("name")] = (f.get("type") or "").replace("esriFieldType", "")
    return out


def refine_mapping_with_samples(mapping, fields, features, sample=60):
    """Fill in canonical fields the name-based mapper missed, and replace an
    implausible 'value' mapping, using the distribution of real values in a
    sample of features. Only fills MISSING slots (never overrides a good
    name-based match) except for a demonstrably-bad value column."""
    mapping = dict(mapping)
    ftype = _field_type_map(fields)
    rows = []
    for feat in (features or [])[:sample]:
        a = feat.get("attributes") or feat.get("properties") or {}
        if a:
            rows.append(a)
    if not rows:
        return mapping

    used = set(v for v in mapping.values() if v)
    names = [f.get("name") for f in (fields or []) if f.get("name")]

    def col_vals(name):
        return [r.get(name) for r in rows if r.get(name) not in (None, "")]

    # ---- string-field stats ----
    str_stats = {}
    for name in names:
        t = ftype.get(name, "")
        if t and t != "String":
            continue
        vals = [str(v) for v in col_vals(name)]
        if not vals:
            continue
        avg_len = sum(len(v) for v in vals) / len(vals)
        addr_frac = sum(1 for v in vals if _ADDR_RX.match(v)) / len(vals)
        uniq_frac = len(set(vals)) / len(vals)
        str_stats[name] = {"avg_len": avg_len, "addr_frac": addr_frac,
                           "uniq_frac": uniq_frac, "n": len(vals)}

    # address: the string column whose values most look like street addresses
    if not mapping.get("address"):
        cand = [(s["addr_frac"], n) for n, s in str_stats.items()
                if n not in used and s["addr_frac"] >= 0.4 and not _TEXTY_STOP.search(n)]
        if cand:
            best = max(cand)[1]
            mapping["address"] = best
            used.add(best)

    # description: the longest free-text column that isn't the address/id
    if not mapping.get("description"):
        cand = [(s["avg_len"], n) for n, s in str_stats.items()
                if n not in used and s["avg_len"] >= 12 and s["addr_frac"] < 0.4
                and not _TEXTY_STOP.search(n)]
        if cand:
            best = max(cand)[1]
            mapping["description"] = best
            used.add(best)

    # ---- numeric value column: plausible dollar range, prefer money-ish names ----
    def numeric_median(name):
        nums = []
        for v in col_vals(name):
            try:
                nums.append(float(v))
            except Exception:
                pass
        if not nums:
            return None
        nums.sort()
        return nums[len(nums) // 2]

    def plausible_value_col(name):
        t = ftype.get(name, "")
        if t not in ("Double", "Single", "Integer", "SmallInteger", "BigInteger", ""):
            return False
        if _ID_NAME_RX.search(name):
            return False
        med = numeric_median(name)
        if med is None:
            return False
        # residential/commercial permit values: ~$100 to ~$50M; reject folio/coord/epoch
        return 100 <= med <= 50_000_000

    current_val = mapping.get("value")
    val_ok = current_val and plausible_value_col(current_val) and _MONEY_NAME_RX.search(current_val)
    if not val_ok:
        named = [n for n in names if n not in used and _MONEY_NAME_RX.search(n)
                 and plausible_value_col(n)]
        if named:
            mapping["value"] = named[0]
        elif not (current_val and plausible_value_col(current_val)):
            # current mapping is absurd (e.g. folio → $205M). Prefer a plausible
            # numeric col; if none, drop value rather than show garbage.
            anyplaus = [n for n in names if n not in used and plausible_value_col(n)]
            mapping["value"] = anyplaus[0] if anyplaus else None

    return mapping


def _ms_to_timestamp(ms):
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _build_date_where(date_field, start_ms, end_ms, style):
    """Build a WHERE clause for a date range in one of several SQL dialects
    ArcGIS servers accept (they disagree on date literals)."""
    parts = []
    if style == "ts":       # standardized queries (most hosted FeatureServers)
        if start_ms is not None:
            parts.append(f"{date_field} >= TIMESTAMP '{_ms_to_timestamp(start_ms)}'")
        if end_ms is not None:
            parts.append(f"{date_field} <= TIMESTAMP '{_ms_to_timestamp(end_ms)}'")
    elif style == "date":   # older ArcGIS Server MapServers
        if start_ms is not None:
            parts.append(f"{date_field} >= DATE '{_ms_to_timestamp(start_ms)[:10]}'")
        if end_ms is not None:
            parts.append(f"{date_field} <= DATE '{_ms_to_timestamp(end_ms)[:10]}'")
    elif style == "epoch":  # some services accept raw epoch millis
        if start_ms is not None:
            parts.append(f"{date_field} >= {int(start_ms)}")
        if end_ms is not None:
            parts.append(f"{date_field} <= {int(end_ms)}")
    return " AND ".join(parts) if parts else "1=1"


def _and_where(a, b):
    a = (a or "").strip() or "1=1"
    b = (b or "").strip() or "1=1"
    if a == "1=1":
        return b
    if b == "1=1":
        return a
    return f"({a}) AND ({b})"


def query_layer(layer_url, order_field=None, date_field=None, start_ms=None,
                end_ms=None, record_count=2000, max_records=2000, base_where=None):
    """Pull records, preferring a SERVER-SIDE date filter (so historical windows
    return the right rows, not just the newest N) but degrading safely.

    Robustness is the priority: date SQL dialects vary and a wrong one can
    silently match ZERO rows rather than error. So we try date-WHERE variants,
    and — critically — if a filtered query returns 0 rows we fall through to an
    UNFILTERED newest-first pull and let the caller's client-side window filter
    do the work. That guarantees a layer with data never reports empty just
    because its date column didn't accept our literal."""
    qurl = f"{layer_url}/query"
    page = min(record_count, 2000)

    def fetch_page(where, offset, use_order):
        params = {
            "where": where, "outFields": "*", "f": "json",
            "resultRecordCount": page, "resultOffset": offset,
            "returnGeometry": "true", "outSR": 4326,
        }
        if use_order and order_field:
            params["orderByFields"] = f"{order_field} DESC"
        return _get_json(qurl, params=params, timeout=HTTP_TIMEOUT + 8)

    # Candidate WHERE clauses in priority order; the source's base filter (e.g.
    # open-case CASE_STATUS IN (...)) is ANDed onto every variant, and the base
    # filter alone is always the final fallback so a live layer never returns
    # empty on a date-dialect miss while still honoring the base filter.
    base = (base_where or "1=1").strip() or "1=1"
    where_options = []
    if date_field and (start_ms is not None or end_ms is not None):
        for style in ("ts", "epoch", "date"):  # cover all ArcGIS date dialects
            where_options.append(_and_where(base, _build_date_where(date_field, start_ms, end_ms, style)))
    where_options.append(base)

    chosen_where, use_order, first = None, bool(order_field), None
    last_err = None
    for i, where in enumerate(where_options):
        is_last = (i == len(where_options) - 1)
        uo = bool(order_field)
        data = fetch_page(where, 0, uo)
        if data.get("error") and uo:            # retry once without ORDER BY
            uo = False
            data = fetch_page(where, 0, uo)
        if data.get("error"):
            last_err = data["error"].get("message", "error")
            continue
        feats = data.get("features") or []
        # accept this WHERE if it yielded rows, or it's the final fallback (the
        # base filter alone) — so a genuinely-empty result is still honored.
        if feats or is_last:
            chosen_where, use_order, first = where, uo, data
            break
    if first is None:
        raise RuntimeError(f"query error: {last_err or 'no working query variant'}")

    features = list(first.get("features") or [])
    data, offset = first, page
    while len(features) < max_records and data.get("exceededTransferLimit"):
        data = fetch_page(chosen_where, offset, use_order)
        if data.get("error"):
            break
        feats = data.get("features") or []
        if not feats:
            break
        features.extend(feats)
        offset += page
    return features[:max_records]


# Tokens that must appear in a discovered dataset's metadata for it to count
# as belonging to a given county (guards against pulling another state's
# "Building Permits" from the global Hub search).
COUNTY_TOKENS = {
    "Miami-Dade": ["miami-dade", "miami dade", "mdc", "miami"],
    "Broward": ["broward", "fort lauderdale", "ftl", "hollywood", "pompano", "coral springs"],
    "Palm Beach": ["palm beach", "pbc", "west palm", "boca raton", "delray"],
    "Martin": ["martin county", "martin ", "stuart", "hobe sound", "palm city"],
}


def _layer_url_from_service(svc, layer_id):
    svc = (svc or "").rstrip("/")
    if not svc:
        return None
    if re.search(r"/(Feature|Map)Server/\d+$", svc):
        return svc
    if re.search(r"/(Feature|Map)Server$", svc):
        return f"{svc}/{layer_id if layer_id is not None else 0}"
    return None


# Known-wrong ArcGIS orgs/hosts that name-collide with our counties in search
# results (Esri sample data, Palm BAY, Seattle, Tempe, Baltimore County,
# Fort Worth, and various Canadian districts). A candidate layer matching any
# of these is never used, even if discovery or an env override surfaces it.
_BLOCKED_LAYER_RX = re.compile(
    r"ONZht79c8QWuX759"          # Esri sample "Building_Permits" (a.k.a. Canadian)
    r"|palmbayflorida"           # Palm BAY (Brevard), not Palm Beach
    r"|ZOyb2t4B0UYuYNYH"         # Seattle
    r"|lQySeXwbBg53XWDi"         # Tempe, AZ
    r"|data-csrd"                # Columbia Shuswap, BC
    r"|bcstat|www-bcstat"        # Baltimore County, MD ("bc-gis")
    r"|CFW_Open_Data|3ddLCBXe1bRt7mzj",  # Fort Worth, TX
    re.I)


def _is_blocked(layer_url):
    return bool(layer_url and _BLOCKED_LAYER_RX.search(layer_url))


def resolve_hub_dataset_id(dataset_id):
    """Resolve an ArcGIS Hub dataset id (e.g. '<itemid>_0') to a queryable
    layer URL via the Hub v3 dataset API. This returns clean JSON and works
    for county Hub datasets whose items reject the ArcGIS sharing API with a
    permissions error (the exact Miami-Dade failure)."""
    ck = f"hubds:{dataset_id}"
    hit = _cache_get(ck)
    if hit is not None:
        return hit
    data = _get_json(f"https://hub.arcgis.com/api/v3/datasets/{dataset_id}",
                     params={"fields[datasets]": "url,layer,name,recordCount"},
                     timeout=HTTP_TIMEOUT + 8)
    d = data.get("data") or {}
    a = d.get("attributes") or {}
    layer_id = None
    lay = a.get("layer")
    if isinstance(lay, dict) and lay.get("id") is not None:
        layer_id = lay.get("id")
    if layer_id is None:
        m = re.search(r"_(\d+)$", dataset_id)
        layer_id = m.group(1) if m else 0
    url = _layer_url_from_service(a.get("url") or a.get("serviceUrl"), layer_id)
    if url:
        _cache_put(ck, url, CACHE_TTL_META)
    return url


# --------------------------------------------------------------------------
# ArcGIS Hub discovery
# --------------------------------------------------------------------------
def discover_via_hub_search(query, county_tokens, limit=30):
    """Discover permit layers via the ArcGIS Hub v3 datasets API, which returns
    well-formed JSON:API (unlike the DCAT feed, which some counties — e.g.
    Miami-Dade — emit as malformed JSON). Returns [{title, layer_url, landing}]
    best-first, county-gated. Raises only if the API itself is unreachable."""
    ck = f"hubv3:{query}:{county_tokens}"
    hit = _cache_get(ck)
    if hit is not None:
        return hit
    # Hub v3 is JSON:API — pagination is page[size], not the invalid `num`
    # (which returned HTTP 400 and killed discovery for PBC + Broward-uninc).
    data = _get_json("https://hub.arcgis.com/api/v3/datasets",
                     params={"q": query, "page[size]": limit},
                     timeout=HTTP_TIMEOUT + 8)
    out = []
    for d in data.get("data", []) or []:
        a = d.get("attributes", {}) or {}
        name = a.get("name") or a.get("title") or ""
        if not _PERMIT_DATASET_RX.search(name) or _PERMIT_DATASET_NEG_RX.search(name):
            continue
        hay = " ".join(str(a.get(k) or "") for k in
                       ("name", "source", "orgName", "owner", "region",
                        "snippet", "description")).lower()
        if county_tokens and not any(tok in hay for tok in county_tokens):
            continue
        layer_id = None
        lay = a.get("layer")
        if isinstance(lay, dict) and lay.get("id") is not None:
            layer_id = lay.get("id")
        if layer_id is None:
            m = re.search(r"_(\d+)$", d.get("id") or "")
            layer_id = m.group(1) if m else 0
        layer_url = _layer_url_from_service(a.get("url") or a.get("serviceUrl"), layer_id)
        if not layer_url:
            continue
        score = 0 if re.search(r"building\s*permit", name, re.I) else 1
        out.append((score, {"title": name, "layer_url": layer_url,
                            "landing": a.get("url") or ""}))
    result = [c for _, c in sorted(out, key=lambda x: x[0])]
    _cache_put(ck, result, CACHE_TTL_META)
    return result


# --------------------------------------------------------------------------
# ArcGIS Hub discovery (DCAT catalogs) — for counties w/o a known layer
# --------------------------------------------------------------------------
def discover_hub_permit_layers(hub_site):
    """Scan a Hub site's DCAT feed for permit-ish datasets with a GeoService
    distribution. Returns [{title, layer_url, landing}] best-first.
    Raises if the site's catalog cannot be fetched at all (so callers can
    distinguish 'unreachable' from 'reachable but nothing published')."""
    ck = f"dcat:{hub_site}"
    hit = _cache_get(ck)
    if hit is not None:
        return hit
    candidates = []
    feed, last_err = None, None
    for path in ("/api/feed/dcat-us/1.1.json", "/data.json"):
        try:
            feed = _get_json(hub_site.rstrip("/") + path, timeout=HTTP_TIMEOUT + 8)
            break
        except Exception as e:
            last_err = e
            continue
    if feed is None:
        raise RuntimeError(f"catalog unreachable: {last_err}")
    for ds in (feed or {}).get("dataset", []):
        title = ds.get("title") or ""
        # match on the title only — descriptions mention "permits" on plenty
        # of unrelated datasets (parks, zoning, ...)
        if not _PERMIT_DATASET_RX.search(title):
            continue
        if _PERMIT_DATASET_NEG_RX.search(title):
            continue
        layer_url = None
        for dist in ds.get("distribution", []):
            u = dist.get("accessURL") or dist.get("downloadURL") or ""
            if re.search(r"/(Feature|Map)Server(/\d+)?/?$", u):
                layer_url = u.rstrip("/")
                if not re.search(r"/\d+$", layer_url):
                    layer_url += "/0"
                break
        if layer_url:
            # exact "building permit" titles sort first
            score = 0 if re.search(r"building\s*permit", title, re.I) else 1
            candidates.append((score, {"title": title, "layer_url": layer_url,
                                       "landing": ds.get("landingPage", "")}))
    result = [c for _, c in sorted(candidates, key=lambda x: x[0])]
    _cache_put(ck, result, CACHE_TTL_META)
    return result


# --------------------------------------------------------------------------
# Normalization + tagging
# --------------------------------------------------------------------------
def _epoch_to_iso(v):
    if v in (None, "", 0):
        return None
    try:
        if isinstance(v, str):
            v = v.strip()
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
            if m:
                iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                try:  # validate real month/day, reject 2024-13-99 etc.
                    datetime.strptime(iso, "%Y-%m-%d")
                    return iso
                except ValueError:
                    return None
            if not re.match(r"^-?\d+$", v):
                return None
            v = int(v)
        ms = float(v)
        if ms > 1e12:      # epoch millis
            ms /= 1000.0
        elif ms < 1e8:     # not an epoch
            return None
        return datetime.fromtimestamp(ms, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def _to_float(v):
    if v in (None, ""):
        return None
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(v)) or 0) or None
    except Exception:
        return None


# Florida bounding box + ZIP range — a jurisdiction sanity guard. A
# misconfigured source (wrong ArcGIS org) can return another state's permits;
# this drops anything that is provably NOT in Florida so it can never be shown
# under a Florida county. Conservative: only drops when it has clear evidence
# (a ZIP field or geometry that is out of state); keeps records it can't judge.
FL_ZIP_LO, FL_ZIP_HI = 32000, 34999
FL_LAT_LO, FL_LAT_HI = 24.0, 31.2
FL_LON_LO, FL_LON_HI = -87.8, -79.8


def _out_of_florida(p):
    z = p.get("zip")
    if z:
        m = re.search(r"\b(\d{5})\b", str(z))
        if m:
            return not (FL_ZIP_LO <= int(m.group(1)) <= FL_ZIP_HI)
    lat, lon = p.get("lat"), p.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and (lat or lon):
        return not (FL_LAT_LO <= lat <= FL_LAT_HI and FL_LON_LO <= lon <= FL_LON_HI)
    return False


def tag_permit(text):
    tags = [key for key, _label, rx in _COMPILED_TAGS if rx.search(text or "")]
    return tags


def normalize_feature(feature, mapping, source):
    attrs = feature.get("attributes") or feature.get("properties") or {}
    geom = feature.get("geometry") or {}

    def pick(canon):
        f = mapping.get(canon)
        return attrs.get(f) if f else None

    desc = str(pick("description") or "").strip()
    ptype = str(pick("type") or "").strip()
    address = str(pick("address") or "").strip()
    tags = tag_permit(f"{desc} {ptype}")
    county = source.get("county", "")
    lat = geom.get("y")
    lon = geom.get("x")
    if isinstance(geom.get("coordinates"), list) and len(geom["coordinates"]) >= 2:
        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
    # Sanity-clamp coordinates: some layers (e.g. the Miami-Dade EnerGov code-
    # violations layer) store/return projected State Plane values. Only accept
    # geometry that is plausibly lon/lat, else drop it so the FL guard and map
    # never see a bogus 900000-style coordinate.
    if not (isinstance(lat, (int, float)) and -90 <= lat <= 90):
        lat = None
    if not (isinstance(lon, (int, float)) and -180 <= lon <= 180):
        lon = None
    return {
        "source_id": source.get("id"),
        "county": county,
        "category": source.get("category", "permit"),
        "permit_number": str(pick("permit_number") or "").strip() or None,
        "type": ptype or None,
        "status": (str(pick("status") or "").strip() or None),
        "description": desc or None,
        "address": address or None,
        "city": (str(pick("city") or "").strip() or None),
        "zip": (str(pick("zip") or "").strip() or None),
        "issued_date": _epoch_to_iso(pick("issue_date")),
        "applied_date": _epoch_to_iso(pick("applied_date")),
        "value": _to_float(pick("value")),
        "contractor": (str(pick("contractor") or "").strip() or None),
        "owner": (str(pick("owner") or "").strip() or None),
        "lat": lat,
        "lon": lon,
        "tags": tags,
        "appraiser_url": APPRAISER_SEARCH.get(county),
    }


# --------------------------------------------------------------------------
# Per-source fetch
# --------------------------------------------------------------------------
def fetch_source(source, record_count=2000, start_ms=None, end_ms=None):
    """Returns (permits, info). Never raises."""
    info = {"id": source.get("id"), "county": source.get("county"),
            "label": source.get("label"), "status": "error", "count": 0,
            "note": source.get("note"), "portal": source.get("portal")}
    started = time.time()
    attempts = []  # per-step diagnostics surfaced to the health check

    def _discover(sites):
        found, scanned = [], 0
        # 1) Hub v3 search API first — clean JSON, immune to broken DCAT feeds.
        q = source.get("discover_query") or "building permit"
        toks = COUNTY_TOKENS.get(source.get("county"), [])
        try:
            v3 = discover_via_hub_search(q, toks)
            if v3:
                found.extend(v3)
            scanned += 1
        except Exception as e:
            attempts.append(f"hubv3: {str(e)[:120]}")
        # 2) per-site DCAT catalogs as a secondary path.
        for site in sites or []:
            if time.time() - started > SOURCE_BUDGET:
                break
            try:
                found.extend(discover_hub_permit_layers(site))
                scanned += 1
            except Exception as e:
                attempts.append(f"discover {site}: {str(e)[:120]}")
        # de-dupe candidate layers by URL, keeping best-first order.
        seen, uniq = set(), []
        for c in found:
            if c["layer_url"] in seen:
                continue
            seen.add(c["layer_url"])
            uniq.append(c)
        return uniq, scanned

    try:
        # Accela Citizen Access portals (no GIS feed) — scrape the ASP.NET
        # General Search. Handled entirely by the accela adapter.
        if source.get("kind") == "accela_aca":
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            try:
                from accela import scrape_accela
            except ImportError:
                from api.accela import scrape_accela
            end_dt = _dt.fromtimestamp((end_ms or int(time.time() * 1000)) / 1000, tz=_tz.utc)
            start_dt = _dt.fromtimestamp((start_ms or int((time.time() - 730 * 86400) * 1000)) / 1000,
                                        tz=_tz.utc)
            rows, diag = scrape_accela(source.get("agency"), start_dt, end_dt,
                                       module=source.get("module", "Building"))
            county = source.get("county", "")
            permits = []
            for r in rows:
                permits.append({
                    "source_id": source.get("id"), "county": county,
                    "permit_number": r.get("permit_number"), "type": r.get("type"),
                    "status": r.get("status"), "description": r.get("description"),
                    "address": r.get("address"), "city": None, "zip": None,
                    "issued_date": r.get("issued_date"), "applied_date": r.get("applied_date"),
                    "value": r.get("value"), "contractor": r.get("contractor"),
                    "owner": None, "lat": None, "lon": None,
                    "tags": tag_permit(f"{r.get('description') or ''} {r.get('type') or ''}"),
                    "appraiser_url": APPRAISER_SEARCH.get(county),
                })
            info["accela"] = {k: diag.get(k) for k in
                              ("steps", "fields_found", "pages", "parsed", "error")}
            if permits:
                info.update({"status": "ok", "count": len(permits)})
                return permits, info
            info["status"] = "error"
            info["error"] = diag.get("error", "accela scrape returned no rows")
            return [], info

        # Build candidate layer URLs from every strategy the source declares,
        # in priority order: pinned direct layers -> resolved items ->
        # catalog discovery. This lets a source pin a known-good endpoint AND
        # keep discovery as an automatic fallback if that endpoint ever moves.
        layer_urls = []          # ordered candidates to try
        discovered_titles = []
        discovery_ran = False
        discovery_scanned = 0

        # 1) direct, pinned layer URLs (most reliable)
        layer_urls.extend(source.get("layer_urls") or [])

        # 2) Hub dataset ids -> layer URL via Hub v3 (clean JSON; bypasses the
        #    ArcGIS sharing-API permission errors some county items return)
        for did in source.get("hub_dataset_ids") or []:
            try:
                u = resolve_hub_dataset_id(did)
                if u:
                    layer_urls.append(u)
                else:
                    attempts.append(f"hubds {did}: no service url")
            except Exception as e:
                attempts.append(f"hubds {did}: {str(e)[:120]}")

        # 3) ArcGIS Online item IDs -> service layer
        for item_id in source.get("item_ids") or []:
            try:
                layer_urls.append(resolve_item_to_layer(item_id))
            except Exception as e:
                attempts.append(f"item {item_id}: {str(e)[:120]}")

        # 4) open-data catalog discovery (Hub v3 search + DCAT)
        if source.get("hub_sites") or source.get("kind") == "hub_discover":
            discovery_ran = True
            found, discovery_scanned = _discover(source.get("hub_sites"))
            layer_urls.extend(c["layer_url"] for c in found[:3])
            discovered_titles = [c["title"] for c in found[:5]]

        # de-dupe, drop blocklisted false-positive orgs, preserve priority
        seen, ordered, blocked = set(), [], []
        for u in layer_urls:
            if not u or u in seen:
                continue
            seen.add(u)
            if _is_blocked(u):
                blocked.append(u)
                continue
            ordered.append(u)
        if blocked:
            attempts.append(f"blocked {len(blocked)} known-wrong-jurisdiction layer(s)")
        layer_urls = ordered

        if discovered_titles:
            info["discovered"] = discovered_titles

        if not layer_urls:
            # Nothing to try. Distinguish "catalog reachable but empty" from
            # "everything was unreachable" for an honest health status.
            if discovery_ran and discovery_scanned > 0 and not source.get("item_ids") \
                    and not source.get("layer_urls"):
                info["status"] = "no_dataset"
                info["error"] = ("No permit dataset published on this county's open-data "
                                 "portals yet (checked their catalogs).")
                if attempts:
                    info["attempts"] = attempts[:6]
                return [], info
            raise RuntimeError("; ".join(attempts) or "no sources configured")

        last_err = None
        for layer_url in layer_urls:
            if time.time() - started > SOURCE_BUDGET:
                last_err = "source time budget exceeded"
                break
            try:
                meta = layer_metadata(layer_url)
                mapping = map_fields(meta.get("fields"))
                # Explicit per-source field map wins over auto-mapping (used for
                # known-schema layers like the EnerGov code-violations layer and
                # the pinned MDC permit feed) — but ONLY for fields that actually
                # exist in THIS layer. A source can fall back to a *discovered*
                # layer whose schema differs (see the MDC hub-v3 recovery path);
                # forcing the pinned schema onto it would map every field to
                # nothing and silently return empty rows.
                field_map = source.get("field_map") or {}
                _have = {str(f.get("name") or "") for f in (meta.get("fields") or [])}
                _by_ci = {n.lower(): n for n in _have}
                applied_map = {}
                for _k, _v in field_map.items():
                    if not _v:
                        continue
                    # resolve to the layer's REAL field name (casing differs between
                    # the pinned feed and any discovered fallback layer)
                    _real = _v if _v in _have else _by_ci.get(str(_v).lower())
                    if _real:
                        applied_map[_k] = _real
                mapping.update(applied_map)
                _map_fully_applied = bool(field_map) and len(applied_map) == len(
                    [v for v in field_map.values() if v])
                if not mapping.get("issue_date") and not mapping.get("applied_date") \
                        and not mapping.get("permit_number"):
                    raise RuntimeError("layer has no recognizable permit fields")
                order_field = mapping.get("issue_date") or mapping.get("applied_date")
                feats = query_layer(layer_url, order_field=order_field,
                                    date_field=order_field, start_ms=start_ms,
                                    end_ms=end_ms, record_count=record_count,
                                    base_where=source.get("where_clause"))
                # data-driven refinement: recover fields the name-mapper missed
                # and fix an implausible value column, using the real sample.
                # Skip only when the explicit field_map applied IN FULL to this
                # layer (schema known). On a discovered fallback layer it applies
                # partially at best, so we still need the sample-based refinement.
                if not _map_fully_applied:
                    mapping = refine_mapping_with_samples(mapping, meta.get("fields"), feats)
                permits = [normalize_feature(f, mapping, source) for f in feats]
                info.update({
                    "status": "ok", "count": len(permits), "layer_url": layer_url,
                    "layer_name": meta.get("name"),
                    "resolved_fields": mapping,
                    "layer_fields": [{"name": f.get("name"), "type": (f.get("type") or "")
                                      .replace("esriFieldType", "")}
                                     for f in (meta.get("fields") or [])],
                })
                if attempts:
                    info["fallback_notes"] = attempts
                return permits, info
            except Exception as e:
                last_err = str(e)
                attempts.append(f"query {layer_url[:80]}: {str(e)[:120]}")
                continue
        raise RuntimeError(last_err or "no layer urls resolved")
    except Exception as e:
        info["error"] = str(e)[:400]
        if attempts:
            info["attempts"] = attempts[:6]
        return [], info


# --------------------------------------------------------------------------
# Demo dataset (deterministic; used when live sources are unreachable)
# --------------------------------------------------------------------------
_DEMO_ROWS = [
    # (county, city, zip, address, type, description, value, contractor, status)
    ("Miami-Dade", "Miami", "33133", "2740 SW 27TH AVE", "BLDG - RESIDENTIAL",
     "RE-ROOF: REMOVE EXISTING SHINGLES, INSTALL NEW GAF TIMBERLINE SHINGLE ROOF 24 SQ", 18500, "SUNSHINE ROOFERS LLC", "ISSUED"),
    ("Miami-Dade", "Hialeah", "33012", "1290 W 46TH ST", "ELEC - RESIDENTIAL",
     "INSTALL ROOF MOUNTED SOLAR PV SYSTEM 11.2KW WITH BATTERY BACKUP", 34200, "MIA SOLAR CORP", "ISSUED"),
    ("Miami-Dade", "Coral Gables", "33134", "815 CATALONIA AVE", "MECH - RESIDENTIAL",
     "A/C CHANGEOUT 4 TON SPLIT SYSTEM LIKE FOR LIKE", 8900, "COOLBREEZE AIR CONDITIONING", "ISSUED"),
    ("Miami-Dade", "Miami", "33137", "480 NE 29TH ST", "BLDG - COMMERCIAL",
     "INTERIOR BUILD-OUT OF RESTAURANT SPACE 2,400 SF INCLUDING HOOD AND FIRE SUPPRESSION", 265000, "MAGNUM BUILD GROUP", "IN REVIEW"),
    ("Miami-Dade", "Palmetto Bay", "33157", "14805 SW 82ND AVE", "BLDG - RESIDENTIAL",
     "NEW SWIMMING POOL 14X28 WITH PAVER DECK AND CHILD SAFETY FENCE", 68000, "BLUE LAGOON POOLS", "ISSUED"),
    ("Miami-Dade", "Miami Beach", "33139", "1020 WEST AVE", "BLDG - RESIDENTIAL",
     "IMPACT WINDOWS AND DOORS REPLACEMENT (22 OPENINGS) HURRICANE RATED", 41000, "STORMSAFE GLASS LLC", "ISSUED"),
    ("Broward", "Fort Lauderdale", "33301", "600 SE 4TH ST", "ROOF",
     "TILE ROOF REPLACEMENT - REMOVE AND REPLACE CONCRETE TILE 31 SQ", 27400, "ATLANTIC ROOFING SYSTEMS", "ISSUED"),
    ("Broward", "Fort Lauderdale", "33304", "1720 NE 26TH AVE", "PLUMBING",
     "WHOLE HOUSE RE-PIPE COPPER TO PEX, REPLACE WATER HEATER 50 GAL", 9600, "RAPID ROOTER PLUMBING", "ISSUED"),
    ("Broward", "Fort Lauderdale", "33316", "1800 SE 15TH ST", "MARINE",
     "REPLACE 60 LF SEAWALL CAP AND INSTALL NEW 10,000 LB BOAT LIFT", 88000, "INTRACOASTAL MARINE CONSTRUCTION", "ISSUED"),
    ("Broward", "Fort Lauderdale", "33308", "2450 NE 57TH CT", "ELECTRICAL",
     "INSTALL 22KW STANDBY GENERATOR WITH AUTOMATIC TRANSFER SWITCH AND LP TANK", 21500, "POWERGUARD GENERATORS", "ISSUED"),
    ("Broward", "Fort Lauderdale", "33312", "3100 SW 16TH CT", "BUILDING",
     "KITCHEN AND BATHROOM REMODEL, RELOCATE NON-BEARING WALL, NEW CABINETS", 54000, "OWNER/BUILDER", "APPLIED"),
    ("Palm Beach", "West Palm Beach", "33401", "500 CLEMATIS ST", "COMMERCIAL",
     "TENANT IMPROVEMENT - OFFICE BUILD OUT 3RD FLOOR 5,200 SF", 310000, "GULFSTREAM CONSTRUCTION GROUP", "ISSUED"),
    ("Palm Beach", "Boca Raton", "33432", "250 NW 2ND AVE", "RESIDENTIAL",
     "RE-ROOF FLAT TILE TO METAL STANDING SEAM 29 SQ PLUS NEW SKYLIGHTS", 46500, "PALM COAST ROOFING", "ISSUED"),
    ("Palm Beach", "Delray Beach", "33444", "1102 NASSAU ST", "RESIDENTIAL",
     "ADDITION - 480 SF MASTER SUITE ADDITION WITH NEW BATH", 145000, "SEASIDE BUILDERS", "IN REVIEW"),
    ("Palm Beach", "Jupiter", "33458", "180 OCEAN DUNE CIR", "ELECTRICAL",
     "INSTALL EV CHARGER 60A CIRCUIT IN GARAGE (TESLA WALL CONNECTOR)", 2800, "BRIGHT CURRENT ELECTRIC", "ISSUED"),
    ("Palm Beach", "Lake Worth Beach", "33460", "715 LUCERNE AVE", "MECHANICAL",
     "HVAC CHANGE OUT 3.5 TON 16 SEER WITH NEW DUCTWORK", 12400, "EVERCOOL AIR", "ISSUED"),
    ("Martin", "Stuart", "34994", "900 SE OCEAN BLVD", "BUILDING",
     "RE-ROOF METAL 5V CRIMP 18 SQ INCLUDING NEW UNDERLAYMENT", 21000, "TREASURE COAST ROOFING", "ISSUED"),
    ("Martin", "Palm City", "34990", "2201 SW MAPP RD", "POOL",
     "NEW GUNITE POOL AND SPA WITH SCREEN ENCLOSURE AND PAVER DECK", 92000, "AQUA DESIGN POOLS", "ISSUED"),
    ("Martin", "Hobe Sound", "33455", "8735 SE BRIDGE RD", "RESIDENTIAL",
     "NEW SINGLE FAMILY RESIDENCE 2,850 SF CBS CONSTRUCTION", 685000, "COASTAL HAMMOCK HOMES", "APPLIED"),
    ("Martin", "Stuart", "34996", "35 SW FLAGLER AVE", "MARINE",
     "REPLACE EXISTING WOOD DOCK AND INSTALL TWO NEW PILINGS", 38500, "RIVERWORKS MARINE", "ISSUED"),
]


# A few sample code-violation rows so the "Code Violations" data type isn't
# empty in demo mode. (county, city, zip, address, problem, status, folio)
_DEMO_VIOLATIONS = [
    ("Miami-Dade", "Miami", "33127", "220 NW 36 ST",
     "UNSAFE STRUCTURE - ROOF PARTIALLY COLLAPSED, OPEN TO ELEMENTS", "Open", "0132340010010"),
    ("Miami-Dade", "Hialeah", "33010", "455 E 9 ST",
     "WORK WITHOUT PERMIT - UNPERMITTED SECOND-STORY ADDITION", "Lien", "0431210250020"),
    ("Miami-Dade", "Miami", "33150", "8100 NW 2 AVE",
     "DILAPIDATED STRUCTURE / PROPERTY MAINTENANCE - OVERGROWTH AND DEBRIS", "Open", "0131190080030"),
]


def demo_permits(now=None):
    now = now or datetime.now(timezone.utc)
    out = []
    for i, (county, city, zc, addr, ptype, desc, value, contractor, status) in enumerate(_DEMO_ROWS):
        issued = (now - timedelta(days=(i * 3) % 28, hours=i)).strftime("%Y-%m-%d")
        out.append({
            "source_id": "demo",
            "county": county,
            "category": "permit",
            "permit_number": f"DEMO-{now.year}-{1000 + i}",
            "type": ptype,
            "status": status,
            "description": desc,
            "address": addr,
            "city": city,
            "zip": zc,
            "issued_date": issued,
            "applied_date": None,
            "value": float(value),
            "contractor": contractor,
            "owner": None,
            "lat": None,
            "lon": None,
            "tags": tag_permit(f"{desc} {ptype}"),
            "appraiser_url": APPRAISER_SEARCH.get(county),
        })
    for j, (county, city, zc, addr, desc, status, folio) in enumerate(_DEMO_VIOLATIONS):
        opened = (now - timedelta(days=(j * 5) % 25, hours=j)).strftime("%Y-%m-%d")
        out.append({
            "source_id": "demo",
            "county": county,
            "category": "violation",
            "permit_number": f"DEMO-CE-{now.year}-{200 + j}",
            "type": "Code Violation",
            "status": status,
            "description": desc,
            "address": addr,
            "city": city,
            "zip": zc,
            "issued_date": opened,
            "applied_date": None,
            "value": None,
            "contractor": None,
            "owner": folio,
            "lat": None,
            "lon": None,
            "tags": tag_permit(desc),
            "appraiser_url": APPRAISER_SEARCH.get(county),
        })
    return out


# --------------------------------------------------------------------------
# Search orchestration
# --------------------------------------------------------------------------
def _parse_counties(raw):
    if not raw:
        return list(COUNTIES)
    wanted = []
    for tok in raw.split(","):
        tok = tok.strip().lower().replace("miami dade", "miami-dade")
        # accept URL-safe slugs too (palm-beach, miami_dade, ...)
        tok = tok.replace("palm-beach", "palm beach").replace("palm_beach", "palm beach")
        tok = tok.replace("miami_dade", "miami-dade")
        if tok in ("dade", "miamidade"):
            tok = "miami-dade"
        for c in COUNTIES:
            if tok and (tok == c.lower() or tok in c.lower()) and c not in wanted:
                wanted.append(c)
    return wanted or list(COUNTIES)


def _clamp_int(v, default, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return default


def _subtract_months(dt, months):
    total = dt.year * 12 + (dt.month - 1) - months
    y, m = divmod(total, 12)
    m += 1
    from calendar import monthrange
    day = min(dt.day, monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=day)


def compute_window(params, now=None):
    """Resolve the requested time window into (start_dt, end_dt, label).
    Supports: year=YYYY (a whole calendar year), years=N, months=N, days=N
    (default 30). Explicit start/end (YYYY-MM-DD) override everything."""
    now = now or datetime.now(timezone.utc)

    def _parse_iso(s):
        try:
            return datetime.strptime(s.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None

    start_s = _parse_iso(params.get("start") or "")
    end_s = _parse_iso(params.get("end") or "")
    if start_s or end_s:
        s = start_s or datetime(2000, 1, 1, tzinfo=timezone.utc)
        e = end_s or now
        return s, e, f"{s.strftime('%Y-%m-%d')} → {e.strftime('%Y-%m-%d')}"

    if params.get("year"):
        y = _clamp_int(params.get("year"), now.year, 2000, now.year)
        start = datetime(y, 1, 1, tzinfo=timezone.utc)
        end = datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        return start, min(end, now), str(y)

    if params.get("years"):
        n = _clamp_int(params.get("years"), 1, 1, 25)
        try:
            start = now.replace(year=now.year - n)
        except ValueError:  # Feb 29
            start = now.replace(year=now.year - n, day=28)
        return start, now, f"last {n} year{'s' if n > 1 else ''}"

    if params.get("months"):
        n = _clamp_int(params.get("months"), 6, 1, 300)
        return _subtract_months(now, n), now, f"last {n} months"

    n = _clamp_int(params.get("days"), 30, 1, 3660)
    return now - timedelta(days=n), now, f"last {n} days"


def run_search(params):
    counties = _parse_counties(params.get("county") or params.get("counties") or "")
    now = datetime.now(timezone.utc)
    start_dt, end_dt, window_label = compute_window(params, now)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    start_iso = start_dt.strftime("%Y-%m-%d")
    end_iso = end_dt.strftime("%Y-%m-%d")
    try:
        limit = max(1, min(5000, int(params.get("limit") or 250)))
    except Exception:
        limit = 250
    tags_filter = [t.strip() for t in (params.get("tags") or "").split(",") if t.strip()]
    q = (params.get("q") or "").strip().lower()
    min_value = _to_float(params.get("min_value"))
    force_demo = str(params.get("demo") or "") in ("1", "true", "yes")
    source_filter = (params.get("source") or "").strip()
    category = (params.get("category") or "").strip().lower()  # "", permit, violation

    cache_key = (f"search:{sorted(counties)}:{start_iso}:{end_iso}:{limit}:{tags_filter}"
                 f":{q}:{min_value}:{force_demo}:{source_filter}:{category}")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    sources = [s for s in load_sources() if s.get("county") in counties]
    if source_filter:
        sources = [s for s in sources if s.get("id") == source_filter]
    if category:
        sources = [s for s in sources if s.get("category", "permit") == category]

    all_permits, infos = [], []
    if force_demo:
        all_permits = [p for p in demo_permits() if p["county"] in counties]
        infos = [{"id": "demo", "county": "all", "label": "Bundled sample data",
                  "status": "demo", "count": len(all_permits)}]
    elif sources:
        with ThreadPoolExecutor(max_workers=min(4, len(sources))) as pool:
            futures = {pool.submit(fetch_source, s, 2000, start_ms, end_ms): s
                       for s in sources}
            done = set()
            try:
                # whole-request budget (must stay under vercel maxDuration) so a
                # hung source can't 504 the function — remaining sources are
                # cancelled and reported as timeouts.
                for fut in as_completed(futures, timeout=REQUEST_BUDGET):
                    done.add(fut)
                    try:
                        permits, info = fut.result()
                    except Exception as e:  # future-level failure
                        s = futures[fut]
                        permits, info = [], {"id": s.get("id"), "county": s.get("county"),
                                             "label": s.get("label"), "status": "error",
                                             "count": 0, "error": str(e)[:400]}
                    all_permits.extend(permits)
                    infos.append(info)
            except FuturesTimeout:
                for fut, s in futures.items():
                    if fut not in done:
                        fut.cancel()
                        infos.append({"id": s.get("id"), "county": s.get("county"),
                                      "label": s.get("label"), "status": "timeout",
                                      "count": 0, "error": "source timed out"})

    # Demo fallback fires ONLY on genuine failure — i.e. no source actually
    # reported data-bearing status. A source that succeeded but honestly
    # returned 0 rows (e.g. "open violations, last 7 days") must NOT be masked
    # with fabricated sample rows.
    any_source_ok = any(i.get("status") in ("ok", "no_dataset") for i in infos)
    demo_used = force_demo
    if not all_permits and not force_demo and not any_source_ok:
        all_permits = [p for p in demo_permits() if p["county"] in counties]
        demo_used = True

    dropped_geo = [0]

    def keep(p):
        if _out_of_florida(p):        # wrong-jurisdiction guard
            dropped_geo[0] += 1
            return False
        if category and p.get("category", "permit") != category:
            return False
        d = p.get("issued_date") or p.get("applied_date")
        if d and (d < start_iso or d > end_iso):
            return False
        if tags_filter and not (set(tags_filter) & set(p.get("tags") or [])):
            return False
        if min_value is not None and (p.get("value") or 0) < min_value:
            return False
        if q:
            hay = " ".join(str(p.get(k) or "") for k in
                           ("description", "address", "contractor", "permit_number",
                            "type", "city", "owner")).lower()
            if q not in hay:
                return False
        return True

    filtered = [p for p in all_permits if keep(p)]
    filtered.sort(key=lambda p: (p.get("issued_date") or p.get("applied_date") or ""),
                  reverse=True)
    filtered = filtered[:limit]

    result = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"counties": counties, "window": window_label,
                   "start": start_iso, "end": end_iso, "tags": tags_filter, "q": q,
                   "min_value": min_value, "limit": limit},
        "demo": demo_used,
        "sources": infos,
        "dropped_out_of_state": dropped_geo[0],
        "count": len(filtered),
        "permits": filtered,
    }
    _cache_put(cache_key, result, CACHE_TTL_RESULTS)
    return result


# --------------------------------------------------------------------------
# Re-roof lead shaping (post-re-roof anchor-recertification campaign)
# --------------------------------------------------------------------------
def _reroof_pitch(p):
    """One-line, board-ready reason this re-roof is an anchor-recert lead."""
    parts = ["Re-roof permit"]
    if p.get("permit_number"):
        parts.append("#" + str(p["permit_number"]))
    d = p.get("issued_date") or p.get("applied_date")
    if d:
        parts.append("issued " + d)
    if p.get("contractor"):
        parts.append("by " + str(p["contractor"]))
    return (" ".join(parts) + " — the roof was torn off and replaced, so the "
            "rooftop fall-protection anchors were disturbed and their OSHA "
            "1910.27(b) certification is now void. Anchor re-certification is due "
            "before any window-washing or facade crew uses the roof.")


def run_reroof_leads(params):
    """Recent FULL re-roof permits, shaped as anchor-recertification leads.
    Defaults to the counties with queryable permit feeds (Miami-Dade + Broward)
    and an 18-month lookback (the window in which anchors still need recert)."""
    args = dict(params)
    args.setdefault("counties", "Miami-Dade,Broward")
    args.setdefault("months", "18")
    args.setdefault("limit", "500")
    args["tags"] = "reroof"            # force the high-signal tag
    args.pop("category", None)         # permits only, never violations
    data = run_search(args)
    leads = []
    for p in data.get("permits", []):
        if not p.get("address"):
            continue
        leads.append({
            "address": p.get("address"),
            "city": p.get("city"),
            "county": p.get("county"),
            "permit_number": p.get("permit_number"),
            "issued_date": p.get("issued_date") or p.get("applied_date"),
            "contractor": p.get("contractor"),
            "type": p.get("type"),
            "description": p.get("description"),
            "value": p.get("value"),
            "appraiser_url": p.get("appraiser_url"),
            "pitch": _reroof_pitch(p),
        })
    return {
        "ok": True,
        "generated_at": data.get("generated_at"),
        "window": data.get("params", {}).get("window"),
        "counties": data.get("params", {}).get("counties"),
        "demo": data.get("demo"),
        "sources": data.get("sources"),
        "count": len(leads),
        "leads": leads,
    }


# --------------------------------------------------------------------------
# Flask wiring
# --------------------------------------------------------------------------
def register_permits_routes(app):
    from flask import jsonify, request, Response

    @app.route("/api/permits/reroof", methods=["GET"])
    def permits_reroof():
        """Post-re-roof anchor-recertification lead list. Recent full re-roof
        permits in Miami-Dade + Broward (override with ?counties= &months= &limit=
        &city= via q). Each lead carries a ready pitch line."""
        return jsonify(run_reroof_leads(request.args))

    @app.route("/api/permits/search", methods=["GET"])
    def permits_search():
        return jsonify(run_search(request.args))

    @app.route("/api/permits/tags", methods=["GET"])
    def permits_tags():
        return jsonify({"ok": True, "tags": [
            {"key": key, "label": label} for key, label, _ in TAG_RULES]})

    @app.route("/api/permits/sources", methods=["GET"])
    def permits_sources():
        sources = load_sources()
        check = str(request.args.get("check") or "") in ("1", "true")
        health = {}
        if check:
            # Probe every source concurrently with a bounded wall-clock budget
            # so the endpoint returns within the serverless timeout even when a
            # source (Accela scrape, discovery) is slow.
            def probe(s):
                _, info = fetch_source(s, record_count=5)
                return s["id"], {k: info.get(k) for k in
                                 ("status", "error", "layer_url", "layer_name",
                                  "count", "discovered", "attempts", "fallback_notes",
                                  "resolved_fields", "layer_fields", "accela")}
            with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
                futs = {pool.submit(probe, s): s for s in sources}
                try:
                    for fut in as_completed(futs, timeout=SOURCE_BUDGET + 5):
                        try:
                            sid, h = fut.result()
                            health[sid] = h
                        except Exception as e:
                            health[futs[fut]["id"]] = {"status": "error",
                                                       "error": str(e)[:200]}
                except FuturesTimeout:
                    for fut, s in futs.items():
                        health.setdefault(s["id"], {"status": "timeout",
                                                    "error": "health probe exceeded budget"})
        out = []
        for s in sources:
            entry = {k: s.get(k) for k in
                     ("id", "county", "label", "kind", "portal", "note")}
            if check:
                entry["health"] = health.get(s["id"], {"status": "timeout"})
            out.append(entry)
        return jsonify({"ok": True, "sources": out,
                        "appraisers": APPRAISER_SEARCH, "counties": COUNTIES})

    @app.route("/api/permits/discover", methods=["GET"])
    def permits_discover():
        """Scan a hub site (or all configured hub_discover sources) for
        permit datasets — admin helper for expanding coverage."""
        site = (request.args.get("site") or "").strip()
        results = {}
        if site:
            if not re.match(r"^https://[a-z0-9.\-]+(\.arcgis\.com|\.gov|\.us|\.org)/?$", site, re.I):
                return jsonify({"ok": False,
                                "error": "site must be an https URL on .arcgis.com, .gov, .us, or .org"}), 400
            try:
                results[site] = discover_hub_permit_layers(site)
            except Exception as e:
                results[site] = {"error": str(e)[:300]}
        else:
            for s in load_sources():
                if s.get("kind") != "hub_discover":
                    continue
                for hub in s.get("hub_sites") or []:
                    try:
                        results[hub] = discover_hub_permit_layers(hub)
                    except Exception as e:
                        results[hub] = {"error": str(e)[:300]}
        return jsonify({"ok": True, "results": results})

    @app.route("/api/permits/export.csv", methods=["GET"])
    def permits_export():
        # CSV should carry the whole window, not just the page-view cap.
        args = dict(request.args)
        args.setdefault("limit", "5000")
        data = run_search(args)
        buf = io.StringIO()
        cols = ["issued_date", "category", "county", "city", "permit_number", "type",
                "status", "description", "address", "zip", "value", "contractor",
                "owner", "tags", "applied_date", "source_id", "appraiser_url"]
        w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in data["permits"]:
            row = dict(p)
            row["tags"] = "|".join(p.get("tags") or [])
            w.writerow(row)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return Response(
            buf.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition":
                     f"attachment; filename=soflo-permit-leads-{stamp}.csv"})

    return app

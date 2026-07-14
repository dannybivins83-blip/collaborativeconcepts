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
HTTP_TIMEOUT = 12          # per outbound request, seconds
SOURCE_BUDGET = 25         # per-source total budget, seconds
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
        "label": "Miami-Dade County — Building Permits (countywide)",
        "kind": "arcgis_item",
        "item_ids": [
            "31cd319f45544648b59f0418aea60091",  # "Building Permit" (rolling ~3 years, points)
            "f2181fb7e4ae46adbc633e478a607226",  # "Building Permits Issued by MDC" (2 yrs+)
        ],
        # if the pinned items ever move, discovery finds the current layer:
        "hub_sites": ["https://gis-mdc.opendata.arcgis.com",
                      "https://opendata.miamidade.gov"],
        "portal": "https://gis-mdc.opendata.arcgis.com/datasets/MDC::building-permit/about",
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
        "note": "Broward issues permits per-municipality; Fort Lauderdale is the largest single source. Add more cities via PERMITS_EXTRA_SOURCES.",
    },
    {
        "id": "pbc",
        "county": "Palm Beach",
        "label": "Palm Beach — county + West Palm Beach open-data discovery",
        "kind": "hub_discover",
        "hub_sites": [
            "https://opendata2-pbcgov.opendata.arcgis.com",
            "https://gisportal-wpbgis.opendata.arcgis.com",
        ],
        "portal": "https://opendata2-pbcgov.opendata.arcgis.com/",
        "note": "PBC does not publish a stable countywide permits layer; the DCAT catalogs are scanned at runtime for permit datasets.",
    },
    {
        "id": "martin",
        "county": "Martin",
        "label": "Martin County — open-data discovery",
        "kind": "hub_discover",
        "hub_sites": [
            "https://data-mcgov.opendata.arcgis.com",
        ],
        "portal": "https://data-mcgov.opendata.arcgis.com/",
        "note": "Martin County permits live in Accela; the open-data catalog is scanned at runtime for permit/development datasets.",
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


def query_layer(layer_url, order_field=None, record_count=2000):
    """Pull recent records. Uses where=1=1 + server-side ORDER BY when
    available (date filtering happens client-side — avoids per-server SQL
    dialect problems). Falls back to unordered query if ORDER BY errors."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "resultRecordCount": record_count,
        "returnGeometry": "true",
        "outSR": 4326,
    }
    if order_field:
        params["orderByFields"] = f"{order_field} DESC"
    data = _get_json(f"{layer_url}/query", params=params, timeout=HTTP_TIMEOUT + 8)
    if data.get("error") and order_field:
        params.pop("orderByFields", None)
        data = _get_json(f"{layer_url}/query", params=params, timeout=HTTP_TIMEOUT + 8)
    if data.get("error"):
        raise RuntimeError(f"query error: {data['error'].get('message', 'error')}")
    return data.get("features") or []


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
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
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
    return {
        "source_id": source.get("id"),
        "county": county,
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
        "lat": lat if isinstance(lat, (int, float)) else None,
        "lon": lon if isinstance(lon, (int, float)) else None,
        "tags": tags,
        "appraiser_url": APPRAISER_SEARCH.get(county),
    }


# --------------------------------------------------------------------------
# Per-source fetch
# --------------------------------------------------------------------------
def fetch_source(source, record_count=2000):
    """Returns (permits, info). Never raises."""
    info = {"id": source.get("id"), "county": source.get("county"),
            "label": source.get("label"), "status": "error", "count": 0,
            "note": source.get("note"), "portal": source.get("portal")}
    started = time.time()
    attempts = []  # per-step diagnostics surfaced to the health check

    def _discover(sites):
        found, scanned = [], 0
        for site in sites or []:
            if time.time() - started > SOURCE_BUDGET:
                break
            try:
                found.extend(discover_hub_permit_layers(site))
                scanned += 1
            except Exception as e:
                attempts.append(f"discover {site}: {str(e)[:120]}")
        return found, scanned

    try:
        kind = source.get("kind")
        layer_urls = []          # ordered candidates to try
        discovered_titles = []

        if kind == "arcgis_layer":
            layer_urls = list(source.get("layer_urls") or [])
        elif kind == "arcgis_item":
            for item_id in source.get("item_ids") or []:
                try:
                    layer_urls.append(resolve_item_to_layer(item_id))
                except Exception as e:
                    attempts.append(f"item {item_id}: {str(e)[:120]}")
            # graceful fallback: if the pinned items can't resolve, discover
            # the current permit layer from the county's own open-data catalog.
            if source.get("hub_sites"):
                found, _ = _discover(source["hub_sites"])
                layer_urls.extend(c["layer_url"] for c in found[:2])
                discovered_titles = [c["title"] for c in found[:5]]
            if not layer_urls:
                raise RuntimeError("; ".join(attempts) or "no item ids configured")
        elif kind == "hub_discover":
            found, scanned = _discover(source.get("hub_sites"))
            if not found:
                if scanned == 0:
                    raise RuntimeError("; ".join(attempts) or "no hub sites configured")
                info["status"] = "no_dataset"
                info["error"] = ("No permit dataset published on this county's open-data "
                                 "portals yet (checked their DCAT catalogs).")
                return [], info
            layer_urls = [c["layer_url"] for c in found[:3]]
            discovered_titles = [c["title"] for c in found[:5]]
        else:
            raise RuntimeError(f"unknown source kind: {kind}")

        if discovered_titles:
            info["discovered"] = discovered_titles

        last_err = None
        for layer_url in layer_urls:
            if time.time() - started > SOURCE_BUDGET:
                last_err = "source time budget exceeded"
                break
            try:
                meta = layer_metadata(layer_url)
                mapping = map_fields(meta.get("fields"))
                if not mapping.get("issue_date") and not mapping.get("applied_date") \
                        and not mapping.get("permit_number"):
                    raise RuntimeError("layer has no recognizable permit fields")
                order_field = mapping.get("issue_date") or mapping.get("applied_date")
                feats = query_layer(layer_url, order_field=order_field,
                                    record_count=record_count)
                permits = [normalize_feature(f, mapping, source) for f in feats]
                info.update({
                    "status": "ok", "count": len(permits), "layer_url": layer_url,
                    "layer_name": meta.get("name"),
                    "resolved_fields": mapping,
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


def demo_permits(now=None):
    now = now or datetime.now(timezone.utc)
    out = []
    for i, (county, city, zc, addr, ptype, desc, value, contractor, status) in enumerate(_DEMO_ROWS):
        issued = (now - timedelta(days=(i * 3) % 28, hours=i)).strftime("%Y-%m-%d")
        out.append({
            "source_id": "demo",
            "county": county,
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
        if tok == "dade":
            tok = "miami-dade"
        for c in COUNTIES:
            if tok and (tok == c.lower() or tok in c.lower()) and c not in wanted:
                wanted.append(c)
    return wanted or list(COUNTIES)


def run_search(params):
    counties = _parse_counties(params.get("county") or params.get("counties") or "")
    try:
        days = max(1, min(365, int(params.get("days") or 30)))
    except Exception:
        days = 30
    try:
        limit = max(1, min(2000, int(params.get("limit") or 250)))
    except Exception:
        limit = 250
    tags_filter = [t.strip() for t in (params.get("tags") or "").split(",") if t.strip()]
    q = (params.get("q") or "").strip().lower()
    min_value = _to_float(params.get("min_value"))
    force_demo = str(params.get("demo") or "") in ("1", "true", "yes")
    source_filter = (params.get("source") or "").strip()

    cache_key = f"search:{sorted(counties)}:{days}:{limit}:{tags_filter}:{q}:{min_value}:{force_demo}:{source_filter}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    sources = [s for s in load_sources() if s.get("county") in counties]
    if source_filter:
        sources = [s for s in sources if s.get("id") == source_filter]

    all_permits, infos = [], []
    if force_demo:
        all_permits = [p for p in demo_permits() if p["county"] in counties]
        infos = [{"id": "demo", "county": "all", "label": "Bundled sample data",
                  "status": "demo", "count": len(all_permits)}]
    elif sources:
        with ThreadPoolExecutor(max_workers=min(4, len(sources))) as pool:
            futures = {pool.submit(fetch_source, s): s for s in sources}
            done = set()
            try:
                for fut in as_completed(futures, timeout=SOURCE_BUDGET + 10):
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

    demo_used = force_demo
    if not all_permits and not force_demo:
        # every live source failed or was empty -> serve labeled sample data
        all_permits = [p for p in demo_permits() if p["county"] in counties]
        demo_used = True

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    def keep(p):
        d = p.get("issued_date") or p.get("applied_date")
        if d and d < cutoff:
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
        "params": {"counties": counties, "days": days, "tags": tags_filter, "q": q,
                   "min_value": min_value, "limit": limit},
        "demo": demo_used,
        "sources": infos,
        "count": len(filtered),
        "permits": filtered,
    }
    _cache_put(cache_key, result, CACHE_TTL_RESULTS)
    return result


# --------------------------------------------------------------------------
# Flask wiring
# --------------------------------------------------------------------------
def register_permits_routes(app):
    from flask import jsonify, request, Response

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
        out = []
        for s in sources:
            entry = {k: s.get(k) for k in
                     ("id", "county", "label", "kind", "portal", "note")}
            if str(request.args.get("check") or "") in ("1", "true"):
                _, info = fetch_source(s, record_count=5)
                entry["health"] = {k: info.get(k) for k in
                                   ("status", "error", "layer_url", "layer_name",
                                    "count", "discovered", "attempts", "fallback_notes")}
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
        data = run_search(request.args)
        buf = io.StringIO()
        cols = ["issued_date", "county", "city", "permit_number", "type", "status",
                "description", "address", "zip", "value", "contractor", "owner",
                "tags", "applied_date", "source_id", "appraiser_url"]
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

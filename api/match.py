"""
Address-list matcher — cross-reference a list of addresses (e.g. a CRM export
of solar leads) against the permit engine's records.

Given a pasted list of addresses and a project tag (default "solar"), it pulls
the tagged permits from the live engine and reports, per input address, whether
a matching permit exists on record — so you can see which canceled/old leads
actually pulled a permit (often with a competitor).

Matching is normalization-based (house number + normalized street + ZIP), not
exact-string, so "810 North A Street" matches "810 N A ST". Pure functions here
are unit-tested offline; the live fetch happens via the engine on the server.
"""

import re

# street-type + directional canonicalization
_SUFFIX = {
    "street": "st", "st": "st", "avenue": "ave", "ave": "ave", "av": "ave",
    "road": "rd", "rd": "rd", "drive": "dr", "dr": "dr", "lane": "ln", "ln": "ln",
    "court": "ct", "ct": "ct", "circle": "cir", "cir": "cir", "boulevard": "blvd",
    "blvd": "blvd", "place": "pl", "pl": "pl", "way": "way", "terrace": "ter",
    "ter": "ter", "trail": "trl", "trl": "trl", "parkway": "pkwy", "pkwy": "pkwy",
    "highway": "hwy", "hwy": "hwy", "square": "sq", "loop": "loop", "run": "run",
    "path": "path", "pike": "pike", "crossing": "xing", "point": "pt", "pt": "pt",
}
_DIR = {"north": "n", "south": "s", "east": "e", "west": "w",
        "n": "n", "s": "s", "e": "e", "w": "w", "ne": "ne", "nw": "nw",
        "se": "se", "sw": "sw", "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw"}
_UNIT_RX = re.compile(r"\b(apt|apartment|unit|ste|suite|bldg|building|lot|rm|room|fl|floor|#)\b.*$", re.I)
_ORD_RX = re.compile(r"^(\d+)(st|nd|rd|th)$", re.I)
_ZIP_RX = re.compile(r"\b(3\d{4})(?:-\d{4})?\b")   # FL ZIPs


def normalize_address(s):
    """-> {'num','street','zip','raw'}. Empty num/street when unparseable."""
    raw = (s or "").strip()
    up = raw.upper()
    zc = _ZIP_RX.search(up)
    zipc = zc.group(1) if zc else ""

    # leading house number
    m = re.match(r"\s*(\d+)\s+(.*)", up)
    num = m.group(1) if m else ""
    rest = m.group(2) if m else up

    # keep only the street portion (before the first comma = city)
    street_part = rest.split(",")[0]
    street_part = _UNIT_RX.sub("", street_part)

    toks = re.findall(r"[A-Z0-9]+", street_part)
    out = []
    for t in toks:
        tl = t.lower()
        if tl in _DIR:
            out.append(_DIR[tl])
        elif tl in _SUFFIX:
            out.append(_SUFFIX[tl])
        else:
            om = _ORD_RX.match(tl)          # 42ND -> 42, 7TH -> 7
            out.append(om.group(1) if om else tl)
    return {"num": num, "street": " ".join(out), "zip": zipc, "raw": raw}


# generic tokens carry no identity — a shared "ln" or "n" must never make a match
_GENERIC_TOK = set(_SUFFIX.values()) | set(_DIR.values())


def addr_matches(a, b):
    """True if two normalized addresses are the same property. Requires the
    house number to match AND the DISTINCTIVE street-name tokens to overlap
    (a shared suffix/directional alone never counts). ZIP corroborates but
    cannot rescue a name mismatch."""
    if not a["num"] or a["num"] != b["num"]:
        return False
    at = set(a["street"].split())
    bt = set(b["street"].split())
    if not at or not bt:
        return False
    an = at - _GENERIC_TOK          # distinctive (name) tokens only
    bn = bt - _GENERIC_TOK
    if an and bn:
        name_overlap = len(an & bn) / min(len(an), len(bn))
    else:                            # both are only generic (e.g. "Main St" vs "Main")
        name_overlap = 1.0 if an == bn else 0.0
    contained = a["street"] in b["street"] or b["street"] in a["street"]
    if name_overlap < 0.5 and not contained:
        return False
    zip_ok = bool(a["zip"]) and a["zip"] == b["zip"]
    return zip_ok or name_overlap >= 0.67 or contained


def match_list(inputs, permits):
    """inputs: [{... 'address' or 'num'/'street'/'zip', optional 'name','status'}]
    permits: engine permit dicts (with 'address'/'zip'/'city').
    Returns [{input, matched:bool, permits:[...]}] preserving input order."""
    # normalize permits once
    norm_permits = []
    for p in permits:
        addr = p.get("address") or ""
        # append zip from the record if the address string lacks one
        n = normalize_address(addr)
        if not n["zip"] and p.get("zip"):
            zm = _ZIP_RX.search(str(p.get("zip")))
            if zm:
                n["zip"] = zm.group(1)
        norm_permits.append((n, p))

    results = []
    for item in inputs:
        if item.get("address"):
            key = normalize_address(item["address"])
        else:
            key = {"num": str(item.get("num", "")),
                   "street": normalize_address(item.get("street", ""))["street"],
                   "zip": str(item.get("zip", "")), "raw": item.get("street", "")}
        hits = []
        for n, p in norm_permits:
            if addr_matches(key, n):
                hits.append({
                    "permit_number": p.get("permit_number"),
                    "issued_date": p.get("issued_date") or p.get("applied_date"),
                    "description": p.get("description"),
                    "address": p.get("address"),
                    "city": p.get("city"), "county": p.get("county"),
                    "contractor": p.get("contractor"),
                    "tags": p.get("tags"),
                })
        results.append({
            "input": {k: item.get(k) for k in ("name", "address", "city",
                                               "zip", "status") if item.get(k)},
            "normalized": key["num"] + " " + key["street"] + (" " + key["zip"] if key["zip"] else ""),
            "matched": bool(hits),
            "permits": hits,
        })
    return results


def parse_pasted(text):
    """Turn a pasted block (one address per line, optional 'Name | Address' or
    'Name, 123 Main St, City FL 33333') into input records."""
    items = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        name = ""
        addr = line
        # split "Name | address" or "Name — address"
        for sep in ("|", "\t", " — ", "  "):
            if sep in line:
                left, right = line.split(sep, 1)
                if _ZIP_RX.search(right) or re.search(r"\d+\s+\w", right):
                    name, addr = left.strip(), right.strip()
                    break
        items.append({"name": name, "address": addr})
    return items

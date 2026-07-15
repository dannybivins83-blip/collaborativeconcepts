"""
WWSLGC portal API (Vercel Python / Flask).

Internal outreach mailer. The portal opens WITHOUT a forced login (it stores no
lead data server-side -- CSVs are parsed in the browser). A mailbox connection
is required only to actually send/draft, and the user can connect either:
  - Microsoft 365 (Outlook) via Graph, or
  - Google (Gmail) via the Gmail API.
Drafts/sends land in the connected account's own mailbox.

No secrets live in the repo; everything sensitive comes from Vercel env vars.

Env vars:
  MS_CLIENT_ID / MS_CLIENT_SECRET / MS_TENANT_ID   Entra app (Microsoft path)
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET           Google Cloud OAuth (Gmail path)
  SESSION_SECRET                                    signs/encrypts the session cookie
  WWSLGC_REDIRECT_URI / GOOGLE_REDIRECT_URI         optional explicit redirect URIs
  ALLOWED_EMAIL_DOMAIN                              optional Microsoft domain restriction
"""

import base64
import hashlib
import json
import os
import re
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import requests
from flask import Flask, request, redirect, jsonify, make_response
from cryptography.fernet import Fernet, InvalidToken
import msal

app = Flask(__name__)

# ---- Microsoft Graph ----
GRAPH = "https://graph.microsoft.com/v1.0"
MS_SCOPES = ["User.Read", "Mail.Send", "Mail.ReadWrite"]

# ---- Google / Gmail ----
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.compose"]

SESSION_COOKIE = "wwslgc_session"
FLOW_COOKIE = "wwslgc_flow"
GSTATE_COOKIE = "wwslgc_gstate"
ALLOWED_DOMAIN = os.environ.get("ALLOWED_EMAIL_DOMAIN", "").lower()

SIGNATURE = (
    "Daniel Bivins · Client Relations\n"
    "La Gala Construction / Tilt Patchers, Inc. · CGC059211 · in partnership with a FL State Certified Engineer\n"
    "(561) 475-8615 · danny@lagalacon.com · lagalacon.com\n"
    "25 SE 7th Street, Suite 12, Deerfield Beach, FL 33441\n"
    "Reply STOP or UNSUBSCRIBE to opt out."
)
TEMPLATES = [
    {"name": "Cold intro — open OSHA item",
     "subject": "Closing out the fall-protection item at {{Company}}",
     "body": ("Hi {{First}},\n\nI saw {{Company}} has an open OSHA walking-surface matter on the "
              "public record (§{{Standard}}) at the {{City}} location. We're a licensed Florida GC "
              "(CGC059211) that self-performs the work that closes that out — guardrail, edge "
              "protection, concrete/coating repair, anchor install/replacement, and Complete "
              "Building Code Compliant Recertifications — and a FL State Certified Engineer "
              "provides the sealed inspection and the 5,000-lb anchor "
              "certification. One team for both the certificate and the fix.\n\nCan I set up a free "
              "walking-surface assessment this week and get you documentation for your file? "
              "Flyer attached.\n\n" + SIGNATURE)},
    {"name": "Free assessment offer",
     "subject": "Free walking-surface assessment for {{Company}}",
     "body": ("Hi {{First}},\n\nWe're offering a no-obligation walking-surface assessment for "
              "facilities in {{County}} County with open OSHA Subpart D items. La Gala (CGC059211) "
              "self-performs the surface, edge, and anchor work plus Complete Building Code "
              "Compliant Recertifications; a FL State Certified Engineer seals the inspection and "
              "any anchor certification — one accountable team, one point of contact.\n\nYou'd get a "
              "clear written scope plus documentation for your case file. Do you have 20 minutes "
              "this week? Flyer attached.\n\n" + SIGNATURE)},
    {"name": "Follow-up — no reply",
     "subject": "Following up — {{Company}} walking-surface item",
     "body": ("Hi {{First}},\n\nCircling back on the open OSHA walking-surface item (§{{Standard}}) "
              "at {{Company}}. We can scope it this week and hand you documentation for your file at "
              "no cost — we self-perform the fix and a FL State Certified Engineer seals the "
              "engineered sign-off where one is needed.\n\nWant me to set up the free assessment?\n\n" + SIGNATURE)},
    {"name": "Blank — write your own",
     "subject": "",
     "body": "Hi {{First}},\n\n\n\n" + SIGNATURE},
]

# --------------------------------------------------------------------------
# Collaborative Concept — PBC trades outreach (Outcome AI offer)
# Merge fields: {{First}} {{Company}} {{City}} {{Trade}}
# --------------------------------------------------------------------------
CC_SIGNATURE = (
    "Danny Bivins · Collaborative Concept\n"
    "(561) 475-8615 · dannybivins83@gmail.com · Palm Beach County, FL\n"
    "I build it — you only pay if it works.\n"
    "Reply STOP or UNSUBSCRIBE to opt out."
)

TRADES_TEMPLATES = [
    {"name": "Roofing — cold (AccuLynx admin)", "trade": "Roofing",
     "subject": "Quick one for {{Company}} — contractor to contractor",
     "body": ("Hi {{First}},\n\nI'll keep this short. I was born and raised here and spent 10+ years in "
              "roofing in Palm Beach County, so I know the process and the headaches that come with it. "
              "These days I help small roofing companies cut the office grind — honestly the part of this "
              "I enjoy most.\n\nIf {{Company}} runs AccuLynx, your office is probably burning close to a "
              "full work-week every week exporting it, re-keying reports, and chasing stale leads by hand. "
              "I built a tool that automates exactly that for my own shop — it cut about 125 admin hours a "
              "month, roughly $4,000. I'll white-label the same thing as {{Company}}'s own internal "
              "system.\n\nAnd unlike the software you're paying for now — AccuLynx, CompanyCam, the rest: no "
              "licensing fee, unlimited users, and it ties right into the third-party apps you already run. "
              "Where it makes sense, I can rebuild those tools as your own — picture a CompanyCam-style photo "
              "app branded to {{Company}} with no per-seat bill — so you stop paying their monthly licenses "
              "for good.\n\nNo retainer. We baseline your current admin hours and I take a share only of what "
              "it measurably saves you, tracked on a shared dashboard. If it doesn't save you money, you "
              "owe me nothing — only the software cost is ever upfront.\n\nWorth 20 minutes to look at the "
              "number on your shop?\n\n" + CC_SIGNATURE)},

    {"name": "AC/HVAC — cold (speed-to-lead)", "trade": "AC/HVAC",
     "subject": "The after-hours calls {{Company}} is missing are booked jobs",
     "body": ("Hi {{First}},\n\nQuick one, contractor to contractor. I'm local — born and raised here, "
              "10+ years in construction and the trades around Palm Beach County — and these days I help "
              "small shops stop leaving money on the table.\n\nEvery after-hours or slow-answered call at "
              "{{Company}} is a job that went to the next AC company in the Google results. I built an "
              "instant call/text responder that answers, qualifies, and books — plus reminders that kill "
              "no-shows. Built it for my own operation first.\n\nAnd unlike ServiceTitan or Housecall Pro: "
              "no licensing fee, unlimited users, and it ties right into the apps you already run. Where it "
              "makes sense I can rebuild those tools as your own — branded to {{Company}}, no per-seat bill "
              "— so you stop paying their monthly licenses for good.\n\nNo retainer. We pick one number — "
              "booked-call rate or no-show rate — and I'm paid only from the jobs it wins back. Nothing but "
              "software cost upfront.\n\n20 minutes to see if there's an easy number to move at "
              "{{Company}}?\n\n" + CC_SIGNATURE)},

    {"name": "Electrical / Plumbing — cold (speed-to-lead)", "trade": "Service",
     "subject": "How fast does {{Company}} call a new lead back?",
     "body": ("Hi {{First}},\n\nContractor to contractor — I'm local, born and raised here, 10+ years in "
              "construction and the trades around Palm Beach County, and I like helping small shops like "
              "{{Company}}.\n\nQuick question: when a new lead comes in after hours, how fast does someone "
              "actually call them back? Every gap there is a booked job walking to the next shop. I built a "
              "tool that answers and books leads in under a minute, plus a system that turns finished jobs "
              "into reviews. Built it for my own operation first.\n\nAnd unlike Housecall Pro, Jobber, or "
              "ServiceTitan: no licensing fee, unlimited users, and it ties right into the apps you already "
              "run. Where it makes sense I can rebuild those tools as your own — branded to {{Company}}, no "
              "per-seat bill — so you stop paying their monthly licenses for good.\n\nNo retainer — I only "
              "get paid out of the jobs and reviews it wins you. Software cost is the only thing "
              "upfront.\n\nWorth 20 minutes?\n\n" + CC_SIGNATURE)},

    {"name": "GC / Multi-trade — cold (proposals + admin)", "trade": "GC/Multi",
     "subject": "Two numbers I can move for {{Company}}",
     "body": ("Hi {{First}},\n\nContractor to contractor — I'm local, born and raised here with 10+ years "
              "in construction and the trades around Palm Beach County, and I enjoy helping small shops "
              "like {{Company}}.\n\nFor a multi-trade shop, two things quietly cost you jobs: proposals "
              "that take too long, and an office buried in admin. I built tools that fix both — a "
              "proposal/quote generator and an ops command center that reclaims admin hours. They cut "
              "~$4,000/month of office grind in my own shop before I ever sold one.\n\nAnd unlike "
              "ServiceTitan or Buildertrend: no licensing fee, unlimited users, and it ties right into the "
              "apps you already run. Where it makes sense I can rebuild those tools as your own — branded "
              "to {{Company}}, no per-seat bill — so you stop paying their monthly licenses for good.\n\nNo "
              "retainer. We pick one number, baseline it, and I'm paid only from what it measurably moves. "
              "No result, no invoice.\n\n20 minutes to find the most expensive bottleneck at "
              "{{Company}}?\n\n" + CC_SIGNATURE)},

    {"name": "HOT — they're hiring an admin/dispatcher", "trade": "Any",
     "subject": "Before you fill that office seat at {{Company}}",
     "body": ("Hi {{First}},\n\nSaw {{Company}} is hiring an office admin/dispatcher. Before you put "
              "someone on payroll for ~$50k/yr to do it by hand — one thing worth 15 minutes.\n\nI run a "
              "roofing & construction shop too. The exact work that role does — exporting and reporting, "
              "answering and booking calls, scheduling — I automated for my own company. It cut about "
              "$4,000 a month. I'll white-label the same tool as {{Company}}'s own system.\n\nAnd you only "
              "pay me out of what it actually saves you. No savings, no invoice — only the software cost.\n\n"
              "Want to see the numbers before you fill that seat?\n\n" + CC_SIGNATURE)},

    {"name": "Follow-up — no reply", "trade": "Any",
     "subject": "Following up — {{Company}}",
     "body": ("Hi {{First}},\n\nFollowing up. Simplest way to see if this is real for {{Company}}: 20 "
              "minutes, we pull your number, and I tell you straight what the upside looks like. If it's "
              "not worth either of our time, I'll say so.\n\nWorth a look?\n\n" + CC_SIGNATURE)},

    {"name": "Break-up — closing the loop", "trade": "Any",
     "subject": "Closing the loop — {{Company}}",
     "body": ("Hi {{First}},\n\nI'll stop here so I'm not a pest. If moving one number on a no-risk, "
              "only-pay-if-it-works basis ever climbs your list, the door's open.\n\n— Danny\n\n" + CC_SIGNATURE)},

    {"name": "Blank — write your own", "trade": "Any",
     "subject": "",
     "body": "Hi {{First}},\n\n\n\n" + CC_SIGNATURE},
]


# --------------------------------------------------------------------------
# Session cookie crypto
# --------------------------------------------------------------------------
def _fernet():
    secret = os.environ.get("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET not configured")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def read_session():
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        return json.loads(_fernet().decrypt(raw.encode()))
    except (InvalidToken, ValueError, RuntimeError):
        return None


def write_session(resp, payload):
    token = _fernet().encrypt(json.dumps(payload).encode()).decode()
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, secure=True,
                    samesite="Lax", max_age=60 * 60 * 8, path="/", domain=_cookie_domain())


def set_temp(resp, name, value, max_age=600):
    token = _fernet().encrypt(json.dumps(value).encode()).decode()
    resp.set_cookie(name, token, httponly=True, secure=True, samesite="Lax",
                    max_age=max_age, path="/", domain=_cookie_domain())


def read_temp(name):
    raw = request.cookies.get(name)
    if not raw:
        return None
    try:
        return json.loads(_fernet().decrypt(raw.encode()))
    except (InvalidToken, ValueError, RuntimeError):
        return None


def clear_cookie(resp, name):
    resp.set_cookie(name, "", expires=0, path="/", domain=_cookie_domain())


def base_url():
    host = request.headers.get("x-forwarded-host", request.host)
    proto = request.headers.get("x-forwarded-proto", "https")
    return "{}://{}".format(proto, host)


ROOT_DOMAIN = "collaborativeconceptsfl.com"


def _cookie_domain():
    """Scope cookies to the parent domain so a session created on the
    wwslgc subdomain callback is also readable on the apex (and vice-versa).
    Falls back to host-only on preview (*.vercel.app)."""
    host = (request.headers.get("x-forwarded-host", request.host) or "").split(":")[0]
    return "." + ROOT_DOMAIN if host == ROOT_DOMAIN or host.endswith("." + ROOT_DOMAIN) else None


def _safe_next(default_path="/wwslgc"):
    """Absolute return URL on the host the user started from (e.g. the apex),
    so after the subdomain callback we can send them back where they began."""
    nxt = request.args.get("next") or default_path
    if not (nxt.startswith("/") and not nxt.startswith("//")):
        nxt = default_path
    return base_url() + nxt


def _safe_path(url, default="/wwslgc"):
    """Validate a stored return URL is same-site before redirecting to it."""
    from urllib.parse import urlparse
    try:
        host = (urlparse(url).hostname or "") if url else ""
        if url and url.startswith("https://") and (host == ROOT_DOMAIN or host.endswith("." + ROOT_DOMAIN)):
            return url
    except Exception:
        pass
    return default


# --------------------------------------------------------------------------
# Microsoft (MSAL)
# --------------------------------------------------------------------------
def msal_app():
    return msal.ConfidentialClientApplication(
        os.environ["MS_CLIENT_ID"],
        authority="https://login.microsoftonline.com/" + os.environ["MS_TENANT_ID"],
        client_credential=os.environ["MS_CLIENT_SECRET"],
    )


def ms_redirect_uri():
    return (os.environ.get("WWSLGC_REDIRECT_URI") or "").strip() or (base_url() + "/api/auth/callback")


def google_redirect_uri():
    return (os.environ.get("GOOGLE_REDIRECT_URI") or "").strip() or (base_url() + "/api/auth/google/callback")


# --------------------------------------------------------------------------
# Routes — identity
# --------------------------------------------------------------------------
@app.get("/api/me")
def me():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"authenticated": False,
                        "providers": {"microsoft": bool(os.environ.get("MS_CLIENT_ID")),
                                      "google": bool(os.environ.get("GOOGLE_CLIENT_ID"))}})
    return jsonify({"authenticated": True, "provider": s.get("provider"),
                    "email": s.get("email"), "name": s.get("name")})


@app.get("/api/templates")
def templates():
    return jsonify({"templates": TEMPLATES, "signature": SIGNATURE})


# ---- shared contact list (Upstash/Vercel KV) ----
CONTACTS_KEY = "wwslgc:contacts"


def _kv():
    base = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return base, token


def _kv_cmd(cmd):
    base, token = _kv()
    if not base or not token:
        return None, False  # store not configured
    r = requests.post(base, headers={"Authorization": "Bearer " + token}, json=cmd, timeout=15)
    r.raise_for_status()
    return r.json().get("result"), True


@app.get("/api/contacts")
def get_contacts():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"error": "not connected", "leads": []}), 401
    try:
        val, configured = _kv_cmd(["GET", CONTACTS_KEY])
        if not configured:
            return jsonify({"configured": False, "leads": []})
        leads = json.loads(val) if val else []
        return jsonify({"configured": True, "leads": leads})
    except Exception as e:
        return jsonify({"configured": True, "leads": [], "status": str(e)}), 200


@app.post("/api/contacts")
def set_contacts():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"error": "not connected"}), 401
    body = request.get_json(force=True, silent=True) or {}
    leads = body.get("leads", [])
    try:
        _, configured = _kv_cmd(["SET", CONTACTS_KEY, json.dumps(leads)])
        return jsonify({"ok": configured, "configured": configured, "count": len(leads)})
    except Exception as e:
        return jsonify({"ok": False, "status": str(e)}), 502


@app.get("/api/trades/templates")
def trades_templates():
    return jsonify({"templates": TRADES_TEMPLATES, "signature": CC_SIGNATURE})


# ---- trades prospect pipeline (Upstash/Vercel KV) ----
PROSPECTS_KEY = "outcomeai:prospects"


@app.get("/api/prospects")
def get_prospects():
    """Return the saved pipeline. KV-backed; degrades to unconfigured so the
    dashboard can seed itself from /data/prospects.json in the browser."""
    try:
        val, configured = _kv_cmd(["GET", PROSPECTS_KEY])
        if not configured:
            return jsonify({"configured": False, "prospects": []})
        prospects = json.loads(val) if val else []
        return jsonify({"configured": True, "prospects": prospects})
    except Exception as e:
        return jsonify({"configured": True, "prospects": [], "status": str(e)}), 200


@app.post("/api/prospects")
def set_prospects():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"error": "not connected"}), 401
    body = request.get_json(force=True, silent=True) or {}
    prospects = body.get("prospects", [])
    try:
        _, configured = _kv_cmd(["SET", PROSPECTS_KEY, json.dumps(prospects)])
        return jsonify({"ok": configured, "configured": configured, "count": len(prospects)})
    except Exception as e:
        return jsonify({"ok": False, "status": str(e)}), 502


# ---- lead discovery via Google Places (Text Search, New) + fit scoring ----
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
TRADE_QUERY = {
    "Roofing": "roofing contractor",
    "AC/HVAC": "air conditioning and heating contractor",
    "Electrical": "electrician electrical contractor",
    "Plumbing": "plumber plumbing contractor",
    "GC/Multi": "general contractor",
}
_NATIONAL = ["roto-rooter", " ars ", "aire serv", "mister sparky", "benjamin franklin",
             "one hour", "horizon services", "service experts", "home depot", "lowe's",
             "sears", "direct energy", "goettl", "rooter"]


def _places_key():
    return os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")


def _parse_city(addr):
    parts = [p.strip() for p in (addr or "").split(",")]
    return parts[-3] if len(parts) >= 3 else (parts[0] if parts else "")


def _score_lead(p, min_r, max_r, min_rating):
    """In-depth fit filter for our ICP: right-size, owner-operated PBC trade shop."""
    reviews = p.get("userRatingCount") or 0
    rating = p.get("rating") or 0
    name = (p.get("displayName") or {}).get("text", "")
    site = p.get("websiteUri")
    phone = p.get("nationalPhoneNumber")
    status = p.get("businessStatus")
    score, good, flags = 0, [], []
    if reviews == 0:
        flags.append("no reviews")
    elif reviews < 8:
        score += 5; flags.append("few reviews (small/new)")
    elif reviews <= max_r:
        score += 40; good.append("%d reviews (right-size)" % reviews)
    else:
        score += 8; flags.append("%d reviews (maybe too big)" % reviews)
    if min_r <= reviews <= max_r:
        score += 8
    if rating >= 4.5:
        score += 22; good.append("%s stars" % rating)
    elif rating >= min_rating:
        score += 12; good.append("%s stars" % rating)
    elif rating > 0:
        flags.append("%s stars (weak)" % rating)
    if site:
        score += 20; good.append("website")
    else:
        flags.append("no website")
    if phone:
        score += 10; good.append("phone")
    else:
        flags.append("no phone")
    if status and status != "OPERATIONAL":
        score -= 15; flags.append(status.lower())
    if any(n in (" " + name.lower() + " ") for n in _NATIONAL):
        score -= 30; flags.append("national/franchise")
    score = max(0, min(100, score))
    verdict = "strong" if score >= 70 else ("ok" if score >= 45 else "weak")
    return score, verdict, good, flags


@app.post("/api/leads/search")
def leads_search():
    key = _places_key()
    if not key:
        return jsonify({"configured": False, "candidates": [],
                        "hint": "Set GOOGLE_PLACES_API_KEY in Vercel (enable Places API New)."})
    body = request.get_json(force=True, silent=True) or {}
    trade = body.get("trade", "Roofing")
    near = body.get("near") or "West Palm Beach, FL"
    min_r = int(body.get("min_reviews", 12))
    max_r = int(body.get("max_reviews", 400))
    min_rating = float(body.get("min_rating", 4.0))
    q = "{} in {}".format(TRADE_QUERY.get(trade, trade), near)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": ("places.id,places.displayName,places.formattedAddress,"
                             "places.nationalPhoneNumber,places.websiteUri,places.rating,"
                             "places.userRatingCount,places.businessStatus,places.primaryType"),
    }
    payload = {"textQuery": q, "maxResultCount": 20, "regionCode": "US"}
    try:
        r = requests.post(PLACES_URL, headers=headers, json=payload, timeout=25)
        if r.status_code != 200:
            return jsonify({"configured": True, "candidates": [], "status": _err(r)}), 200
        places = r.json().get("places", [])
    except requests.RequestException as e:
        return jsonify({"configured": True, "candidates": [], "status": str(e)}), 200
    out = []
    for p in places:
        score, verdict, good, flags = _score_lead(p, min_r, max_r, min_rating)
        site = p.get("websiteUri", "") or ""
        out.append({
            "place_id": p.get("id", ""),
            "company": (p.get("displayName") or {}).get("text", ""),
            "trade": trade,
            "city": _parse_city(p.get("formattedAddress", "")),
            "phone": p.get("nationalPhoneNumber", ""),
            "website": site.replace("https://", "").replace("http://", "").rstrip("/"),
            "rating": p.get("rating", 0),
            "reviews": p.get("userRatingCount", 0),
            "score": score, "verdict": verdict, "good": good, "flags": flags,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"configured": True, "query": q, "count": len(out), "candidates": out})


# ==========================================================================
# WWS lead funnel + lightweight CRM  (KV-backed; degrades gracefully)
# ==========================================================================
import time

WWS_LEADS_KEY = "wws:leads"              # Redis LIST; each item = JSON lead (immutable submission)
WWS_LEAD_META_KEY = "wws:lead_meta"      # JSON map { id: {status, notes:[...], updated} }
WWS_REQ_KEY = "wws:inspection_requests"  # Redis LIST; customer inspection requests
WWS_STAGES = ["new", "contacted", "assessed", "proposal", "won", "lost"]
WWS_ADMIN_EMAILS = set(
    e.strip().lower() for e in os.environ.get(
        "WWS_ADMIN_EMAILS", "dannybivins83@gmail.com,danny@lagalacon.com"
    ).split(",") if e.strip()
)
WWS_NOTIFY_EMAIL = os.environ.get("WWS_NOTIFY_EMAIL", "dannybivins83@gmail.com")


def _now_ms():
    return int(time.time() * 1000)


def _gen_id():
    return format(_now_ms(), "x") + secrets.token_hex(2)


def _is_admin():
    s = read_session()
    if not s: return False
    if s.get("pin_admin"): return True
    return s.get("email", "").lower() in WWS_ADMIN_EMAILS


def _notify(subject, text):
    """Best-effort email notification. Prefers Resend (transactional, already
    provisioned on this project) and falls back to FormSubmit AJAX. Never raises
    — lead capture must not depend on the email going through."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("RESEND_FROM_EMAIL", "")
    if api_key and sender:
        try:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                json={"from": sender, "to": [WWS_NOTIFY_EMAIL], "subject": subject, "text": text},
                timeout=10,
            )
            if r.status_code < 300:
                return
        except Exception:
            pass
    try:
        requests.post(
            "https://formsubmit.co/ajax/" + WWS_NOTIFY_EMAIL,
            json={"_subject": subject, "_template": "table", "message": text},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=8,
        )
    except Exception:
        pass


PORTAL_URL = os.environ.get("PORTAL_URL", "https://wwslgc.collaborativeconceptsfl.com/portal")


def _notify_client(to_email, subject, headline, body_line, cta_label="Open your portal", cta_url=None):
    """Best-effort, on-brand client email via Resend. Self-contained (reads env
    vars directly rather than relying on helpers defined later in the module).
    Never raises — a failed notification must never break the underlying action."""
    try:
        to_email = (to_email or "").strip()
        if not to_email:
            return False
        api_key = os.environ.get("RESEND_API_KEY", "")
        sender = os.environ.get("RESEND_FROM_EMAIL", "") or "updates@collaborativeconceptsfl.com"
        if not api_key:
            return False
        url = cta_url or PORTAL_URL
        html = (
            "<div style='font-family:Arial,sans-serif;max-width:560px;margin:0 auto'>"
            "<div style='background:#13233f;padding:22px 28px'>"
            "<h1 style='color:#fff;font-size:18px;margin:0'>LA GALA CONSTRUCTION</h1>"
            "<p style='color:#c9a227;font-size:11px;margin:4px 0 0;letter-spacing:1px;text-transform:uppercase'>WWS Compliance · Client Portal</p>"
            "</div>"
            "<div style='padding:26px 28px;color:#1f2733;font-size:14px;line-height:1.6;background:#fff'>"
            "<p style='margin:0 0 12px;font-size:17px;font-weight:700;color:#13233f'>{headline}</p>"
            "<p style='margin:0 0 20px'>{body}</p>"
            "<p><a href='{url}' style='background:#c9a227;color:#13233f;text-decoration:none;padding:12px 22px;border-radius:8px;display:inline-block;font-weight:700'>{cta}</a></p>"
            "<p style='font-size:12px;color:#5b6573;margin-top:26px'>Questions? Call (561) 475-8615.</p>"
            "<p style='margin:20px 0 4px'>— La Gala Construction</p>"
            "<p style='margin:0;color:#5b6573;font-size:12px'>CGC059211 · Licensed &amp; Insured</p>"
            "</div></div>"
        ).format(headline=headline, body=body_line, url=url, cta=cta_label)
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json={"from": sender, "to": [to_email], "subject": subject, "html": html},
            timeout=10,
        )
        return r.status_code < 300
    except Exception:
        return False


def _lead_summary(d):
    lines = []
    for k in ("name", "email", "phone", "company", "property", "message"):
        if d.get(k):
            lines.append("{}: {}".format(k.capitalize(), d[k]))
    for k, v in (d.get("fields") or {}).items():
        if k not in ("Name", "Email", "Phone", "Company", "Property Location", "Message") and v:
            lines.append("{}: {}".format(k, v))
    if d.get("source"):
        lines.append("Source: {}".format(d["source"]))
    return "\n".join(lines)


@app.post("/api/lead")
def create_lead():
    """Public — the WWS Free Assessment form posts here. Stores the lead in KV
    and emails a notification. Accepts JSON (fetch) or form-encoded (no-JS)."""
    _allowed, _retry = _rate_limit("lead:ip:" + _client_ip(), 20, 3600)
    if not _allowed:
        return _rate_limited_response(_retry)
    if request.is_json:
        body = request.get_json(force=True, silent=True) or {}
    else:
        body = {"fields": request.form.to_dict()}
    fields = body.get("fields") or {}
    # honeypot — silently accept & drop bots
    if (fields.get("_honey") or fields.get("_gotcha") or "").strip():
        return jsonify({"ok": True}), 200

    def g(*names):
        for n in names:
            for src in (body, fields):
                v = src.get(n)
                if v:
                    return str(v).strip()
        return ""

    name = g("name", "Name")[:200]
    email = g("email", "Email")[:200]
    phone = g("phone", "Phone")[:60]
    company = g("company", "Company")[:200]
    prop = g("property", "Property Location", "address")[:300]
    message = g("message", "Message")[:5000]
    if not (email or phone):
        return jsonify({"ok": False, "error": "email or phone required"}), 400

    clean = {}
    for k, v in fields.items():
        if len(clean) >= 40:
            break
        if k and not k.startswith("_") and str(v).strip():
            clean[k[:60]] = str(v)[:2000]
    ref_code = g("ref", "ref_code")[:40]
    lead = {
        "id": _gen_id(), "ts": _now_ms(), "name": name, "email": email, "phone": phone,
        "company": company, "property": prop, "message": message, "fields": clean,
        "source": (g("source") or request.headers.get("Referer", ""))[:300],
        "ua": request.headers.get("User-Agent", "")[:300],
        "ref_code": ref_code,
    }
    try:
        _, configured = _kv_cmd(["RPUSH", WWS_LEADS_KEY, json.dumps(lead)])
    except Exception:
        configured = False
    if ref_code:
        try:
            referrer_email = _ref_email_for_code(ref_code)
            if referrer_email:
                _ref_credit_add_referral(referrer_email, lead["id"])
        except Exception:
            pass
    _notify("New WWS lead — " + (name or company or email or phone),
            "New Free Assessment request from the WWS site:\n\n" + _lead_summary(lead))

    if request.is_json:
        return jsonify({"ok": True, "stored": bool(configured)}), 200
    return redirect("/?submitted=1#assessment")


# ---- Building compliance check (public lead magnet) ----
# Server-side match of a visitor's building against the harvested enforcement
# dataset (public-records-derived). The dataset stays server-side so the full
# target list is never shipped to the browser; only the matched rows are returned.
_ENFORCEMENT_CACHE = None
_ADDR_STOP = {"fl", "florida", "usa", "ste", "suite", "unit", "apt", "bldg", "building",
              "ave", "avenue", "st", "street", "dr", "drive", "rd", "road", "blvd",
              "boulevard", "ln", "lane", "ct", "court", "cir", "circle", "way", "pl",
              "place", "ter", "terrace", "hwy", "highway", "n", "s", "e", "w", "ne",
              "nw", "se", "sw", "the", "of", "and", "at"}
_GEO_STOP = {"hollywood", "miami", "beach", "dade", "broward", "palm", "lauderdale",
             "aventura", "boca", "boynton", "doral", "unincorporated", "kendall",
             "kendale", "fisher", "island"}
_NAME_STOP = _ADDR_STOP | _GEO_STOP | {"condominium", "condominiums", "condo", "condos",
                           "association", "associations", "assn", "inc", "llc", "hoa",
                           "co", "company", "apartments", "apartment", "complex", "tower",
                           "towers", "resort", "villas", "villa", "house", "homes", "club"}


def _cc_norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def _cc_num(s):
    m = re.match(r"\s*(\d+)", s or "")
    return m.group(1) if m else ""


_CC_DIRS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}


def _cc_street(s):
    return (s or "").split(",")[0]


def _cc_core(s):
    toks = [t for t in _cc_norm(_cc_street(s)).split() if not t.isdigit() and len(t) >= 3]
    return set(t for t in toks if t not in _ADDR_STOP)


def _cc_snums(s):
    # street-number tokens (e.g. the "68" in "SW 68 CT") — the leading house number dropped
    toks = _cc_norm(_cc_street(s)).split()
    if toks and toks[0].isdigit():
        toks = toks[1:]
    return set(t for t in toks if t.isdigit())


def _cc_sdir(s):
    return set(t for t in _cc_norm(_cc_street(s)).split() if t in _CC_DIRS)


def _cc_name_tokens(s):
    return set(t for t in _cc_norm(s).split() if len(t) >= 3 and t not in _NAME_STOP)


def _load_enforcement():
    global _ENFORCEMENT_CACHE
    if _ENFORCEMENT_CACHE is not None:
        return _ENFORCEMENT_CACHE
    data = []
    for cand in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "wws_enforcement.json"),
        os.path.join(os.getcwd(), "api", "wws_enforcement.json"),
        os.path.join(os.getcwd(), "wws_enforcement.json"),
    ):
        try:
            with open(cand, "r", encoding="utf-8") as f:
                data = json.load(f)
            break
        except Exception:
            continue
    for rec in data:
        rec["_num"] = _cc_num(rec.get("address", ""))
        rec["_core"] = _cc_core(rec.get("address", ""))
        rec["_sn"] = _cc_snums(rec.get("address", ""))
        rec["_dir"] = _cc_sdir(rec.get("address", ""))
        # building-identity tokens come from the association name + any parenthetical
        # building name — NOT the street address (street/geo tokens are too common and
        # would cross-match neighboring cited buildings).
        paren = re.search(r"\(([^)]*)\)", rec.get("building", "") or "")
        name_src = (rec.get("assoc", "") or "") + " " + (paren.group(1) if paren else "")
        rec["_nametok"] = _cc_name_tokens(name_src)
    _ENFORCEMENT_CACHE = data
    return data


def _match_enforcement(query):
    data = _load_enforcement()
    qnum = _cc_num(query)
    qcore = _cc_core(query)
    qsn = _cc_snums(query)
    qdir = _cc_sdir(query)
    qname = _cc_name_tokens(query)
    addr_hits = []
    name_hits = []
    for rec in data:
        # strong address match: same house number AND either a shared distinctive street-name
        # token (named streets) OR a shared street-number with matching direction (numbered
        # grid streets like "SW 68 CT", common in Miami-Dade)
        if qnum and rec["_num"] and qnum == rec["_num"] and (
            (qcore & rec["_core"])
            or ((qsn & rec["_sn"]) and (not qdir or not rec["_dir"] or (qdir & rec["_dir"])))
        ):
            addr_hits.append(rec)
            continue
        # building / association name match: 2+ shared distinctive tokens, or one long one
        overlap = qname & rec["_nametok"]
        if len(overlap) >= 2 or any(len(t) >= 7 for t in overlap):
            name_hits.append(rec)
    # an exact address hit wins outright — never dilute it with fuzzy name matches
    hits = addr_hits if addr_hits else name_hits
    return hits[:6]


def _program_label(src):
    s = (src or "").lower()
    if "hollywood" in s:
        return "City of Hollywood Building Safety Inspection Program (BSIP)"
    if "usb" in s or "unsafe" in s:
        return "Miami-Dade Unsafe Structures Board"
    return src or "a county/city enforcement list"


# ---- WWS compliance analyzer (runs when an address is NOT on our enforcement lists) ----
# Deterministic, no external calls: infers county + coastal exposure from the address, then
# maps to the Florida laws that apply on an age schedule (milestone inspection, recertification)
# plus OSHA anchor certification. Turns a dead "not found" into a real, honest determination.
WWS_RESEARCH_KEY = "wws:research_queue"
WWS_RESEARCH_MAX = 3000

_WWS_COUNTY_BY_CITY = {
    # Miami-Dade
    "miami": "Miami-Dade", "miami beach": "Miami-Dade", "north miami": "Miami-Dade",
    "north miami beach": "Miami-Dade", "sunny isles": "Miami-Dade", "sunny isles beach": "Miami-Dade",
    "aventura": "Miami-Dade", "bal harbour": "Miami-Dade", "surfside": "Miami-Dade",
    "bay harbor islands": "Miami-Dade", "key biscayne": "Miami-Dade", "coral gables": "Miami-Dade",
    "doral": "Miami-Dade", "hialeah": "Miami-Dade", "homestead": "Miami-Dade", "kendall": "Miami-Dade",
    "cutler bay": "Miami-Dade", "fisher island": "Miami-Dade", "golden beach": "Miami-Dade",
    "sweetwater": "Miami-Dade", "pinecrest": "Miami-Dade", "palmetto bay": "Miami-Dade",
    # Broward
    "fort lauderdale": "Broward", "ft lauderdale": "Broward", "hollywood": "Broward",
    "hallandale": "Broward", "hallandale beach": "Broward", "pompano beach": "Broward",
    "deerfield beach": "Broward", "dania beach": "Broward", "lauderdale-by-the-sea": "Broward",
    "lauderdale by the sea": "Broward", "pembroke pines": "Broward", "davie": "Broward",
    "sunrise": "Broward", "plantation": "Broward", "coral springs": "Broward", "weston": "Broward",
    "miramar": "Broward", "tamarac": "Broward", "margate": "Broward", "coconut creek": "Broward",
    # Palm Beach
    "west palm beach": "Palm Beach", "palm beach": "Palm Beach", "boca raton": "Palm Beach",
    "boynton beach": "Palm Beach", "delray beach": "Palm Beach", "highland beach": "Palm Beach",
    "riviera beach": "Palm Beach", "singer island": "Palm Beach", "jupiter": "Palm Beach",
    "lake worth": "Palm Beach", "lake worth beach": "Palm Beach", "lantana": "Palm Beach",
    "manalapan": "Palm Beach", "juno beach": "Palm Beach", "palm beach gardens": "Palm Beach",
    "wellington": "Palm Beach", "greenacres": "Palm Beach", "royal palm beach": "Palm Beach",
}

_WWS_COASTAL_CITIES = {
    "miami beach", "sunny isles", "sunny isles beach", "bal harbour", "surfside",
    "bay harbor islands", "key biscayne", "fisher island", "golden beach", "hollywood",
    "hallandale", "hallandale beach", "fort lauderdale", "pompano beach", "deerfield beach",
    "dania beach", "lauderdale-by-the-sea", "lauderdale by the sea", "highland beach",
    "boca raton", "delray beach", "boynton beach", "palm beach", "singer island",
    "riviera beach", "juno beach", "jupiter", "manalapan", "lantana", "north miami beach",
}
_WWS_COASTAL_KEYWORDS = (
    "oceanfront", "s ocean", "n ocean", " ocean blvd", " ocean dr", "ocean drive",
    "collins ave", "collins avenue", "a1a", "surf rd", "surf road", "atlantic ave",
    "atlantic blvd", "fisher island", "intracoastal", "bayshore", "harbour", "seaway",
    "beachfront", "on the beach",
)


_WWS_CITIES_BY_LEN = sorted(_WWS_COUNTY_BY_CITY.keys(), key=len, reverse=True)


def _wws_detect_county(text):
    t = " " + (text or "").lower() + " "
    for city in _WWS_CITIES_BY_LEN:  # longest name first so "miami beach" beats "miami"
        if (" " + city + " ") in t or (" " + city + ",") in t:
            return _WWS_COUNTY_BY_CITY[city], city
    m = re.search(r"\b(3\d{4})\b", t)
    if m:
        p = m.group(1)[:3]
        if p in ("330", "331", "332"):
            return "Miami-Dade", ""
        if p == "333":
            return "Broward", ""
        if p == "334":
            return "Palm Beach", ""
    return "", ""


def _wws_is_coastal(text, city):
    if city in _WWS_COASTAL_CITIES:
        return True
    t = (text or "").lower()
    return any(k in t for k in _WWS_COASTAL_KEYWORDS)


def _wws_analyze(query, building):
    text = ((query or "") + " " + (building or "")).strip()
    county, city = _wws_detect_county(text)
    coastal = _wws_is_coastal(text, city)
    place = ((city.title() + ", ") if city else "") + (county + " County" if county else "South Florida")
    programs = []
    yr = 25 if coastal else 30
    programs.append({
        "name": "Florida Milestone Structural Inspection (§ 553.899)",
        "detail": ("Condominium & co-op buildings 3+ habitable stories must complete a milestone structural "
                   "inspection at %d years of age%s, then re-inspect every 10 years. Most South Florida coastal "
                   "towers are already past this threshold." % (yr, " (within ~3 miles of the coast)" if coastal else "")),
    })
    if county in ("Miami-Dade", "Broward"):
        programs.append({
            "name": "%s Building Recertification (40-year / 10-year)" % county,
            "detail": ("%s requires a structural & electrical recertification once a building reaches 40 years "
                       "(some cities 30), then every 10 years after. Missing it is what puts a building on the "
                       "unsafe-structures enforcement track." % county),
        })
    elif county == "Palm Beach":
        programs.append({
            "name": "Palm Beach County / municipal building-safety recertification",
            "detail": ("Palm Beach County and its coastal municipalities run building-safety inspection and "
                       "recertification programs for aging multi-story buildings, backed by unsafe-structures enforcement."),
        })
    programs.append({
        "name": "OSHA 1910 Subpart D — roof anchors & walking-working surfaces",
        "detail": ("Any building where workers access the roof — window washing, HVAC, facade work, inspections "
                   "— must have its anchors, tiebacks and davits inspected annually and PE load-test certified "
                   "(ANSI/IWCA I-14.1, ASME A120.1). This is separate from code enforcement and applies even when a "
                   "building is on no violation list."),
    })
    if coastal:
        headline = "Your building is almost certainly on the hook — it just hasn't been cited yet."
        summary = ("%s is an oceanfront / coastal corridor — buildings here are overwhelmingly 3+ story towers. "
                   "That puts them under Florida's 25-year coastal milestone inspection and the recertification cycle, "
                   "and an oceanfront tower almost always has roof anchors or davits for window washing that need annual "
                   "inspection and PE-stamped load-test certification." % place)
    elif county:
        headline = "Not cited today — but here's what still applies to your building."
        summary = ("Based on the address, your building sits in %s. If it's a 3+ story condo or co-op, Florida's "
                   "milestone inspection and the county recertification program apply on an age schedule, and any roof "
                   "access triggers OSHA anchor-certification requirements." % place)
    else:
        headline = "Not on our current lists — send a bit more and we'll research it."
        summary = ("We couldn't pin your county from what you entered. Florida's milestone inspection (3+ story condos) "
                   "and OSHA roof-anchor certification still very likely apply. Add the city or ZIP and we'll pull the exact records.")
    return {
        "county": county, "city": city.title() if city else "", "coastal": coastal, "place": place,
        "headline": headline, "summary": summary, "likely_anchor": bool(coastal), "programs": programs,
    }


def _wws_analysis_text(a):
    """Format the analyzer result as a plain-text compliance brief for the notify email."""
    if not a:
        return ""
    lines = ["-- INSTANT COMPLIANCE ANALYSIS (auto) --",
             "Location: " + (a.get("place") or "South Florida")
             + ("  |  COASTAL" if a.get("coastal") else ""),
             "",
             a.get("headline") or "",
             a.get("summary") or "",
             "",
             "What applies to a building like this:"]
    for p in (a.get("programs") or []):
        lines.append("  - " + (p.get("name") or "") + ": " + (p.get("detail") or ""))
    lines.append("")
    lines.append("POTENTIAL OSHA EXPOSURE (roof access, no anchor certification of record):")
    lines.append("  Standards in play: 29 CFR 1910.27(b) (rope-descent anchorages must be inspected + "
                 "PE load-test certified >= every 10 yrs, in writing, BEFORE use), 1910.28 (roof edge/hole "
                 "fall protection), 1910.140 (personal fall arrest), 1910.22 (surface condition).")
    lines.append("  Liability: under OSHA's multi-employer / controlling-employer doctrine the ASSOCIATION "
                 "can be cited for a contractor's worker on the roof.")
    lines.append("  2025-26 penalty scale: ~$16,550 per serious violation; up to ~$165,514 per "
                 "willful/repeat violation. Exposure exists the moment a worker steps onto the roof.")
    lines.append("")
    lines.append("A deeper per-building snapshot (year built, association, permit audit for roof/painting/"
                 "restoration work, current OSHA/DOL records, sources) follows automatically from the research runner.")
    return "\n".join(lines)


@app.post("/api/wws/check")
def wws_building_check():
    allowed, retry = _rate_limit("check:ip:" + _client_ip(), 40, 3600)
    if not allowed:
        return _rate_limited_response(retry)
    body = request.get_json(force=True, silent=True) or {}
    if (body.get("_honey") or body.get("_gotcha") or "").strip():
        return jsonify({"ok": True, "status": "clear", "matches": []}), 200
    query = (body.get("query") or body.get("address") or "").strip()[:300]
    building = (body.get("building") or body.get("company") or "").strip()[:200]
    email = (body.get("email") or "").strip()[:200]
    name = (body.get("name") or "").strip()[:200]
    phone = (body.get("phone") or "").strip()[:60]
    role = (body.get("role") or "").strip()[:80]
    if not query and not building:
        return jsonify({"ok": False, "error": "Please enter your building address."}), 400
    hits = _match_enforcement((query + " " + building).strip())
    status = "flagged" if hits else "not_listed"
    matches = [{"building": h.get("building", ""), "address": h.get("address", ""),
                "city": h.get("city", ""), "county": h.get("county", ""),
                "program": _program_label(h.get("source", "")), "why": h.get("why", "")}
               for h in hits]
    # When not on our lists, run the compliance analyzer so the visitor gets a real answer
    analysis = None if hits else _wws_analyze(query, building)
    stored = False
    queued = False
    if email or phone:
        if hits:
            summary = ("FLAGGED — matched %d enforcement record(s): " % len(hits)
                       + "; ".join((m["building"] or m["address"]) for m in matches))
        else:
            a = analysis or {}
            summary = ("NEEDS RESEARCH — not on our enforcement lists. Analyzer: %s%s. %s"
                       % (a.get("place", "South Florida"),
                          " (coastal)" if a.get("coastal") else "",
                          a.get("headline", "")))
        lead = {
            "id": _gen_id(), "ts": _now_ms(), "name": name, "email": email, "phone": phone,
            "company": building, "property": query, "message": summary,
            "fields": {k: v for k, v in {
                "Building/Association": building, "Role": role, "Searched": query,
                "Check result": ("FLAGGED" if hits else "NOT LISTED — needs research"),
                "Matched": "; ".join((m["building"] or m["address"]) for m in matches),
                "County (inferred)": (analysis or {}).get("county", ""),
                "Coastal": ("yes" if (analysis or {}).get("coastal") else "") if analysis else "",
            }.items() if v},
            "source": "Building Compliance Check",
            "ua": request.headers.get("User-Agent", "")[:300],
            "ref_code": (body.get("ref") or "")[:40],
        }
        try:
            _, configured = _kv_cmd(["RPUSH", WWS_LEADS_KEY, json.dumps(lead)])
            stored = bool(configured)
        except Exception:
            stored = False
        # queue non-matches for a deeper per-building records pull (year built, actual violations, etc.)
        if not hits:
            try:
                job = {"id": _gen_id(), "ts": _now_ms(), "status": "pending",
                       "query": query, "building": building, "name": name,
                       "email": email, "phone": phone,
                       "county": (analysis or {}).get("county", ""),
                       "coastal": bool((analysis or {}).get("coastal")),
                       "lead_id": lead["id"]}
                _, cfg2 = _kv_cmd(["RPUSH", WWS_RESEARCH_KEY, json.dumps(job)])
                _kv_cmd(["LTRIM", WWS_RESEARCH_KEY, -WWS_RESEARCH_MAX, -1])
                queued = bool(cfg2)
            except Exception:
                queued = False
        try:
            body_txt = "A building compliance check was submitted on the WWS site:\n\n" + _lead_summary(lead)
            if not hits and analysis:
                body_txt += "\n\n" + _wws_analysis_text(analysis)
            _notify("WWS building check — " + status.upper() + " — " + (name or email or phone or query),
                    body_txt)
        except Exception:
            pass
    resp = {"ok": True, "status": status, "count": len(matches),
            "matches": matches, "stored": stored}
    if analysis is not None:
        resp["analysis"] = analysis
        resp["researching"] = queued
    return jsonify(resp), 200


# ---- WWS research queue (buildings checked that weren't on our lists) ----
WWS_RESEARCH_DONE_KEY = "wws:research_done"   # SET of resolved job ids


@app.get("/api/admin/research")
def admin_research_list():
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    only_pending = (request.args.get("pending") or "").strip() in ("1", "true", "yes")
    raw, _cfg = _kv_cmd(["LRANGE", WWS_RESEARCH_KEY, 0, 499])
    raw = raw or []
    done_raw, _dcfg = _kv_cmd(["SMEMBERS", WWS_RESEARCH_DONE_KEY])
    done = set(done_raw or [])
    items = []
    for r in raw:
        try:
            j = json.loads(r)
        except Exception:
            continue
        j["status"] = "done" if j.get("id") in done else (j.get("status") or "pending")
        items.append(j)
    items.reverse()  # newest first
    pending = [i for i in items if i["status"] == "pending"]
    out = pending if only_pending else items
    return jsonify({"ok": True, "items": out, "count": len(items), "pending": len(pending)})


@app.post("/api/admin/research/resolve")
def admin_research_resolve():
    """Runner posts a completed research snapshot here: emails it to the WWS notify
    address (Danny) and marks the queue job done. 'notify me only' delivery."""
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    body = request.get_json(force=True, silent=True) or {}
    jid = (body.get("id") or "").strip()
    if not jid:
        return jsonify({"ok": False, "error": "id required"}), 400
    snapshot = (body.get("snapshot") or "").strip()
    building = (body.get("building") or body.get("address") or "").strip()
    try:
        _kv_cmd(["SADD", WWS_RESEARCH_DONE_KEY, jid])
    except Exception:
        pass
    notified = False
    if snapshot:
        try:
            _notify("WWS research snapshot — " + (building or jid)[:80],
                    "A /check building was researched (it was NOT on our enforcement lists):\n\n"
                    + snapshot + "\n\n— auto-research runner")
            notified = True
        except Exception:
            notified = False
    _log_activity("research_resolved", (building or jid)[:120], name="research-runner")
    return jsonify({"ok": True, "resolved": jid, "notified": notified})


# ---- admin activity log ----
WWS_ACTIVITY_KEY = "wws:admin_activity"
WWS_ACTIVITY_MAX = 1000


def _admin_name():
    s = read_session() or {}
    return (s.get("admin_name") or s.get("name") or s.get("email") or "unknown").split("@")[0]


def _log_activity(action, detail="", name=None):
    try:
        entry = json.dumps({
            "ts": _now_ms(),
            "name": name or _admin_name(),
            "action": action,
            "detail": (detail or "")[:300],
            "ip": ((request.headers.get("x-forwarded-for") or "") + " " + (request.remote_addr or "")).strip()[:80],
        })
        _kv_cmd(["LPUSH", WWS_ACTIVITY_KEY, entry])
        _kv_cmd(["LTRIM", WWS_ACTIVITY_KEY, 0, WWS_ACTIVITY_MAX - 1])
    except Exception:
        pass


@app.get("/api/admin/activity")
def admin_activity():
    if not _is_admin(): return jsonify({"ok": False, "error": "forbidden"}), 403
    raw, _cfg = _kv_cmd(["LRANGE", WWS_ACTIVITY_KEY, 0, 199])
    raw = raw or []
    entries = []
    for r in raw:
        try: entries.append(json.loads(r))
        except: pass
    return jsonify({"ok": True, "entries": entries})


# ---- admin (gated by WWS_ADMIN_EMAILS or shared PIN) ----
@app.get("/api/admin/session")
def admin_session():
    s = read_session() or {}
    pin_ok = bool(s.get("pin_admin"))
    email_ok = s.get("email", "").lower() in WWS_ADMIN_EMAILS
    return jsonify({
        "authed": bool(s.get("email")) or pin_ok,
        "email": s.get("email", ""),
        "name": s.get("admin_name") or s.get("name", "Team"),
        "admin": pin_ok or email_ok,
    })


@app.post("/api/admin/pin")
def admin_pin():
    expected = (os.environ.get("ADMIN_PIN") or "").strip()
    if not expected:
        return jsonify({"ok": False, "error": "PIN not configured (set ADMIN_PIN in Vercel env vars)"}), 503
    body = request.get_json(force=True, silent=True) or {}
    if (body.get("pin") or "").strip() != expected:
        _log_activity("login_fail", "Wrong access code", name="unknown")
        return jsonify({"ok": False, "error": "Wrong code"}), 401
    name = (body.get("name") or "Team").strip()[:50] or "Team"
    s = read_session() or {}
    s["pin_admin"] = True
    s["admin_name"] = name
    _log_activity("login", "Signed in via access code", name=name)
    resp = make_response(jsonify({"ok": True, "name": name}))
    write_session(resp, s)
    return resp


@app.get("/api/admin/pin/logout")
def admin_pin_logout():
    s = read_session() or {}
    s.pop("pin_admin", None)
    resp = make_response(redirect("/admin"))
    write_session(resp, s)
    return resp


def _load_leads():
    raw, configured = _kv_cmd(["LRANGE", WWS_LEADS_KEY, "0", "-1"])
    if not configured:
        return None
    leads = []
    for item in (raw or []):
        try:
            leads.append(json.loads(item))
        except Exception:
            pass
    meta_raw, _ = _kv_cmd(["GET", WWS_LEAD_META_KEY])
    try:
        meta = json.loads(meta_raw) if meta_raw else {}
    except Exception:
        meta = {}
    for l in leads:
        m = meta.get(l.get("id"), {})
        l["status"] = m.get("status", "new")
        l["notes"] = m.get("notes", [])
        l["updated"] = m.get("updated")
    leads.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return leads


def _load_requests():
    raw, configured = _kv_cmd(["LRANGE", WWS_REQ_KEY, "0", "-1"])
    if not configured:
        return []
    out = []
    for item in (raw or []):
        try:
            out.append(json.loads(item))
        except Exception:
            pass
    out.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return out


@app.get("/api/admin/leads")
def admin_leads():
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    leads = _load_leads()
    if leads is None:
        return jsonify({"configured": False, "leads": [], "requests": [], "stages": WWS_STAGES})
    return jsonify({"configured": True, "leads": leads, "requests": _load_requests(), "stages": WWS_STAGES})


@app.post("/api/admin/lead/update")
def admin_lead_update():
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    body = request.get_json(force=True, silent=True) or {}
    lid = (body.get("id") or "").strip()
    if not lid:
        return jsonify({"ok": False, "error": "id required"}), 400
    meta_raw, configured = _kv_cmd(["GET", WWS_LEAD_META_KEY])
    if not configured:
        return jsonify({"ok": False, "error": "store not configured"}), 200
    try:
        meta = json.loads(meta_raw) if meta_raw else {}
    except Exception:
        meta = {}
    m = meta.get(lid, {})
    st = body.get("status")
    if st in WWS_STAGES:
        m["status"] = st
    note = (body.get("note") or "").strip()
    if note:
        notes = m.get("notes", [])
        notes.append({"ts": _now_ms(), "text": note[:2000], "by": (read_session() or {}).get("email", "")})
        m["notes"] = notes
    m["updated"] = _now_ms()
    meta[lid] = m
    _kv_cmd(["SET", WWS_LEAD_META_KEY, json.dumps(meta)])
    _log_activity("lead_update", f"Lead {lid[:8]} → {st or 'note'}" + (f": {note[:80]}" if note else ""))
    return jsonify({"ok": True, "meta": m})


@app.post("/api/admin/lead/create")
def admin_lead_create():
    """Manually add a lead/client from the admin dashboard (phone, referral, walk-in)."""
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    b = request.get_json(force=True, silent=True) or {}
    name = (b.get("name") or "").strip()[:200]
    email = (b.get("email") or "").strip()[:200]
    phone = (b.get("phone") or "").strip()[:60]
    company = (b.get("company") or "").strip()[:200]
    prop = (b.get("property") or "").strip()[:300]
    message = (b.get("message") or "").strip()[:5000]
    if not (name or company or email or phone):
        return jsonify({"ok": False, "error": "Enter at least a name, company, phone, or email."}), 400
    lead = {
        "id": _gen_id(), "ts": _now_ms(), "name": name, "email": email, "phone": phone,
        "company": company, "property": prop, "message": message, "fields": {},
        "source": (b.get("source") or "Manual (admin)")[:120], "ua": "admin",
    }
    try:
        _, configured = _kv_cmd(["RPUSH", WWS_LEADS_KEY, json.dumps(lead)])
    except Exception:
        configured = False
    if not configured:
        return jsonify({"ok": False, "error": "store not configured"}), 200
    stage = b.get("status")
    if stage in WWS_STAGES and stage != "new":
        try:
            meta_raw, _ = _kv_cmd(["GET", WWS_LEAD_META_KEY])
            meta = json.loads(meta_raw) if meta_raw else {}
            meta[lead["id"]] = {"status": stage, "notes": [], "updated": _now_ms()}
            _kv_cmd(["SET", WWS_LEAD_META_KEY, json.dumps(meta)])
        except Exception:
            pass
    return jsonify({"ok": True, "lead": lead})


@app.post("/api/admin/leads/import")
def admin_leads_import():
    """Bulk-import prospect leads (e.g., harvested noncompliant-building lists).
    Body: {leads:[{name,company,property,phone,email,message,source}], source?}.
    De-dupes against existing leads by (property|company|email) so re-imports
    don't create duplicates. Admin-gated."""
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    b = request.get_json(force=True, silent=True) or {}
    rows = b.get("leads") or []
    default_source = (b.get("source") or "Import")[:120]
    if not isinstance(rows, list) or not rows:
        return jsonify({"ok": False, "error": "no leads provided"}), 400
    rows = rows[:2000]
    existing = _load_leads()
    if existing is None:
        return jsonify({"ok": False, "error": "store not configured"}), 200
    seen = set()
    for l in existing:
        k = ((l.get("property") or "") + "|" + (l.get("company") or "") + "|" + (l.get("email") or "")).lower().strip()
        if k.strip("|"):
            seen.add(k)
    added, skipped = 0, 0
    for r in rows:
        name = (str(r.get("name") or "")).strip()[:200]
        company = (str(r.get("company") or "")).strip()[:200]
        prop = (str(r.get("property") or "")).strip()[:300]
        email = (str(r.get("email") or "")).strip()[:200]
        phone = (str(r.get("phone") or "")).strip()[:60]
        message = (str(r.get("message") or "")).strip()[:5000]
        if not (name or company or prop or email or phone):
            continue
        k = (prop + "|" + company + "|" + email).lower().strip()
        if k in seen:
            skipped += 1
            continue
        seen.add(k)
        lead = {
            "id": _gen_id(), "ts": _now_ms(), "name": name, "email": email, "phone": phone,
            "company": company, "property": prop, "message": message, "fields": {},
            "source": (str(r.get("source") or default_source))[:120], "ua": "import",
        }
        try:
            _, configured = _kv_cmd(["RPUSH", WWS_LEADS_KEY, json.dumps(lead)])
            if not configured:
                return jsonify({"ok": False, "error": "store not configured"}), 200
            added += 1
        except Exception:
            pass
    _log_activity("leads_import", "Imported {} lead(s), skipped {} dup(s) — {}".format(added, skipped, default_source))
    return jsonify({"ok": True, "added": added, "skipped": skipped})


# ==========================================================================
# Multi-property / portfolio switcher
# ==========================================================================
# Lightweight mapping: client email -> [{id, name, address, notes}]. This is
# ADDITIVE — requests/inspections/invoices continue to be scoped by client
# email exactly as before. When a client has 2+ properties on file, the
# portal shows a switcher and filters the existing lists client-side by
# matching each item's property/address text against the selected property.
# Progressive enhancement: clients with 0 or 1 property see no change.
CLIENT_PROPS_KEY = "wws:client_props"  # JSON map { email(lower): [ {id,name,address,notes,created_ts} ] }


def _client_props_all():
    raw, configured = _kv_cmd(["GET", CLIENT_PROPS_KEY])
    if not configured:
        return {}, False
    try:
        return (json.loads(raw) if raw else {}), True
    except Exception:
        return {}, True


def _client_props_save(m):
    _kv_cmd(["SET", CLIENT_PROPS_KEY, json.dumps(m)])


def _client_props_for(email):
    m, configured = _client_props_all()
    return m.get((email or "").lower().strip(), []) if configured else []


@app.get("/api/portal/properties")
def portal_properties():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "properties": []})
    props = _client_props_for(s["email"])
    return jsonify({"authed": True, "properties": props})


@app.get("/api/admin/client/properties")
def admin_client_properties():
    if not _is_admin(): return jsonify({"ok": False, "error": "forbidden"}), 401
    email = (request.args.get("email") or "").strip().lower()
    if not email: return jsonify({"ok": False, "error": "email required"}), 400
    return jsonify({"ok": True, "properties": _client_props_for(email)})


@app.post("/api/admin/client/properties")
def admin_client_properties_add():
    """Add (or update, if id is supplied) a property on a client's portfolio."""
    if not _is_admin(): return jsonify({"ok": False, "error": "forbidden"}), 401
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip().lower()
    name = (b.get("name") or "").strip()[:200]
    address = (b.get("address") or "").strip()[:300]
    notes = (b.get("notes") or "").strip()[:1000]
    if not email or not (name or address):
        return jsonify({"ok": False, "error": "email and (name or address) required"}), 400
    m, _ = _client_props_all()
    lst = m.get(email, [])
    pid = (b.get("id") or "").strip()
    if pid:
        for p in lst:
            if p.get("id") == pid:
                p.update({"name": name, "address": address, "notes": notes})
                break
        else:
            lst.append({"id": pid, "name": name, "address": address, "notes": notes, "created_ts": _now_ms()})
    else:
        lst.append({"id": _gen_id(), "name": name, "address": address, "notes": notes, "created_ts": _now_ms()})
    m[email] = lst
    _client_props_save(m)
    _log_activity("client_property_add", f"{name or address} for {email}")
    return jsonify({"ok": True, "properties": lst})


@app.post("/api/admin/client/properties/<pid>/delete")
def admin_client_properties_delete(pid):
    if not _is_admin(): return jsonify({"ok": False, "error": "forbidden"}), 401
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip().lower()
    if not email: return jsonify({"ok": False, "error": "email required"}), 400
    m, _ = _client_props_all()
    lst = [p for p in m.get(email, []) if p.get("id") != pid]
    m[email] = lst
    _client_props_save(m)
    return jsonify({"ok": True, "properties": lst})


def _matches_property(text, prop):
    """Loose match: does a free-text property/address field belong to the
    selected portfolio property? Used to filter the existing (string-based)
    requests/inspections/invoices by the switcher selection."""
    if not prop:
        return True
    t = (text or "").lower().strip()
    if not t:
        return False
    for key in ("address", "name"):
        v = (prop.get(key) or "").lower().strip()
        if v and (v in t or t in v):
            return True
    return False


# ---- customer portal (any signed-in user) ----
@app.post("/api/portal/request")
def portal_request():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
    if s.get("readonly"):
        return jsonify({"ok": False, "error": "read-only access cannot submit requests"}), 403
    _allowed, _retry = _rate_limit("portal_request:" + s["email"].lower(), 20, 3600)
    if not _allowed:
        return _rate_limited_response(_retry)
    body = request.get_json(force=True, silent=True) or {}
    req = {
        "id": _gen_id(), "ts": _now_ms(), "kind": "inspection_request",
        "email": s.get("email", ""), "name": s.get("name", ""),
        "company": (body.get("company") or "").strip()[:200],
        "property": (body.get("property") or "").strip()[:300],
        "buildings": (body.get("buildings") or "").strip()[:60],
        "stories": (body.get("stories") or "").strip()[:60],
        "urgency": (body.get("urgency") or "").strip()[:60],
        "notes": (body.get("notes") or "").strip()[:3000],
    }
    if not req["property"] and not req["company"]:
        return jsonify({"ok": False, "error": "property or company required"}), 400
    try:
        _kv_cmd(["RPUSH", WWS_REQ_KEY, json.dumps(req)])
    except Exception:
        pass
    _notify("WWS inspection request — " + (req["company"] or req["email"]),
            "A client requested an inspection via the portal:\n\n"
            "From: {} <{}>\nCompany: {}\nProperty: {}\nBuildings: {} / stories: {}\n"
            "Urgency: {}\n\nNotes:\n{}".format(
                req["name"], req["email"], req["company"], req["property"],
                req["buildings"], req["stories"], req["urgency"], req["notes"]))
    return jsonify({"ok": True})


# ==========================================================================
# Certificate of Insurance (COI) requests — client tells La Gala exactly what
# coverage + exact verbiage a GC/property manager needs on the certificate
# (certificate holder, additional insured, waiver of subrogation, project
# name). This is an intake/tracking tool, not a document generator — the
# actual ACORD 25 certificate is issued by La Gala's insurance broker.
# ==========================================================================
WWS_COI_ALL_KEY = "wws:coireq:all"


def _coi_key(cid): return "wws:coireq:" + cid
def _coi_client_key(email): return "wws:coireq:client:" + (email or "").lower().strip()


def _coi_get(cid):
    raw = _kv_cmd(["GET", _coi_key(cid)])
    if not raw: return None
    try: return json.loads(raw)
    except Exception: return None


def _coi_save(rec):
    _kv_cmd(["SET", _coi_key(rec["id"]), json.dumps(rec)])
    _kv_cmd(["LREM", WWS_COI_ALL_KEY, 0, rec["id"]])
    _kv_cmd(["RPUSH", WWS_COI_ALL_KEY, rec["id"]])
    ck = _coi_client_key(rec.get("client_email", ""))
    _kv_cmd(["LREM", ck, 0, rec["id"]])
    _kv_cmd(["RPUSH", ck, rec["id"]])


def _coi_list(ids):
    out = []
    for cid in (ids or []):
        x = _coi_get(cid)
        if x: out.append(x)
    return sorted(out, key=lambda r: r.get("created_ts", 0), reverse=True)


COI_COVERAGE_TYPES = ("general_liability", "workers_comp", "auto_liability", "umbrella")


@app.post("/api/portal/coi-request")
def portal_coi_request():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
    if s.get("readonly"):
        return jsonify({"ok": False, "error": "read-only access cannot submit requests"}), 403
    owner_email = _effective_email(s)
    _allowed, _retry = _rate_limit("coi_request:" + owner_email.lower(), 20, 3600)
    if not _allowed:
        return _rate_limited_response(_retry)
    body = request.get_json(force=True, silent=True) or {}
    coverage = [c for c in (body.get("coverage_types") or []) if c in COI_COVERAGE_TYPES]
    holder_name = (body.get("holder_name") or "").strip()[:200]
    if not coverage or not holder_name:
        return jsonify({"ok": False, "error": "at least one coverage type and a certificate holder name are required"}), 400
    rec = {
        "id": _gen_id(), "created_ts": _now_ms(), "status": "requested",
        "client_email": owner_email, "client_name": s.get("name", ""),
        "coverage_types": coverage,
        "holder_name": holder_name,
        "holder_address": (body.get("holder_address") or "").strip()[:400],
        "project_name": (body.get("project_name") or "").strip()[:300],
        "additional_insured": bool(body.get("additional_insured")),
        "waiver_of_subrogation": bool(body.get("waiver_of_subrogation")),
        "notes": (body.get("notes") or "").strip()[:2000],
    }
    _coi_save(rec)
    _notify("WWS certificate of insurance request — " + (rec["client_name"] or rec["client_email"]),
            "A client requested a certificate of insurance via the portal:\n\n"
            "From: {} <{}>\nCoverage: {}\nCertificate holder: {}\nHolder address: {}\n"
            "Project / property: {}\nAdditional insured: {}\nWaiver of subrogation: {}\n\n"
            "Special wording / notes:\n{}".format(
                rec["client_name"], rec["client_email"], ", ".join(coverage), rec["holder_name"],
                rec["holder_address"], rec["project_name"],
                "Yes" if rec["additional_insured"] else "No",
                "Yes" if rec["waiver_of_subrogation"] else "No", rec["notes"]))
    return jsonify({"ok": True, "request": rec})


@app.get("/api/portal/coi-requests")
def portal_coi_requests():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "requests": []})
    owner_email = _effective_email(s)
    ids = _kv_cmd(["LRANGE", _coi_client_key(owner_email), 0, -1]) or []
    return jsonify({"authed": True, "requests": _coi_list(ids)})


@app.get("/api/admin/coi-requests")
def admin_coi_requests():
    if not _is_admin(): return jsonify({"ok": False, "error": "auth required"}), 401
    ids = _kv_cmd(["LRANGE", WWS_COI_ALL_KEY, 0, -1]) or []
    return jsonify({"ok": True, "requests": _coi_list(ids)})


@app.post("/api/admin/coi-request/<cid>/status")
def admin_coi_request_status(cid):
    if not _is_admin(): return jsonify({"ok": False, "error": "auth required"}), 401
    rec = _coi_get(cid)
    if not rec: return jsonify({"ok": False, "error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    new_status = (body.get("status") or rec["status"])
    rec["status"] = new_status
    if new_status == "sent" and not rec.get("sent_ts"):
        rec["sent_ts"] = _now_ms()
    _coi_save(rec)
    _log_activity("coi_request_status", "COI request {} -> {} for {}".format(cid[:8], new_status, rec.get("client_email", "")))
    return jsonify({"ok": True, "request": rec})


def _effective_email(s):
    """The email whose data should be shown: the delegate's owner if this is
    a read-only delegate session, otherwise the signed-in user's own email.
    Purely additive — existing (non-delegate) sessions are unaffected since
    s.get('readonly') is absent/false for them."""
    s = s or {}
    if s.get("readonly") and s.get("delegate_owner"):
        return s["delegate_owner"]
    return s.get("email", "")


@app.get("/api/portal/requests")
def portal_requests():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "requests": []})
    owner_email = _effective_email(s)
    mine = [r for r in _load_requests() if r.get("email", "").lower() == owner_email.lower()]
    pid = (request.args.get("property_id") or "").strip()
    if pid:
        sel = next((p for p in _client_props_for(owner_email) if p.get("id") == pid), None)
        if sel:
            mine = [r for r in mine if _matches_property(r.get("property", ""), sel)]
    return jsonify({"authed": True, "email": s.get("email"), "name": s.get("name", ""),
                    "readonly": bool(s.get("readonly")), "requests": mine})


def _client_owns(x, email):
    """A portal client may only ever see an inspection whose client email matches
    their signed-in Google email."""
    ce = ((x.get("client") or {}).get("email") or "").lower()
    return bool(email) and ce == (email or "").lower()


@app.get("/api/portal/inspections")
def portal_inspections():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "inspections": []})
    email = _effective_email(s)
    pid = (request.args.get("property_id") or "").strip()
    sel = None
    if pid:
        sel = next((p for p in _client_props_for(email) if p.get("id") == pid), None)
    out = []
    for iid in (_insp_index() or []):
        x = _insp_get(iid)
        if not x or not _client_owns(x, email):
            continue
        prop = x.get("property", {})
        if sel and not (_matches_property(prop.get("name", ""), sel) or _matches_property(prop.get("address", ""), sel)):
            continue
        photos = [{"thumbUrl": p.get("thumbUrl") or p.get("url"), "url": p.get("url") or p.get("thumbUrl"),
                   "caption": p.get("caption", "")} for p in (x.get("photos") or []) if (p.get("thumbUrl") or p.get("url"))]
        accept = x.get("acceptance") or {}
        docs = ["report", "checklist", "proposal"]
        # property-level compliance verify link/QR, once one has been generated
        ptoken = x.get("property_verify_token")
        if ptoken:
            docs.append("compliance")
        row = {"id": x["id"], "created_ts": x.get("created_ts"), "status": x.get("status", "draft"),
               "property": {"name": prop.get("name", ""), "address": prop.get("address", "")},
               "photos": photos, "docs": docs,
               "proposal_accepted": bool(accept.get("name_typed")),
               "acceptance": {"name_typed": accept.get("name_typed", ""), "ts": accept.get("ts")} if accept.get("name_typed") else None}
        # recert countdown badge — skipped gracefully if the record has no expiration data
        badge = _recert_badge(x)
        if badge:
            row["recert"] = badge
        # PE info for the credentials panel (feature 4), if this inspection has it
        pe = x.get("pe") or {}
        if pe.get("name") or pe.get("license"):
            row["pe"] = {"name": pe.get("name", ""), "license": pe.get("license", "")}
        if ptoken:
            row["verify_url"] = _verify_url("property", ptoken)
        out.append(row)
    out.sort(key=lambda i: i.get("created_ts", 0), reverse=True)
    return jsonify({"authed": True, "email": s.get("email", ""), "name": s.get("name", ""),
                    "readonly": bool(s.get("readonly")), "inspections": out})


@app.get("/api/portal/summary")
def portal_summary():
    """Lightweight dashboard summary for the signed-in client: next upcoming
    inspection, open-invoice count/total, and the most recently added document."""
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False})
    email = s.get("email", "")

    # Upcoming inspection = most recently created inspection not yet complete/sealed.
    upcoming = None
    latest_doc = None
    for iid in (_insp_index() or []):
        x = _insp_get(iid)
        if not x or not _client_owns(x, email):
            continue
        st = (x.get("status") or "draft").lower()
        prop = x.get("property", {})
        if st in ("draft", "field"):
            if not upcoming or (x.get("created_ts", 0) > upcoming.get("created_ts", 0)):
                upcoming = {"id": x["id"], "status": st, "created_ts": x.get("created_ts", 0),
                            "property": {"name": prop.get("name", ""), "address": prop.get("address", "")}}
        ld = x.get("last_doc")
        if ld and ld.get("ts"):
            cand = {"kind": ld.get("kind", ""), "label": ld.get("label", ld.get("kind", "")),
                    "ts": ld.get("ts", 0), "inspection_id": x["id"],
                    "url": "/api/portal/inspection/%s/doc/%s" % (x["id"], ld.get("kind", ""))}
            if not latest_doc or cand["ts"] > latest_doc["ts"]:
                latest_doc = cand

    # Open invoices for this client.
    ids = _kv_cmd(["LRANGE", _inv_client_key(email), 0, -1]) or []
    open_invoices = [i for i in _inv_list(ids) if i.get("status") == "open"]
    open_total_cents = sum(i.get("amount_cents", 0) for i in open_invoices)

    return jsonify({
        "authed": True,
        "upcoming_inspection": upcoming,
        "open_invoice_count": len(open_invoices),
        "open_invoice_total_cents": open_total_cents,
        "latest_document": latest_doc,
    })


@app.get("/api/portal/inspection/<iid>/doc/<kind>")
def portal_inspection_doc(iid, kind):
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"error": "sign in required"}), 401
    x = _insp_get(iid)
    if not x or not _client_owns(x, _effective_email(s)):
        return jsonify({"error": "not found"}), 404
    if kind not in DOC_BUILDERS or not _RL:
        return jsonify({"error": "unavailable"}), 400
    try:
        if kind == "compliance":
            refresh_property_compliance(x)
        else:
            x["_verify_url"] = _verify_url("document", _doc_token_for(x, kind))
        pdf = DOC_BUILDERS[kind](x)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_WWS_%s.pdf"' % kind
    return resp


@app.get("/api/portal/inspection/<iid>/board-packet")
def portal_board_packet(iid):
    """Board-ready compliance packet cover sheet. SIMPLIFICATION: no PDF-merge
    library is available in this project (no PyPDF2/pypdf in requirements.txt
    and adding an unverified new dependency is out of scope here), so this
    returns the cover sheet as its own one-page PDF. The portal pairs it with
    direct links to download the existing individual documents (checklist /
    report / engineer packet / proposal) so the client can assemble/print the
    full board packet from the cover sheet + those PDFs."""
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"error": "sign in required"}), 401
    x = _insp_get(iid)
    if not x or not _client_owns(x, s.get("email", "")):
        return jsonify({"error": "not found"}), 404
    if not _RL:
        return jsonify({"error": "pdf engine unavailable"}), 503
    try:
        pdf = doc_board_cover(x)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_Board_Packet_Cover_%s.pdf"' % iid[:10]
    return resp


@app.post("/api/portal/inspection/<iid>/accept")
def portal_inspection_accept(iid):
    """E-signature-style acceptance of the corrective-work proposal. Records a
    server-logged acceptance (typed legal name + timestamp + IP + UA) — no
    third-party e-signature service, per policy."""
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
    x = _insp_get(iid)
    if not x or not _client_owns(x, s.get("email", "")):
        return jsonify({"ok": False, "error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    name_typed = (body.get("name_typed") or "").strip()[:200]
    if not name_typed:
        return jsonify({"ok": False, "error": "type your full legal name to accept"}), 400
    record = {
        "id": _gen_id(),
        "doc_id": iid,
        "name_typed": name_typed,
        "email": s.get("email", ""),
        "ts": _now_ms(),
        "ip_address": ((request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.remote_addr or ""))[:80],
        "user_agent": request.headers.get("User-Agent", "")[:300],
    }
    try:
        _kv_cmd(["RPUSH", "wws:acceptances", json.dumps(record)])
    except Exception:
        pass
    x["acceptance"] = record
    x["status"] = "accepted" if x.get("status") in ("draft", "field", "complete", "sealed") else x.get("status", "accepted")
    _insp_save(x)
    _log_activity("proposal_accept", f"Inspection {iid[:8]} accepted by {name_typed}")
    return jsonify({"ok": True, "acceptance": record})


# ==========================================================================
# WWS invoices & payments
# ==========================================================================
WWS_INV_ALL_KEY = "wws:inv:all"


def _inv_key(iid): return "wws:inv:" + iid
def _inv_client_key(email): return "wws:inv:client:" + (email or "").lower().strip()


def _inv_get(iid):
    raw = _kv_cmd(["GET", _inv_key(iid)])
    if not raw: return None
    try: return json.loads(raw)
    except: return None


def _inv_save(inv):
    _kv_cmd(["SET", _inv_key(inv["id"]), json.dumps(inv)])
    _kv_cmd(["LREM", WWS_INV_ALL_KEY, 0, inv["id"]])
    _kv_cmd(["RPUSH", WWS_INV_ALL_KEY, inv["id"]])
    ck = _inv_client_key(inv.get("client_email", ""))
    _kv_cmd(["LREM", ck, 0, inv["id"]])
    _kv_cmd(["RPUSH", ck, inv["id"]])


def _inv_list(ids):
    out = []
    for iid in (ids or []):
        x = _inv_get(iid)
        if x: out.append(x)
    return sorted(out, key=lambda i: i.get("created_ts", 0), reverse=True)


@app.get("/api/portal/invoices")
def portal_invoices():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "invoices": []})
    owner_email = _effective_email(s)
    ids = _kv_cmd(["LRANGE", _inv_client_key(owner_email), 0, -1]) or []
    invs = _inv_list(ids)
    pid = (request.args.get("property_id") or "").strip()
    if pid:
        sel = next((p for p in _client_props_for(owner_email) if p.get("id") == pid), None)
        if sel:
            invs = [i for i in invs if not i.get("property") or _matches_property(i.get("property", ""), sel)]
    return jsonify({"authed": True, "readonly": bool(s.get("readonly")), "invoices": invs})


@app.get("/api/admin/invoices")
def admin_invoices():
    if not _is_admin(): return jsonify({"ok": False, "error": "auth required"}), 401
    ids = _kv_cmd(["LRANGE", WWS_INV_ALL_KEY, 0, -1]) or []
    return jsonify({"ok": True, "invoices": _inv_list(ids)})


@app.post("/api/admin/invoice")
def admin_create_invoice():
    if not _is_admin(): return jsonify({"ok": False, "error": "auth required"}), 401
    _allowed, _retry = _rate_limit("admin_invoice:" + _admin_name(), 60, 3600)
    if not _allowed:
        return _rate_limited_response(_retry)
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get("client_email") or "").strip().lower()[:200]
    if not email: return jsonify({"ok": False, "error": "client_email required"}), 400
    try: cents = int(float(body.get("amount") or 0) * 100)
    except: cents = 0
    desc = (body.get("description") or "").strip()[:500]
    inv = {
        "id": _gen_id(), "created_ts": _now_ms(),
        "client_email": email,
        "client_name": (body.get("client_name") or "").strip()[:200],
        "description": desc,
        "property": (body.get("property") or "").strip()[:300],
        "amount_cents": cents,
        "due_date": (body.get("due_date") or "").strip()[:20],
        "pay_url": (body.get("pay_url") or "").strip()[:500],
        "status": "open",
        "created_by": _admin_name(),
    }
    _inv_save(inv)
    _log_activity("invoice_create", f"${cents/100:.2f} for {email} — {desc[:60]}")
    try:
        amt_str = "${:,.2f}".format(cents / 100)
        _notify_client(
            email, "New invoice from La Gala Construction — " + amt_str,
            "A new invoice is ready.",
            "{} is due{}. {}".format(
                amt_str,
                (" on " + inv["due_date"]) if inv.get("due_date") else "",
                (desc if desc else "")
            ).strip(),
            cta_label="View invoice",
        )
    except Exception:
        pass
    return jsonify({"ok": True, "invoice": inv})


@app.post("/api/admin/invoice/<iid>/status")
def admin_invoice_status(iid):
    if not _is_admin(): return jsonify({"ok": False, "error": "auth required"}), 401
    inv = _inv_get(iid)
    if not inv: return jsonify({"ok": False, "error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    new_status = (body.get("status") or inv["status"])
    inv["status"] = new_status
    if new_status == "paid" and not inv.get("paid_ts"):
        inv["paid_ts"] = _now_ms()
    _inv_save(inv)
    _log_activity("invoice_status", f"Invoice {iid[:8]} → {new_status} for {inv.get('client_email','')}")
    return jsonify({"ok": True, "invoice": inv})


# ==========================================================================
# Contractor credentials (feature 4) — CGC license is site copy; COI expiration
# is the one admin-editable value, stored in KV as a tiny settings blob.
# ==========================================================================
WWS_CGC_LICENSE = "CGC059211"
WWS_SETTINGS_KEY = "wws:settings"


def _wws_settings():
    raw, configured = _kv_cmd(["GET", WWS_SETTINGS_KEY])
    if not configured or not raw:
        return {}
    try:
        return json.loads(raw) or {}
    except Exception:
        return {}


@app.get("/api/portal/credentials")
def portal_credentials():
    """PUBLIC-safe (also used by the signed-in portal): license + insurance status.
    No client PII. COI expiration is blank/TBD unless an admin has set it."""
    settings = _wws_settings()
    coi_exp = (settings.get("coi_expiration") or "").strip()
    coi_lapsed = False
    if coi_exp:
        days = _days_until(coi_exp)
        coi_lapsed = days is not None and days < 0
    return jsonify({
        "ok": True,
        "cgc_license": WWS_CGC_LICENSE,
        "coi_expiration": coi_exp,
        "coi_lapsed": coi_lapsed,
    })


@app.post("/api/admin/settings/coi")
def admin_set_coi():
    if not _is_admin():
        return jsonify({"ok": False, "error": "auth required"}), 401
    body = request.get_json(force=True, silent=True) or {}
    settings = _wws_settings()
    settings["coi_expiration"] = (body.get("coi_expiration") or "").strip()[:20]
    _kv_cmd(["SET", WWS_SETTINGS_KEY, json.dumps(settings)])
    _log_activity("settings_update", f"COI expiration set to {settings['coi_expiration'] or '(cleared)'}")
    return jsonify({"ok": True, "coi_expiration": settings["coi_expiration"]})


@app.get("/api/admin/settings")
def admin_get_settings():
    if not _is_admin():
        return jsonify({"ok": False, "error": "auth required"}), 401
    settings = _wws_settings()
    return jsonify({"ok": True, "cgc_license": WWS_CGC_LICENSE, "coi_expiration": settings.get("coi_expiration", "")})


# ==========================================================================
# KV-based sliding-window rate limiter
#
# Applied to: new email/OTP login routes, plus existing POST /api/lead,
# POST /api/admin/invoice, and POST /api/portal/request (best-effort — the
# limiter itself never breaks the request if KV is unconfigured/unreachable).
# ==========================================================================
def _client_ip():
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.remote_addr or ""))[:64]


def _rate_limit(key, max_requests, window_seconds):
    """Sliding-window-ish limiter backed by KV INCR + EXPIRE (fixed window,
    which is a fine approximation for abuse prevention here). Returns
    (allowed: bool, retry_after_seconds: int). Fails OPEN (allowed=True) if
    KV is not configured or errors, so a store outage never blocks the site."""
    rk = "ratelimit:" + key
    try:
        count, configured = _kv_cmd(["INCR", rk])
        if not configured:
            return True, 0
        count = int(count or 0)
        if count == 1:
            _kv_cmd(["EXPIRE", rk, window_seconds])
        if count > max_requests:
            ttl, _ = _kv_cmd(["TTL", rk])
            return False, max(1, int(ttl or window_seconds))
        return True, 0
    except Exception:
        return True, 0


def _rate_limited_response(retry_after):
    resp = jsonify({"ok": False, "error": "Too many requests. Please try again shortly."})
    resp.status_code = 429
    resp.headers["Retry-After"] = str(retry_after)
    return resp


# ==========================================================================
# CSRF protection — issued per-session, checked on new state-changing POSTs
# added in this batch only (email OTP verify, delegate create/revoke).
# Existing routes are intentionally left untouched.
# ==========================================================================
def _check_csrf(body):
    s = read_session() or {}
    tok = s.get("csrf")
    sent = (body or {}).get("csrf") or request.headers.get("X-CSRF-Token")
    return bool(tok) and bool(sent) and secrets.compare_digest(tok, sent)


@app.get("/api/csrf")
def get_csrf():
    """Issue (or return the existing) per-session CSRF token for the signed-in
    client. Frontend calls this once and includes the token on new
    state-changing POSTs (email OTP verify isn't signed in yet, so it uses its
    own short-lived per-request token instead — see /api/login/email/start)."""
    s = read_session() or {}
    if not s.get("email") and not s.get("pin_admin"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
    if not s.get("csrf"):
        s["csrf"] = secrets.token_urlsafe(24)
    resp = make_response(jsonify({"ok": True, "csrf": s["csrf"]}))
    write_session(resp, s)
    return resp


# ==========================================================================
# Non-Google sign-in: email + one-time PIN (adds a second path into the SAME
# session shape the Google OAuth callback produces — {"provider", "email",
# "name", ...} — so every downstream read of session.email behaves the same
# regardless of which login path was used. Does not touch the Google or
# Microsoft OAuth code paths at all.)
# ==========================================================================
OTP_KEY_PREFIX = "wws:otp:"          # wws:otp:<email> -> {"code","ts","tries"}
OTP_TTL_SECONDS = 10 * 60            # 10 minutes
OTP_MAX_TRIES = 5                    # wrong-code attempts per issued code


def _otp_key(email):
    return OTP_KEY_PREFIX + (email or "").strip().lower()


@app.post("/api/login/email/start")
def login_email_start():
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get("email") or "").strip().lower()[:200]
    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "valid email required"}), 400

    # Rate-limit: max 5 code requests/hour per email, plus a coarser per-IP
    # guard so one IP can't hammer many different addresses.
    allowed, retry = _rate_limit("otp_start:email:" + email, 5, 3600)
    if not allowed:
        return _rate_limited_response(retry)
    allowed_ip, retry_ip = _rate_limit("otp_start:ip:" + _client_ip(), 20, 3600)
    if not allowed_ip:
        return _rate_limited_response(retry_ip)

    code = "{:06d}".format(secrets.randbelow(1000000))
    record = {"code": code, "ts": _now_ms(), "tries": 0}
    try:
        _kv_cmd(["SET", _otp_key(email), json.dumps(record)])
        _kv_cmd(["EXPIRE", _otp_key(email), OTP_TTL_SECONDS])
    except Exception:
        return jsonify({"ok": False, "error": "sign-in temporarily unavailable"}), 503

    ok, info = _resend_send({
        "from": RESEND_FROM if RESEND_KEY else "",
        "to": [email],
        "subject": "Your La Gala portal sign-in code",
        "html": (
            "<div style='font-family:Arial,sans-serif;color:#1f2733'>"
            "<p>Your one-time sign-in code for the La Gala WWS client portal is:</p>"
            "<p style='font-size:28px;font-weight:800;letter-spacing:4px;color:#13233f'>{}</p>"
            "<p style='color:#5b6573;font-size:13px'>This code expires in 10 minutes. If you didn't "
            "request this, you can ignore this email.</p></div>"
        ).format(code),
    }) if RESEND_KEY else (False, "RESEND_API_KEY not configured")

    if not ok:
        # Don't leak whether the store/email is misconfigured to the client;
        # log server-side only.
        _log_activity("otp_send_fail", info, name=email)
        return jsonify({"ok": False, "error": "Could not send the code. Please call (561) 475-8615."}), 502

    return jsonify({"ok": True, "sent_to": email})


@app.post("/api/login/email/verify")
def login_email_verify():
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get("email") or "").strip().lower()[:200]
    code = (body.get("code") or "").strip()[:12]
    if not email or not code:
        return jsonify({"ok": False, "error": "email and code required"}), 400

    allowed, retry = _rate_limit("otp_verify:email:" + email, 10, 3600)
    if not allowed:
        return _rate_limited_response(retry)

    try:
        raw, configured = _kv_cmd(["GET", _otp_key(email)])
    except Exception:
        configured = False
    if not configured:
        return jsonify({"ok": False, "error": "sign-in temporarily unavailable"}), 503
    if not raw:
        return jsonify({"ok": False, "error": "Code expired or not found. Request a new one."}), 400
    try:
        record = json.loads(raw)
    except Exception:
        return jsonify({"ok": False, "error": "Code expired or not found. Request a new one."}), 400

    if record.get("tries", 0) >= OTP_MAX_TRIES:
        _kv_cmd(["DEL", _otp_key(email)])
        return jsonify({"ok": False, "error": "Too many attempts. Request a new code."}), 429

    if not secrets.compare_digest(str(record.get("code", "")), code):
        record["tries"] = record.get("tries", 0) + 1
        try:
            _kv_cmd(["SET", _otp_key(email), json.dumps(record)])
            _kv_cmd(["EXPIRE", _otp_key(email), OTP_TTL_SECONDS])
        except Exception:
            pass
        return jsonify({"ok": False, "error": "Incorrect code."}), 401

    # success — consume the code and open the SAME session shape the Google
    # OAuth callback writes, so every existing session.email read works
    # identically regardless of login path.
    try:
        _kv_cmd(["DEL", _otp_key(email)])
    except Exception:
        pass
    resp = make_response(jsonify({"ok": True, "email": email}))
    write_session(resp, {"provider": "email_otp", "access_token": "otp", "email": email, "name": email.split("@")[0]})
    _log_activity("login", "Signed in via email code", name=email)
    return resp


# ==========================================================================
# Read-only delegate access — a signed-in client can invite a named
# recipient to view (not submit/pay) their own requests/inspections/invoices
# via a scoped magic-link token. Session payload gains an ADDITIVE
# "readonly"/"delegate_owner" flag on the recipient's session only; existing
# session fields and the Google/Microsoft OAuth paths are untouched.
# ==========================================================================
DELEGATE_KEY_PREFIX = "wws:delegate:"          # wws:delegate:<token> -> {owner_email, recipient_email, created_ts, scope}
DELEGATE_OWNER_INDEX = "wws:delegate:owner:"   # wws:delegate:owner:<owner_email> -> LIST of tokens


def _delegate_key(token):
    return DELEGATE_KEY_PREFIX + token


def _delegate_owner_index_key(owner_email):
    return DELEGATE_OWNER_INDEX + (owner_email or "").strip().lower()


@app.post("/api/portal/delegate/invite")
def portal_delegate_invite():
    s = read_session() or {}
    owner_email = s.get("email", "")
    if not owner_email:
        return jsonify({"ok": False, "error": "sign in required"}), 401
    if s.get("readonly"):
        return jsonify({"ok": False, "error": "read-only delegates cannot invite further delegates"}), 403

    body = request.get_json(force=True, silent=True) or {}
    if not _check_csrf(body):
        return jsonify({"ok": False, "error": "session expired, please refresh and try again"}), 403

    recipient = (body.get("email") or "").strip().lower()[:200]
    if not recipient or "@" not in recipient:
        return jsonify({"ok": False, "error": "valid recipient email required"}), 400
    if recipient == owner_email.lower():
        return jsonify({"ok": False, "error": "enter someone else's email"}), 400

    allowed, retry = _rate_limit("delegate_invite:" + owner_email.lower(), 10, 3600)
    if not allowed:
        return _rate_limited_response(retry)

    token = secrets.token_urlsafe(32)
    record = {
        "token": token,
        "owner_email": owner_email.lower(),
        "owner_name": s.get("name", ""),
        "recipient_email": recipient,
        "created_ts": _now_ms(),
        "scope": "readonly",
        "revoked": False,
    }
    try:
        _kv_cmd(["SET", _delegate_key(token), json.dumps(record)])
        _kv_cmd(["RPUSH", _delegate_owner_index_key(owner_email), token])
    except Exception:
        return jsonify({"ok": False, "error": "store not configured"}), 503

    link = base_url() + "/api/portal/delegate/accept/" + token
    _resend_send({
        "from": RESEND_FROM if RESEND_KEY else "",
        "to": [recipient],
        "subject": "You've been given read-only access to a La Gala compliance portal",
        "html": (
            "<div style='font-family:Arial,sans-serif;color:#1f2733'>"
            "<p><strong>{owner}</strong> ({owner_email}) has given you read-only access to their "
            "La Gala Construction OSHA compliance portal — you'll be able to view their inspection "
            "requests, documents, and invoices, but not submit or pay on their behalf.</p>"
            "<p><a href='{link}' style='background:#13233f;color:#fff;text-decoration:none;"
            "padding:12px 24px;border-radius:6px;display:inline-block;font-weight:600'>"
            "View the portal</a></p>"
            "<p style='color:#5b6573;font-size:13px'>If you weren't expecting this, you can ignore this email.</p>"
            "</div>"
        ).format(owner=s.get("name") or owner_email, owner_email=owner_email, link=link),
    }) if RESEND_KEY else None

    _log_activity("delegate_invite", "{} invited {}".format(owner_email, recipient), name=owner_email)
    return jsonify({"ok": True, "invited": recipient})


@app.get("/api/portal/delegate/accept/<token>")
def portal_delegate_accept(token):
    try:
        raw, configured = _kv_cmd(["GET", _delegate_key(token)])
    except Exception:
        configured = False
    if not configured or not raw:
        return _err_page("This invite link is invalid or has expired.")
    try:
        record = json.loads(raw)
    except Exception:
        return _err_page("This invite link is invalid or has expired.")
    if record.get("revoked"):
        return _err_page("This invite link has been revoked by its owner.")

    resp = make_response(redirect("/portal"))
    write_session(resp, {
        "provider": "delegate", "access_token": "readonly", "email": record["recipient_email"],
        "name": record["recipient_email"].split("@")[0],
        "readonly": True, "delegate_owner": record["owner_email"], "delegate_token": token,
    })
    _log_activity("delegate_accept", "{} accepted delegate link from {}".format(
        record["recipient_email"], record["owner_email"]), name=record["recipient_email"])
    return resp


@app.get("/api/portal/delegate/list")
def portal_delegate_list():
    s = read_session() or {}
    owner_email = s.get("email", "")
    if not owner_email:
        return jsonify({"ok": False, "error": "sign in required"}), 401
    try:
        tokens, configured = _kv_cmd(["LRANGE", _delegate_owner_index_key(owner_email), 0, -1])
    except Exception:
        configured = False
    if not configured:
        return jsonify({"ok": True, "delegates": []})
    out = []
    for t in (tokens or []):
        try:
            raw, _ = _kv_cmd(["GET", _delegate_key(t)])
            rec = json.loads(raw) if raw else None
        except Exception:
            rec = None
        if rec:
            out.append({"token": rec["token"][:8] + "…", "full_token": rec["token"],
                        "recipient_email": rec.get("recipient_email", ""),
                        "created_ts": rec.get("created_ts"), "revoked": rec.get("revoked", False)})
    out.sort(key=lambda x: x.get("created_ts", 0), reverse=True)
    return jsonify({"ok": True, "delegates": out})


@app.post("/api/portal/delegate/revoke")
def portal_delegate_revoke():
    s = read_session() or {}
    owner_email = s.get("email", "")
    if not owner_email:
        return jsonify({"ok": False, "error": "sign in required"}), 401
    body = request.get_json(force=True, silent=True) or {}
    if not _check_csrf(body):
        return jsonify({"ok": False, "error": "session expired, please refresh and try again"}), 403
    token = (body.get("token") or "").strip()
    if not token:
        return jsonify({"ok": False, "error": "token required"}), 400
    try:
        raw, configured = _kv_cmd(["GET", _delegate_key(token)])
    except Exception:
        configured = False
    if not configured or not raw:
        return jsonify({"ok": False, "error": "not found"}), 404
    try:
        record = json.loads(raw)
    except Exception:
        return jsonify({"ok": False, "error": "not found"}), 404
    if record.get("owner_email") != owner_email.lower():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    record["revoked"] = True
    _kv_cmd(["SET", _delegate_key(token), json.dumps(record)])
    _log_activity("delegate_revoke", "{} revoked delegate for {}".format(
        owner_email, record.get("recipient_email", "")), name=owner_email)
    return jsonify({"ok": True})


# ==========================================================================
# WWS field inspections + pre-filled documents (reportlab, server-side)
# ==========================================================================
import io
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image
    NAVY = colors.HexColor("#13233f"); GOLD = colors.HexColor("#c9a227")
    INK = colors.HexColor("#1f2733"); MUTE = colors.HexColor("#5b6573")
    LINE = colors.HexColor("#d8dce2"); ZEBRA = colors.HexColor("#f5f6f8"); CREAM = colors.HexColor("#f6efd9")
    _RL = True
except Exception:
    _RL = False
F, FB = "Helvetica", "Helvetica-Bold"
RED = "#b3261e"; GREEN = "#1e7a3d"; GREY = "#5b6573"
SEV = {"high": ("#b3261e", "HIGH"), "med": ("#b8860b", "MEDIUM"), "low": ("#1e7a3d", "LOW")}


def _fetch_img(url):
    """Fetch a durable public image URL into a BytesIO for PDF embedding.
    Best-effort, with a light SSRF guard: http(s) only, no loopback/private hosts."""
    try:
        if (url or "").startswith("data:"):
            import base64 as _b64
            b64 = url.partition(",")[2]
            return io.BytesIO(_b64.b64decode(b64)) if b64 else None
        from urllib.parse import urlparse
        p = urlparse(url or "")
        host = (p.hostname or "").lower()
        if p.scheme not in ("http", "https") or not host:
            return None
        if host == "localhost" or host.startswith(("127.", "10.", "192.168.", "169.254.")):
            return None
        if host.startswith("172."):
            seg = host.split(".")
            if len(seg) > 1 and seg[1].isdigit() and 16 <= int(seg[1]) <= 31:
                return None
        r = requests.get(url, timeout=8)
        if r.status_code < 300 and r.content:
            return io.BytesIO(r.content)
    except Exception:
        pass
    return None


SUBPART_D = [
    ("General Surface Conditions", "§1910.22", [
        "Surfaces clean, orderly, sanitary; dry or drained where wet",
        "Free of trip / sharp / corrosion / spill / ice hazards",
        "Each surface supports its maximum intended load",
        "Safe means of access and egress at every surface",
        "Inspected regularly; hazards corrected or guarded"]),
    ("Portable Ladders", "§1910.23(b),(c)", [
        "Inspected before use; defective ladders tagged out",
        "Rungs slip-resistant, level, spaced 10-14 in",
        "On stable level surface; secured where needed",
        "Side rails extend >= 3 ft above the landing",
        "Not overloaded; no improper use (boxes, top cap)"]),
    ("Fixed Ladders", "§1910.23(d)", [
        "Supports max load; corrosion-protected",
        "Clearances behind / beside rungs per code",
        "Through / side-step extensions; grab bars where required",
        "Ladders > 24 ft: PFAS or ladder safety system",
        "All fixed ladders need PFAS / LSS by Nov 18, 2036"]),
    ("Stairways", "§1910.25", [
        "Riser / tread geometry and width within limits",
        "Uniform risers and treads between landings",
        "Landings sized correctly; clearance maintained",
        "Stair-rail + handrails per Table D-2",
        "Landings >= 4 ft above lower level guarded"]),
    ("Dockboards", "§1910.26", [
        "Supports load; run-off prevented",
        "Secured / anchored against displacement; handholds",
        "Wheel chocks / restraints where required",
        "Guardrails where fall hazard >= 4 ft"]),
    ("Rope Descent Systems & Anchorages", "§1910.27", [
        "Each anchorage certified >= 5,000 lb per worker",
        "Annual qualified-person inspection current",
        "Anchorages re-tested at least every 10 years",
        "RDS inspected at start of each shift",
        "Each worker on an independent PFAS"]),
    ("Fall Protection - Duty & Criteria", "§1910.28 / .29", [
        "Unprotected sides / edges >= 4 ft protected",
        "Holes / skylights covered, guarded, or PFAS",
        "Low-slope roof edge work rules met",
        "Guardrails meet 200 / 150 lb strength criteria",
        "Toeboards where falling-object exposure exists"]),
    ("Training", "§1910.30", [
        "Trained by qualified person in fall-hazard recognition",
        "Trained to use the fall-protection systems in place",
        "RDS / dockboard users trained for their equipment",
        "Retraining when conditions or equipment change"]),
]


def _seed_findings():
    out = []
    for section, std, items in SUBPART_D:
        for it in items:
            out.append({"section": section, "std": std, "item": it, "result": "", "severity": "", "note": ""})
    return out


def _esc(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _dstyles():
    return {
        "wordmark": ParagraphStyle("wm", fontName=FB, fontSize=13, textColor=NAVY, leading=15),
        "doctype": ParagraphStyle("dt", fontName=F, fontSize=9, textColor=GOLD, leading=11, spaceAfter=1),
        "h1": ParagraphStyle("h1", fontName=FB, fontSize=17, textColor=NAVY, leading=20, spaceBefore=2, spaceAfter=2),
        "meta": ParagraphStyle("meta", fontName=F, fontSize=8.5, textColor=MUTE, leading=12),
        "metab": ParagraphStyle("metab", fontName=FB, fontSize=8.5, textColor=NAVY, leading=12),
        "sect": ParagraphStyle("sect", fontName=FB, fontSize=10.5, textColor=NAVY, leading=13, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", fontName=F, fontSize=9.5, textColor=INK, leading=13.5, spaceBefore=2),
        "th": ParagraphStyle("th", fontName=FB, fontSize=8, textColor=colors.white, leading=10),
        "thc": ParagraphStyle("thc", fontName=FB, fontSize=8, textColor=colors.white, leading=10, alignment=1),
        "td": ParagraphStyle("td", fontName=F, fontSize=8.5, textColor=INK, leading=11),
        "tdc": ParagraphStyle("tdc", fontName=F, fontSize=8.5, textColor=INK, leading=11, alignment=1),
        "tdr": ParagraphStyle("tdr", fontName=F, fontSize=8.5, textColor=INK, leading=11, alignment=2),
        "key": ParagraphStyle("key", fontName=F, fontSize=9, textColor=NAVY, leading=13, backColor=CREAM, borderPadding=(5, 6, 5, 6)),
        "disc": ParagraphStyle("disc", fontName=F, fontSize=7, textColor=MUTE, leading=9, spaceBefore=8),
    }


def _dfooter(c, d):
    c.saveState(); w, h = letter
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(0.7 * inch, 0.55 * inch, w - 0.7 * inch, 0.55 * inch)
    c.setFont(F, 7); c.setFillColor(MUTE)
    c.drawString(0.7 * inch, 0.4 * inch, "La Gala Construction / Tilt Patchers, Inc.  ·  CGC059211  ·  in partnership with a FL State Certified Engineer")
    c.drawRightString(w - 0.7 * inch, 0.4 * inch, "Page %d" % d.page)
    c.restoreState()
    # optional per-document verification QR, stamped bottom-right of page 1 only
    verify_url = getattr(d, "_verify_url", None)
    if verify_url and d.page == 1:
        qbuf = _qr_png(verify_url)
        if qbuf is not None:
            try:
                from reportlab.lib.utils import ImageReader
                c.saveState()
                qsize = 0.62 * inch
                qx, qy = w - 0.7 * inch - qsize, 0.65 * inch
                c.drawImage(ImageReader(qbuf), qx, qy, width=qsize, height=qsize, mask="auto")
                c.setFont(F, 5.5); c.setFillColor(MUTE)
                c.drawRightString(qx + qsize, qy - 7, "Scan to verify")
                c.restoreState()
            except Exception:
                pass


def _dheader(story, st, doctype, title, insp):
    p = insp.get("property", {}); cl = insp.get("client", {}); insr = insp.get("inspector", {})
    story.append(Paragraph("LA GALA CONSTRUCTION", st["wordmark"]))
    story.append(Paragraph(_esc(doctype), st["doctype"]))
    story.append(Paragraph(_esc(title), st["h1"]))
    rule = Table([[""]], colWidths=[7.1 * inch]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.3, GOLD)]))
    story.append(Spacer(1, 3)); story.append(rule); story.append(Spacer(1, 6))
    def kv(k, v): return [Paragraph(k, st["meta"]), Paragraph(_esc(v or "—"), st["metab"])]
    owner = (cl.get("name", "") + (("  ·  " + cl.get("company", "")) if cl.get("company") else "")).strip(" ·")
    rows = [
        kv("Property", p.get("name", "")) + kv("Inspected", insr.get("date", "")),
        kv("Address", p.get("address", "")) + kv("Inspector", insr.get("name", "")),
        kv("Owner / contact", owner) + kv("License", insr.get("license", "CGC059211")),
    ]
    t = Table(rows, colWidths=[0.95 * inch, 2.55 * inch, 0.85 * inch, 2.05 * inch])
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 6))


def _dtable_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3a4a63")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)])


def _dzebra(t, nrows, start=1):
    for r in range(start, nrows):
        if (r - start) % 2 == 1:
            t.setStyle(TableStyle([("BACKGROUND", (0, r), (-1, r), ZEBRA)]))


def _dnew(title):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.7 * inch, title=title)
    return buf, doc


def _dfinish(buf, doc, story, verify_url=None):
    doc._verify_url = verify_url
    doc.build(story, onFirstPage=_dfooter, onLaterPages=_dfooter)
    return buf.getvalue()


def _money(v):
    try:
        return "{:,.0f}".format(float(str(v).replace(",", "").replace("$", "")))
    except Exception:
        return str(v)


def doc_checklist(insp):
    st = _dstyles(); buf, doc = _dnew("Completed OSHA Subpart D Checklist"); story = []
    _dheader(story, st, "OSHA 1910 Subpart D / 1910.140 · ANSI/IWCA I-14.1 · ASME A120.1", "Anchor & Davit Visual Inspection Checklist", insp)

    # ---- building-level visual inspection fields ----
    vc = insp.get("visual_check") or {}
    def _yn(v): return v if v else "—"
    story.append(Paragraph("Building information &amp; engineered drawings", st["sect"]))
    brows = [
        [Paragraph("Parapet height", st["td"]), Paragraph(_esc(_yn(vc.get("parapet_height"))), st["td"]),
         Paragraph("Parapet type", st["td"]), Paragraph(_esc(_yn(vc.get("parapet_type"))), st["td"])],
        [Paragraph("Photos taken", st["td"]), Paragraph(_esc(_yn(vc.get("photos_taken"))), st["td"]),
         Paragraph("Windows on drawings", st["td"]), Paragraph(_esc(_yn(vc.get("windows_on_drawing"))), st["td"])],
        [Paragraph("Engineered drawing on site", st["td"]), Paragraph(_esc(_yn(vc.get("drawing_on_site"))), st["td"]),
         Paragraph("Drawing stamped / dated / signed", st["td"]), Paragraph(_esc(_yn(vc.get("drawing_stamped"))), st["td"])],
        [Paragraph("Accurate roof layout on drawing", st["td"]), Paragraph(_esc(_yn(vc.get("drawing_accurate"))), st["td"]),
         Paragraph("Rigging restrictions noted", st["td"]), Paragraph(_esc(_yn(vc.get("rigging_restrictions"))), st["td"])],
        [Paragraph("Adequate safety approach", st["td"]), Paragraph(_esc(_yn(vc.get("safety_approach"))), st["td"]),
         Paragraph("", st["td"]), Paragraph("", st["td"])],
    ]
    bt = Table(brows, colWidths=[2.3*inch, 0.9*inch, 2.3*inch, 0.9*inch])
    bt.setStyle(_dtable_style()); _dzebra(bt, len(brows)); story.append(bt)

    # ---- per-anchor visual inspection ----
    anchors = insp.get("anchors") or []
    if anchors:
        story.append(Paragraph("Anchor visual inspection  ·  Failure threshold: &gt;1/16″ permanent deflection", st["sect"]))
        arows = [[Paragraph("#", st["thc"]), Paragraph("Type", st["th"]), Paragraph("Location", st["th"]),
                  Paragraph("Pins", st["thc"]), Paragraph("Threads", st["thc"]),
                  Paragraph("Plates", st["thc"]), Paragraph("Rust", st["thc"]),
                  Paragraph("Result", st["thc"]), Paragraph("Deflection", st["thc"]), Paragraph("Note", st["th"])]]
        for a in anchors:
            res = (a.get("result") or "").lower()
            rc = GREEN if res == "pass" else (RED if res == "fail" else GREY)
            def _ync(v):
                if v == "Y": return '<font color="%s"><b>Y</b></font>' % GREEN
                if v == "N": return '<font color="%s"><b>N</b></font>' % RED
                return _esc(v or "—")
            arows.append([
                Paragraph(_esc(a.get("num", "")), st["tdc"]),
                Paragraph(_esc(a.get("type", "")), st["td"]),
                Paragraph(_esc(a.get("location", "")), st["td"]),
                Paragraph(_ync(a.get("pins", "")), st["tdc"]),
                Paragraph(_ync(a.get("threads", "")), st["tdc"]),
                Paragraph(_ync(a.get("plates", "")), st["tdc"]),
                Paragraph(_ync(a.get("rust", "")), st["tdc"]),
                Paragraph('<font color="%s"><b>%s</b></font>' % (rc, (a.get("result") or "—").upper()), st["tdc"]),
                Paragraph(_esc(a.get("deflection", "") or "—"), st["tdc"]),
                Paragraph(_esc(a.get("note", "")), st["td"]),
            ])
        at = Table(arows, colWidths=[0.45*inch, 1.0*inch, 1.3*inch, 0.45*inch, 0.55*inch, 0.45*inch, 0.45*inch, 0.65*inch, 0.65*inch, 1.15*inch], repeatRows=1)
        at.setStyle(_dtable_style()); _dzebra(at, len(arows)); story.append(at)

    # ---- per-davit visual inspection ----
    davits = insp.get("davits") or []
    if davits:
        story.append(Paragraph("Davit schedule  ·  Test load = 2× working load  ·  ASME A120.1", st["sect"]))
        drows = [[Paragraph("#", st["thc"]), Paragraph("Location", st["th"]), Paragraph("Height", st["thc"]),
                  Paragraph("Outreach", st["thc"]), Paragraph("Capacity", st["thc"]),
                  Paragraph("W/L (lbs)", st["thc"]), Paragraph("Test (2×)", st["thc"]),
                  Paragraph("Pins", st["thc"]), Paragraph("Rust", st["thc"]),
                  Paragraph("Result", st["thc"]), Paragraph("Deflection", st["thc"]), Paragraph("Note", st["th"])]]
        for d in davits:
            res = (d.get("result") or "").lower()
            rc = GREEN if res == "pass" else (RED if res == "fail" else GREY)
            wl = d.get("working_load", "")
            try: tl = str(int(float(wl) * 2)) + " lbs"
            except: tl = "—"
            def _ync2(v):
                if v == "Y": return '<font color="%s"><b>Y</b></font>' % GREEN
                if v == "N": return '<font color="%s"><b>N</b></font>' % RED
                return _esc(v or "—")
            drows.append([
                Paragraph(_esc(d.get("num", "")), st["tdc"]),
                Paragraph(_esc(d.get("location", "")), st["td"]),
                Paragraph(_esc(d.get("height", "") or "—"), st["tdc"]),
                Paragraph(_esc(d.get("outreach", "") or "—"), st["tdc"]),
                Paragraph(_esc(d.get("capacity", "") or "—"), st["tdc"]),
                Paragraph(_esc(str(wl) or "—"), st["tdc"]),
                Paragraph(tl, st["tdc"]),
                Paragraph(_ync2(d.get("pins", "")), st["tdc"]),
                Paragraph(_ync2(d.get("rust", "")), st["tdc"]),
                Paragraph('<font color="%s"><b>%s</b></font>' % (rc, (d.get("result") or "—").upper()), st["tdc"]),
                Paragraph(_esc(d.get("deflection", "") or "—"), st["tdc"]),
                Paragraph(_esc(d.get("note", "")), st["td"]),
            ])
        dvt = Table(drows, colWidths=[0.4*inch, 1.1*inch, 0.55*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.65*inch, 0.45*inch, 0.45*inch, 0.65*inch, 0.65*inch, 0.9*inch], repeatRows=1)
        dvt.setStyle(_dtable_style()); _dzebra(dvt, len(drows)); story.append(dvt)

    # ---- Subpart D findings checklist ----
    findings = insp.get("findings") or _seed_findings()
    secs, order = {}, []
    for f in findings:
        s = f.get("section", "Other")
        if s not in secs:
            secs[s] = []; order.append(s)
        secs[s].append(f)
    story.append(Paragraph("Subpart D field findings (.22–.30)", st["sect"]))
    for s in order:
        std = secs[s][0].get("std", "")
        story.append(Paragraph(_esc(s) + "  ·  " + _esc(std), st["sub"] if hasattr(st.get("sub"), "fontName") else st["body"]))
        rows = [[Paragraph("Inspection item", st["th"]), Paragraph("Result", st["thc"]), Paragraph("Note", st["th"])]]
        for f in secs[s]:
            res = (f.get("result") or "").lower()
            label = {"ok": "OK", "def": "DEF", "na": "N/A"}.get(res, "—")
            col = RED if res == "def" else (GREEN if res == "ok" else GREY)
            rows.append([Paragraph(_esc(f.get("item", "")), st["td"]),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (col, label), st["tdc"]),
                         Paragraph(_esc(f.get("note", "")), st["td"])])
        t = Table(rows, colWidths=[3.7 * inch, 0.8 * inch, 2.6 * inch], repeatRows=1)
        t.setStyle(_dtable_style()); _dzebra(t, len(rows))
        story.append(t)

    defs = [f for f in findings if (f.get("result") or "").lower() == "def"]
    story.append(Paragraph("Deficiencies to correct (%d)" % len(defs), st["sect"]))
    if defs:
        for f in defs:
            story.append(Paragraph("&bull; <b>%s</b> (%s): %s" % (_esc(f.get("item", "")), _esc(f.get("std", "")), _esc(f.get("note", "") or "see field notes")), st["body"]))
    else:
        story.append(Paragraph("No deficiencies recorded at the time of inspection.", st["body"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Inspector signature: ______________________________     Date: ____________", st["body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Owner / manager acknowledgment: ______________________________     Date: ____________", st["body"]))
    story.append(Paragraph("Field compliance record per OSHA 29 CFR 1910 Subpart D, 1910.140, ANSI/IWCA I-14.1, and ASME A120.1. Anchorage load-test certification and structural repair must be performed and sealed by a licensed Florida PE. Failure threshold: &gt;1/16″ permanent deflection.", st["disc"]))
    return _dfinish(buf, doc, story, verify_url=insp.get("_verify_url"))


def doc_report(insp):
    st = _dstyles(); buf, doc = _dnew("WWS Inspection Report"); story = []
    _dheader(story, st, "Walking-Working Surfaces - inspection findings", "Inspection Report", insp)
    findings = insp.get("findings") or []
    defs = [f for f in findings if (f.get("result") or "").lower() == "def"]
    nhigh = sum(1 for f in defs if (f.get("severity") or "").lower() == "high")
    band = [[Paragraph("Items reviewed", st["thc"]), Paragraph("Deficiencies", st["thc"]), Paragraph("High severity", st["thc"]), Paragraph("Standards", st["thc"])],
            [Paragraph(str(len(findings)), st["tdc"]), Paragraph(str(len(defs)), st["tdc"]), Paragraph(str(nhigh), st["tdc"]), Paragraph(str(len(set(f.get("std", "") for f in findings))), st["tdc"])]]
    bt = Table(band, colWidths=[1.78 * inch] * 4); bt.setStyle(_dtable_style())
    story.append(bt); story.append(Spacer(1, 4))
    if insp.get("summary"):
        story.append(Paragraph("Summary", st["sect"])); story.append(Paragraph(_esc(insp["summary"]), st["body"]))
    diagram = insp.get("diagram") or ""
    anchors = insp.get("anchors") or []
    if diagram:
        story.append(Paragraph("Roof anchor plan", st["sect"]))
        dbuf = _fetch_img(diagram) if _RL else None
        if dbuf is not None:
            try:
                story.append(Image(dbuf, width=6.9 * inch, height=4.6 * inch, kind="proportional"))
            except Exception:
                pass
    if anchors:
        story.append(Paragraph("Anchor schedule", st["sect"]))
        arows = [[Paragraph("#", st["thc"]), Paragraph("Type", st["th"]), Paragraph("Location", st["th"]),
                  Paragraph("Result", st["thc"]), Paragraph("Deflection", st["thc"]), Paragraph("Note", st["th"])]]
        for a in anchors:
            res = (a.get("result") or "").lower()
            rc = GREEN if res == "pass" else (RED if res == "fail" else GREY)
            arows.append([Paragraph(_esc(a.get("num", "")), st["tdc"]), Paragraph(_esc(a.get("type", "")), st["td"]),
                          Paragraph(_esc(a.get("location", "")), st["td"]),
                          Paragraph('<font color="%s"><b>%s</b></font>' % (rc, _esc(a.get("result", "") or "—")), st["tdc"]),
                          Paragraph(_esc(a.get("deflection", "")), st["tdc"]), Paragraph(_esc(a.get("note", "")), st["td"])])
        at = Table(arows, colWidths=[0.5 * inch, 1.3 * inch, 1.8 * inch, 0.8 * inch, 0.9 * inch, 1.8 * inch], repeatRows=1)
        at.setStyle(_dtable_style()); _dzebra(at, len(arows)); story.append(at)
        npass = sum(1 for a in anchors if (a.get("result") or "").lower() == "pass")
        nfail = sum(1 for a in anchors if (a.get("result") or "").lower() == "fail")
        story.append(Paragraph("%d anchors - %d pass, %d fail." % (len(anchors), npass, nfail), st["disc"]))
    story.append(Paragraph("Findings", st["sect"]))
    if defs:
        rows = [[Paragraph("Standard", st["th"]), Paragraph("Finding", st["th"]), Paragraph("Severity", st["thc"]), Paragraph("Note", st["th"])]]
        for f in defs:
            sevc, sevl = SEV.get((f.get("severity") or "").lower(), (GREY, "—"))
            rows.append([Paragraph(_esc(f.get("std", "")), st["td"]), Paragraph(_esc(f.get("item", "")), st["td"]),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (sevc, sevl), st["tdc"]), Paragraph(_esc(f.get("note", "")), st["td"])])
        t = Table(rows, colWidths=[1.0 * inch, 2.7 * inch, 0.8 * inch, 2.6 * inch], repeatRows=1)
        t.setStyle(_dtable_style()); _dzebra(t, len(rows)); story.append(t)
    else:
        story.append(Paragraph("No deficiencies were identified at the time of inspection.", st["body"]))
    photos = sorted(insp.get("photos") or [], key=lambda p: (not p.get("anchor"), p.get("anchor", "")))
    if photos:
        story.append(Paragraph("Photo log", st["sect"]))
        cells = []
        for ph in photos[:30]:
            img_url = ph.get("thumbUrl") or ph.get("url") or ""
            flow = []
            buf2 = _fetch_img(img_url) if (_RL and img_url) else None
            if buf2 is not None:
                try:
                    flow.append(Image(buf2, width=2.15 * inch, height=1.5 * inch, kind="proportional"))
                except Exception:
                    flow.append(Paragraph(_esc(img_url), st["td"]))
            else:
                flow.append(Paragraph(_esc(img_url or "captured in SiteCam"), st["td"]))
            anc = ph.get("anchor", ""); pres = (ph.get("result", "") or "")
            if anc:
                rc = GREEN if pres.lower() == "pass" else (RED if pres.lower() == "fail" else GREY)
                flow.append(Paragraph('<font color="%s"><b>%s</b></font>' % (rc, _esc(anc + (" - " + pres if pres else ""))), st["tdc"]))
            elif ph.get("caption"):
                flow.append(Paragraph(_esc(ph.get("caption", "")), st["tdc"]))
            cells.append(flow)
        while len(cells) % 3 != 0:
            cells.append("")
        grid = [cells[i:i + 3] for i in range(0, len(cells), 3)]
        gt = Table(grid, colWidths=[2.36 * inch] * 3)
        gt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                                ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
        story.append(gt)
        if len(photos) > 30:
            story.append(Paragraph("+ %d more photo(s) in SiteCam." % (len(photos) - 30), st["disc"]))
    if insp.get("recommendations"):
        story.append(Paragraph("Recommendations", st["sect"])); story.append(Paragraph(_esc(insp["recommendations"]), st["body"]))
    story.append(Paragraph("La Gala Construction provides licensed contracting services; engineered inspection and anchorage load-test certification are performed and sealed by an independent licensed Florida professional engineer. La Gala does not provide engineering services. Not legal advice.", st["disc"]))
    return _dfinish(buf, doc, story, verify_url=insp.get("_verify_url"))


def doc_cert(insp):
    st = _dstyles(); buf, doc = _dnew("Engineer Certification Packet"); story = []
    _dheader(story, st, "For review and seal by the licensed FL professional engineer", "Engineer Certification Packet", insp)
    pe = insp.get("pe", {})
    story.append(Paragraph("Items submitted for engineered certification", st["sect"]))
    findings = insp.get("findings") or []
    eng = [f for f in findings if f.get("std", "").startswith("§1910.27") or "anchor" in (f.get("item", "").lower()) or ((f.get("result", "").lower() == "def") and (f.get("severity", "").lower() == "high"))]
    if not eng:
        eng = [f for f in findings if f.get("std", "").startswith("§1910.27")]
    rows = [[Paragraph("Standard", st["th"]), Paragraph("Item requiring engineered certification", st["th"]), Paragraph("Field note", st["th"])]]
    for f in (eng or [{"std": "§1910.27", "item": "Roof anchorage load-test certification (5,000 lb / worker)", "note": ""}]):
        rows.append([Paragraph(_esc(f.get("std", "")), st["td"]), Paragraph(_esc(f.get("item", "")), st["td"]), Paragraph(_esc(f.get("note", "")), st["td"])])
    t = Table(rows, colWidths=[1.0 * inch, 3.5 * inch, 2.6 * inch], repeatRows=1)
    t.setStyle(_dtable_style()); _dzebra(t, len(rows)); story.append(t)
    story.append(Spacer(1, 6))
    story.append(Paragraph("Scope of certification requested", st["sect"]))
    story.append(Paragraph("The engineer is asked to inspect, test where applicable, and provide a sealed certification that the items above meet 29 CFR 1910 Subpart D (including §1910.27 anchorage capacity of 5,000 lb in any direction per worker) and applicable Florida Building Code. La Gala Construction performs the corrective work <b>to the engineer's sealed specification</b>.", st["key"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Engineer of record", st["sect"]))
    rows = [
        [Paragraph("Name", st["meta"]), Paragraph(_esc(pe.get("name", "") or "______________________________"), st["metab"])],
        [Paragraph("Firm", st["meta"]), Paragraph(_esc(pe.get("firm", "") or "______________________________"), st["metab"])],
        [Paragraph("FL PE license #", st["meta"]), Paragraph(_esc(pe.get("license", "") or "______________________________"), st["metab"])],
    ]
    t = Table(rows, colWidths=[1.3 * inch, 5.8 * inch]); t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(t); story.append(Spacer(1, 22))
    seal = Table([[Paragraph("Engineer signature & date", st["meta"]), Paragraph("Professional engineer seal", st["meta"])],
                  [Paragraph("______________________________", st["body"]), Paragraph("", st["body"])]],
                 colWidths=[3.55 * inch, 3.55 * inch], rowHeights=[14, 96])
    seal.setStyle(TableStyle([("BOX", (1, 0), (1, 1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
    story.append(seal)
    return _dfinish(buf, doc, story, verify_url=insp.get("_verify_url"))


def doc_proposal(insp):
    st = _dstyles(); buf, doc = _dnew("Corrective-Work Proposal"); story = []
    _dheader(story, st, "Scope of corrective work self-performed by La Gala", "Corrective-Work Proposal", insp)
    items = insp.get("corrective") or []
    rows = [[Paragraph("Scope of work", st["th"]), Paragraph("Standard", st["thc"]), Paragraph("Qty", st["thc"]), Paragraph("Unit", st["th"]), Paragraph("Price", st["thc"])]]
    total = 0.0
    for it in items:
        try:
            total += float(str(it.get("price", "0")).replace(",", "").replace("$", "") or 0)
        except Exception:
            pass
        line = it.get("scope", "")
        if it.get("note"):
            line += '  <font color="%s">(%s)</font>' % (GREY, _esc(it["note"]))
        rows.append([Paragraph(line, st["td"]), Paragraph(_esc(it.get("std", "")), st["tdc"]), Paragraph(_esc(it.get("qty", "")), st["tdc"]),
                     Paragraph(_esc(it.get("unit", "")), st["td"]), Paragraph("$" + _money(it.get("price", "")), st["tdr"])])
    if not items:
        rows.append([Paragraph("<i>Scope to be itemized from inspection findings.</i>", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"])])
    rows.append([Paragraph("<b>Total</b>", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("<b>$" + _money(total) + "</b>", st["tdr"])])
    t = Table(rows, colWidths=[3.5 * inch, 0.9 * inch, 0.5 * inch, 0.8 * inch, 1.0 * inch], repeatRows=1)
    t.setStyle(_dtable_style()); _dzebra(t, len(rows) - 1)
    t.setStyle(TableStyle([("LINEABOVE", (0, len(rows) - 1), (-1, len(rows) - 1), 1, NAVY), ("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), CREAM)]))
    story.append(t); story.append(Spacer(1, 8))
    story.append(Paragraph("La Gala Construction self-performs the corrective work above and <b>performs that work to the engineer's sealed specification</b>; the engineered inspection and any anchorage certification are provided and sealed by a licensed Florida professional engineer. One accountable team for the certificate and the fix.", st["key"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Terms", st["sect"]))
    story.append(Paragraph("Pricing is an estimate based on the inspection findings and is valid for 30 days. Final scope and price are confirmed after the engineered inspection. Engineered certification fees are billed by the professional engineer. Florida CGC059211; licensed, bonded, and insured.", st["body"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Accepted by: ______________________________     Title: ______________     Date: ____________", st["body"]))
    return _dfinish(buf, doc, story, verify_url=insp.get("_verify_url"))


def doc_compliance_badge(insp):
    """One-page building-level 'Certificate of Compliance' badge PDF. Property-scoped,
    not tied to a single document — regenerated whenever a passing inspection is logged."""
    st = _dstyles(); buf, doc = _dnew("Certificate of Compliance"); story = []
    _dheader(story, st, "Building-level walking-working surfaces compliance summary", "Certificate of Compliance", insp)
    p = insp.get("property", {})
    through = _compliance_through_date(insp) or "—"
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "This building is compliant through <b>%s</b>" % _esc(through),
        ParagraphStyle("bigkey", fontName=FB, fontSize=14, textColor=NAVY, leading=19,
                       backColor=CREAM, borderPadding=(10, 12, 10, 12))))
    story.append(Spacer(1, 14))
    rows = [
        [Paragraph("Property", st["meta"]), Paragraph(_esc(p.get("name", "") or "—"), st["metab"])],
        [Paragraph("Address", st["meta"]), Paragraph(_esc(p.get("address", "") or "—"), st["metab"])],
        [Paragraph("Basis of certification", st["meta"]), Paragraph("Most recent passing OSHA 29 CFR 1910 Subpart D walking-working surfaces inspection", st["metab"])],
    ]
    t = Table(rows, colWidths=[1.6 * inch, 5.5 * inch]); t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 16))
    token = insp.get("property_verify_token") or ""
    if token:
        qbuf = _qr_png(_verify_url("property", token))
        if qbuf is not None:
            try:
                qrow = Table([[Image(qbuf, width=1.15 * inch, height=1.15 * inch),
                               Paragraph("Scan to verify this certificate, or visit:<br/><b>%s</b>" % _esc(_verify_url("property", token)), st["body"])]],
                            colWidths=[1.3 * inch, 5.8 * inch])
                qrow.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                story.append(qrow); story.append(Spacer(1, 10))
            except Exception:
                pass
    story.append(Paragraph("This certificate reflects the compliance status of the building as of the date of the most recent passing field inspection on file with La Gala Construction. It is not a substitute for the underlying PE-sealed engineering certification, which governs in the event of any conflict. Verify current status at any time using the link or QR code above.", st["disc"]))
    return _dfinish(buf, doc, story)


DOC_BUILDERS = {"checklist": doc_checklist, "report": doc_report, "cert": doc_cert, "proposal": doc_proposal, "compliance": doc_compliance_badge}
DOC_LABEL = {"checklist": "Completed Subpart D Checklist", "report": "Inspection Report",
             "cert": "Engineer Certification Packet", "proposal": "Corrective-Work Proposal",
             "compliance": "Certificate of Compliance"}


# ==========================================================================
# Public document verification (QR + /verify/<token>) — feature 2 & 3
# ==========================================================================
VERIFY_KEY_PREFIX = "wws:verify:"     # per-document token -> summary JSON
VERIFY_PROP_PREFIX = "wws:verify:prop:"  # per-property token -> summary JSON


def _verify_url(kind, token):
    """Public verification URL embedded in the QR code / printed on documents."""
    root = "https://wwslgc." + ROOT_DOMAIN
    if kind == "property":
        return root + "/verify/property/" + token
    return root + "/verify/" + token


def _qr_png(url):
    """Server-side QR code (qrcode package) as a BytesIO PNG, or None if unavailable."""
    try:
        import qrcode
        img = qrcode.make(url)
        b = io.BytesIO()
        img.save(b, format="PNG")
        b.seek(0)
        return b
    except Exception:
        return None


def _parse_date(s):
    """Best-effort parse of a YYYY-MM-DD (or common variants) date string. Returns
    a time.struct_time in UTC, or None if unparseable/blank."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return time.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _cert_expiration(insp):
    """Expiration date string (YYYY-MM-DD) for an inspection's certification, based on
    cert_date + recert_months. Returns '' if there's no cert_date on the record —
    callers should skip the record gracefully rather than guessing."""
    cert_date = (insp.get("cert_date") or "").strip()
    parsed = _parse_date(cert_date)
    if not parsed:
        return ""
    months = insp.get("recert_months") or 12
    try:
        months = int(months)
    except Exception:
        months = 12
    import calendar
    y, m, d = parsed.tm_year, parsed.tm_mon, parsed.tm_mday
    total = (y * 12 + (m - 1)) + months
    ny, nm = divmod(total, 12)
    nm += 1
    last_day = calendar.monthrange(ny, nm)[1]
    nd = min(d, last_day)
    return "%04d-%02d-%02d" % (ny, nm, nd)


def _days_until(date_str):
    """Whole days from now until date_str (YYYY-MM-DD). Negative if already past.
    Returns None if date_str is blank/unparseable."""
    parsed = _parse_date(date_str)
    if not parsed:
        return None
    import datetime
    target = datetime.date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday)
    return (target - datetime.date.today()).days


def _recert_badge(insp):
    """Compute the recertification countdown badge for one inspection record.
    Returns None if the record has no expiration data (skip gracefully)."""
    exp = _cert_expiration(insp)
    if not exp:
        return None
    days = _days_until(exp)
    if days is None:
        return None
    if days < 30:
        level = "red"
    elif days <= 90:
        level = "amber"
    else:
        level = "green"
    return {"expires": exp, "days_left": days, "level": level}


def _compliance_through_date(insp):
    """Best-effort 'compliant through' date for the building-level badge:
    prefers an explicit cert_date + recert cycle, else the last passing inspection date."""
    cert_date = (insp.get("cert_date") or "").strip()
    if cert_date:
        exp = _cert_expiration(insp)
        if exp:
            return exp
    return (insp.get("inspector") or {}).get("date", "") or ""


def _doc_token_for(insp, kind):
    """Get-or-create an unguessable verification token for one generated document
    (doc kind + inspection id), stored in KV as a mapping to a public-safe summary."""
    key = "doc:%s:%s" % (insp.get("id", ""), kind)
    existing = (insp.get("doc_tokens") or {}).get(key)
    if existing:
        return existing
    token = secrets.token_urlsafe(18)
    try:
        summary = {
            "kind": "document", "doc_kind": kind,
            "doc_label": DOC_LABEL.get(kind, kind),
            "issue_date": _now_ms(),
            "property": {"name": (insp.get("property") or {}).get("name", ""),
                        "address": (insp.get("property") or {}).get("address", "")},
            "pe": {"name": (insp.get("pe") or {}).get("name", ""),
                  "license": (insp.get("pe") or {}).get("license", "")},
            "status": "valid",
            "inspection_id": insp.get("id", ""),
        }
        _kv_cmd(["SET", VERIFY_KEY_PREFIX + token, json.dumps(summary)])
    except Exception:
        pass
    insp.setdefault("doc_tokens", {})[key] = token
    try:
        _insp_save(insp)
    except Exception:
        pass
    return token


def _property_verify_token(insp):
    """Get-or-create the property-level verification token, and refresh its stored
    summary (used by the Certificate of Compliance badge)."""
    token = insp.get("property_verify_token")
    if not token:
        token = secrets.token_urlsafe(18)
        insp["property_verify_token"] = token
    try:
        summary = {
            "kind": "property",
            "property": {"name": (insp.get("property") or {}).get("name", ""),
                        "address": (insp.get("property") or {}).get("address", "")},
            "compliant_through": _compliance_through_date(insp),
            "last_inspection_date": (insp.get("inspector") or {}).get("date", ""),
            "status": insp.get("compliance_status", "valid"),
            "inspection_id": insp.get("id", ""),
        }
        _kv_cmd(["SET", VERIFY_PROP_PREFIX + token, json.dumps(summary)])
    except Exception:
        pass
    return token


def refresh_property_compliance(insp):
    """Hook: call whenever an inspection's status flips to a passing/complete state.
    Ensures the property has a verify token and its compliance summary is current."""
    insp["property_verify_token"] = _property_verify_token(insp)
    try:
        _insp_save(insp)
    except Exception:
        pass
    return insp["property_verify_token"]


@app.get("/api/verify/<token>")
def verify_document(token):
    """PUBLIC, unauthenticated. Shows minimal document-verification info — no PDF,
    no client PII beyond the property name/address."""
    token = (token or "")[:120]
    raw, configured = _kv_cmd(["GET", VERIFY_KEY_PREFIX + token])
    if not configured or not raw:
        return jsonify({"ok": False, "found": False}), 404
    try:
        s = json.loads(raw)
    except Exception:
        return jsonify({"ok": False, "found": False}), 404
    return jsonify({"ok": True, "found": True, "kind": "document",
                    "doc_label": s.get("doc_label", ""), "issue_date": s.get("issue_date"),
                    "property": s.get("property", {}),
                    "pe": s.get("pe", {}), "status": s.get("status", "valid")})


@app.get("/api/verify/property/<token>")
def verify_property(token):
    """PUBLIC, unauthenticated. Building-level compliance summary."""
    token = (token or "")[:120]
    raw, configured = _kv_cmd(["GET", VERIFY_PROP_PREFIX + token])
    if not configured or not raw:
        return jsonify({"ok": False, "found": False}), 404
    try:
        s = json.loads(raw)
    except Exception:
        return jsonify({"ok": False, "found": False}), 404
    return jsonify({"ok": True, "found": True, "kind": "property",
                    "property": s.get("property", {}),
                    "compliant_through": s.get("compliant_through", ""),
                    "last_inspection_date": s.get("last_inspection_date", ""),
                    "status": s.get("status", "valid")})


VERIFY_PAGE_TMPL = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="robots" content="noindex, nofollow"/>
<title>Document verification — La Gala Construction</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@700;800&family=Material+Symbols+Outlined&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={{theme:{{extend:{{colors:{{primary:"#13233f",secondary:"#c9a227",surface:"#f7f6f3",ink:"#1f2733",mute:"#54606f",line:"#e3e6ea"}},fontFamily:{{h:["Manrope"],b:["Inter"]}}}}}}}}</script>
<style>body{{font-family:'Inter',sans-serif}}h1,h2{{font-family:'Manrope',sans-serif}}.ms{{font-family:'Material Symbols Outlined'}}</style>
</head>
<body class="bg-surface text-ink min-h-screen flex flex-col">
<header class="bg-primary text-white"><div class="max-w-xl mx-auto px-5 py-3"><span class="font-h font-extrabold">La Gala Construction</span></div></header>
<main class="flex-1 max-w-xl mx-auto w-full px-5 py-14 text-center">
{body}
</main>
<footer class="text-center text-xs text-mute py-6">La Gala Construction / Tilt Patchers, Inc. &middot; CGC059211 &middot; Engineering certifications are performed and sealed by an independent, licensed Florida professional engineer.</footer>
</body></html>"""


def _verify_status_badge(status):
    status = (status or "valid").lower()
    if status == "valid":
        return '<span class="ms text-6xl text-green-600">verified</span><h1 class="text-2xl font-extrabold text-green-700 mt-3">Valid</h1>'
    if status == "superseded":
        return '<span class="ms text-6xl text-amber-500">history</span><h1 class="text-2xl font-extrabold text-amber-600 mt-3">Superseded</h1>'
    if status == "revoked":
        return '<span class="ms text-6xl text-red-600">cancel</span><h1 class="text-2xl font-extrabold text-red-700 mt-3">Revoked</h1>'
    return '<span class="ms text-6xl text-mute">help</span><h1 class="text-2xl font-extrabold text-mute mt-3">Unknown</h1>'


@app.get("/verify/<token>")
def verify_document_page(token):
    """PUBLIC HTML page — no auth, no PDF, no client PII beyond property name/address."""
    token = (token or "")[:120]
    raw, configured = _kv_cmd(["GET", VERIFY_KEY_PREFIX + token])
    if not configured or not raw:
        body = '<span class="ms text-6xl text-mute">search_off</span><h1 class="text-2xl font-extrabold text-primary mt-3">Document not found</h1><p class="text-mute mt-2">This verification link is invalid or has expired.</p>'
        return VERIFY_PAGE_TMPL.format(body=body), 404
    try:
        s = json.loads(raw)
    except Exception:
        s = {}
    prop = s.get("property", {}) or {}
    pe = s.get("pe", {}) or {}
    issue = s.get("issue_date")
    issue_str = time.strftime("%B %d, %Y", time.localtime(issue / 1000)) if issue else "—"
    body = _verify_status_badge(s.get("status")) + (
        '<p class="text-mute mt-2">%s</p>'
        '<div class="bg-white rounded-xl border border-line p-5 mt-6 text-left space-y-2 text-sm">'
        '<div><span class="text-mute">Document type</span><div class="font-semibold text-primary">%s</div></div>'
        '<div><span class="text-mute">Issue date</span><div class="font-semibold text-primary">%s</div></div>'
        '<div><span class="text-mute">Property</span><div class="font-semibold text-primary">%s</div></div>'
        '%s'
        '</div>'
    ) % (
        _esc("This page confirms the authenticity of a La Gala Construction compliance document."),
        _esc(s.get("doc_label", "Compliance document")),
        _esc(issue_str),
        _esc(prop.get("name", "") or prop.get("address", "") or "—"),
        ('<div><span class="text-mute">PE seal holder</span><div class="font-semibold text-primary">%s%s</div></div>' % (
            _esc(pe.get("name", "")), (" &middot; FL PE #" + _esc(pe.get("license", ""))) if pe.get("license") else ""
        )) if pe.get("name") else "",
    )
    return VERIFY_PAGE_TMPL.format(body=body)


@app.get("/verify/property/<token>")
def verify_property_page(token):
    """PUBLIC HTML page — building-level Certificate of Compliance verification."""
    token = (token or "")[:120]
    raw, configured = _kv_cmd(["GET", VERIFY_PROP_PREFIX + token])
    if not configured or not raw:
        body = '<span class="ms text-6xl text-mute">search_off</span><h1 class="text-2xl font-extrabold text-primary mt-3">Certificate not found</h1><p class="text-mute mt-2">This verification link is invalid or has expired.</p>'
        return VERIFY_PAGE_TMPL.format(body=body), 404
    try:
        s = json.loads(raw)
    except Exception:
        s = {}
    prop = s.get("property", {}) or {}
    body = _verify_status_badge(s.get("status")) + (
        '<p class="text-mute mt-2">Building-level walking-working surfaces compliance certificate.</p>'
        '<div class="bg-white rounded-xl border border-line p-5 mt-6 text-left space-y-2 text-sm">'
        '<div><span class="text-mute">Property</span><div class="font-semibold text-primary">%s</div></div>'
        '<div><span class="text-mute">Address</span><div class="font-semibold text-primary">%s</div></div>'
        '<div><span class="text-mute">Compliant through</span><div class="font-semibold text-primary">%s</div></div>'
        '<div><span class="text-mute">Last inspection</span><div class="font-semibold text-primary">%s</div></div>'
        '</div>'
    ) % (
        _esc(prop.get("name", "") or "—"),
        _esc(prop.get("address", "") or "—"),
        _esc(s.get("compliant_through", "") or "—"),
        _esc(s.get("last_inspection_date", "") or "—"),
    )
    return VERIFY_PAGE_TMPL.format(body=body)


# ==========================================================================
# Paid-invoice receipts (reportlab, on the fly)
# ==========================================================================
def doc_receipt(inv):
    """One-page payment receipt for a paid invoice. Not tied to an inspection
    record, so it uses its own minimal header instead of _dheader()."""
    from datetime import datetime, timezone
    st = _dstyles(); buf, doc = _dnew("Payment Receipt"); story = []
    story.append(Paragraph("LA GALA CONSTRUCTION", st["wordmark"]))
    story.append(Paragraph("Tilt Patchers, Inc. · CGC059211", st["doctype"]))
    story.append(Paragraph("Payment Receipt", st["h1"]))
    rule = Table([[""]], colWidths=[7.1 * inch]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.3, GOLD)]))
    story.append(Spacer(1, 3)); story.append(rule); story.append(Spacer(1, 10))

    amt = "$" + "{:,.2f}".format((inv.get("amount_cents") or 0) / 100.0)
    paid_ts = inv.get("paid_ts") or inv.get("created_ts")
    paid_str = datetime.fromtimestamp(paid_ts / 1000, tz=timezone.utc).strftime("%B %d, %Y") if paid_ts else "—"

    def kv(k, v): return [Paragraph(k, st["meta"]), Paragraph(_esc(v or "—"), st["metab"])]
    rows = [
        kv("Receipt #", inv.get("id", "")) + kv("Date paid", paid_str),
        kv("Billed to", inv.get("client_name") or inv.get("client_email", "")) + kv("Client email", inv.get("client_email", "")),
        kv("Property", inv.get("property", "")) + kv("Amount paid", amt),
    ]
    t = Table(rows, colWidths=[0.95 * inch, 2.55 * inch, 0.95 * inch, 2.65 * inch])
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 10))

    story.append(Paragraph("Description", st["sect"]))
    story.append(Paragraph(_esc(inv.get("description") or "Services rendered"), st["body"]))
    story.append(Spacer(1, 14))

    rows2 = [[Paragraph("Description", st["th"]), Paragraph("Amount", st["thc"])],
             [Paragraph(_esc(inv.get("description") or "Services rendered"), st["td"]), Paragraph(amt, st["tdr"])],
             [Paragraph("<b>Total paid</b>", st["td"]), Paragraph("<b>" + amt + "</b>", st["tdr"])]]
    t2 = Table(rows2, colWidths=[5.1 * inch, 2.0 * inch])
    t2.setStyle(_dtable_style())
    t2.setStyle(TableStyle([("LINEABOVE", (0, 2), (-1, 2), 1, NAVY), ("BACKGROUND", (0, 2), (-1, 2), CREAM)]))
    story.append(t2); story.append(Spacer(1, 16))

    story.append(Paragraph("This receipt confirms payment in full for the amount and description above. "
                            "Questions about this invoice? Call (561) 475-8615 or email danny@lagalacon.com.", st["disc"]))
    return _dfinish(buf, doc, story)


@app.get("/api/portal/invoice/<iid>/receipt")
def portal_invoice_receipt(iid):
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"error": "sign in required"}), 401
    inv = _inv_get(iid)
    if not inv or (inv.get("client_email") or "").lower() != s.get("email", "").lower():
        return jsonify({"error": "not found"}), 404
    if not _RL:
        return jsonify({"error": "pdf engine unavailable"}), 503
    if inv.get("status") != "paid":
        return jsonify({"error": "invoice is not marked paid"}), 400
    try:
        pdf = doc_receipt(inv)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_Receipt_%s.pdf"' % iid[:10]
    return resp


# ==========================================================================
# One-click board-ready compliance packet — cover sheet (reportlab)
# ==========================================================================
def _compliance_status(insp):
    """Best-effort roll-up of current compliance status/expiration for the
    cover sheet, from whatever the inspection record already carries."""
    findings = insp.get("findings") or []
    defects = [f for f in findings if (f.get("result") or "").lower() == "def"]
    status = insp.get("status", "draft")
    label = {"draft": "In progress", "field": "Field work in progress",
             "complete": "Inspection complete", "sealed": "Sealed / certified",
             "accepted": "Corrective proposal accepted"}.get(status, status.title())
    return {
        "label": label,
        "defect_count": len(defects),
        "recert_due": (insp.get("pe") or {}).get("recert_due", "") or "Per FL 10-year anchorage re-test cycle",
    }


def doc_board_cover(insp):
    from datetime import datetime, timezone
    st = _dstyles(); buf, doc = _dnew("Board-Ready Compliance Packet — Cover Sheet"); story = []
    _dheader(story, st, "Prepared for the Board / HOA", "Compliance Packet — Cover Sheet", insp)

    cs = _compliance_status(insp)
    accept = insp.get("acceptance") or {}
    story.append(Paragraph("Compliance status summary", st["sect"]))
    def kv(k, v): return [Paragraph(k, st["meta"]), Paragraph(_esc(v or "—"), st["metab"])]
    rows = [
        kv("Current status", cs["label"]) + kv("Open deficiencies", str(cs["defect_count"])),
        kv("Recertification", cs["recert_due"]) + kv("Report generated", datetime.now(timezone.utc).strftime("%B %d, %Y")),
    ]
    if accept.get("name_typed"):
        ts = accept.get("ts")
        when = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%B %d, %Y") if ts else ""
        rows.append(kv("Proposal accepted by", accept.get("name_typed", "") + (("  ·  " + when) if when else "")))
    t = Table(rows, colWidths=[1.1 * inch, 2.4 * inch, 1.1 * inch, 2.4 * inch])
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 10))

    story.append(Paragraph("What's included in this packet", st["sect"]))
    included = []
    for kind in ("report", "checklist", "cert", "proposal"):
        included.append("• " + DOC_LABEL.get(kind, kind.title()))
    story.append(Paragraph("<br/>".join(included) if included else "No documents available yet.", st["body"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("This cover sheet summarizes the current compliance cycle for the property above. "
                            "The individual documents listed are downloaded separately from the client portal and "
                            "should be assembled behind this cover sheet for board presentation.", st["key"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Prepared by La Gala Construction / Tilt Patchers, Inc. · CGC059211 · in partnership with "
                            "a FL State Certified Engineer. Engineering inspections and certifications are performed "
                            "and sealed by an independent, licensed Florida professional engineer.", st["disc"]))
    return _dfinish(buf, doc, story)


# ---- inspection storage (KV) ----
def _insp_index():
    raw, configured = _kv_cmd(["GET", "wws:insp_index"])
    if not configured:
        return None
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def _insp_get(iid):
    raw, configured = _kv_cmd(["GET", "wws:insp:" + iid])
    if not configured or not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _insp_save(insp):
    insp["updated_ts"] = _now_ms()
    _, configured = _kv_cmd(["SET", "wws:insp:" + insp["id"], json.dumps(insp)])
    if not configured:
        return False
    idx = _insp_index() or []
    if insp["id"] not in idx:
        idx.insert(0, insp["id"])
        _kv_cmd(["SET", "wws:insp_index", json.dumps(idx)])
    return True


def _find_lead(lid):
    for l in (_load_leads() or []):
        if l.get("id") == lid:
            return l
    return None


@app.post("/api/admin/inspection")
def insp_create():
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    b = request.get_json(force=True, silent=True) or {}
    iid = _gen_id()
    prop = b.get("property") or {}
    client = b.get("client") or {}
    lead = _find_lead(b.get("lead_id", "")) if b.get("lead_id") else None
    if lead:
        client.setdefault("name", lead.get("name", "")); client.setdefault("company", lead.get("company", ""))
        client.setdefault("email", lead.get("email", "")); client.setdefault("phone", lead.get("phone", ""))
        prop.setdefault("name", lead.get("company", "") or lead.get("property", "")); prop.setdefault("address", lead.get("property", ""))
    s = read_session() or {}
    insp = {
        "id": iid, "created_ts": _now_ms(), "updated_ts": _now_ms(), "status": "draft",
        "property": prop, "client": client,
        "inspector": b.get("inspector") or {"name": s.get("name", ""), "license": "CGC059211"},
        "pe": b.get("pe") or {}, "findings": _seed_findings(),
        "summary": "", "recommendations": "", "corrective": [], "photos": [], "anchors": [], "davits": [], "visual_check": {}, "diagram": "", "sitecam": {},
        "source_lead_id": b.get("lead_id", ""), "source_request_id": b.get("request_id", ""),
        # recertification / compliance tracking (feature: recert countdown + compliance badge)
        "cert_date": b.get("cert_date", ""), "recert_months": b.get("recert_months") or 12,
        "compliance_status": "valid", "doc_tokens": {}, "property_verify_token": "",
    }
    if not _insp_save(insp):
        return jsonify({"ok": False, "error": "store not configured", "inspection": insp}), 200
    _log_activity("insp_create", f"Inspection {iid[:8]} for {insp.get('property',{}).get('address','')[:80]}")
    return jsonify({"ok": True, "inspection": insp})


@app.get("/api/admin/inspections")
def insp_list():
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    idx = _insp_index()
    if idx is None:
        return jsonify({"configured": False, "inspections": []})
    out = []
    for iid in idx:
        x = _insp_get(iid)
        if x:
            out.append({"id": x["id"], "created_ts": x.get("created_ts"), "status": x.get("status", "draft"),
                        "property": x.get("property", {}), "client": x.get("client", {}),
                        "defects": sum(1 for f in x.get("findings", []) if (f.get("result") or "").lower() == "def")})
    return jsonify({"configured": True, "inspections": out})


@app.get("/api/admin/inspection/<iid>")
def insp_one(iid):
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True, "inspection": x, "template": SUBPART_D, "sitecam_on": _sitecam_on()})


@app.post("/api/admin/inspection/<iid>")
def insp_update(iid):
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    b = request.get_json(force=True, silent=True) or {}
    prev_status = (x.get("status") or "draft").lower()
    for k in ("property", "client", "inspector", "pe", "findings", "corrective", "photos", "anchors", "davits",
              "visual_check", "diagram", "summary", "recommendations", "status", "sitecam",
              "cert_date", "recert_months", "compliance_status"):
        if k in b:
            x[k] = b[k]
    _insp_save(x)
    new_status = (x.get("status") or "draft").lower()
    if new_status in ("complete", "passed", "pass") and prev_status != new_status:
        refresh_property_compliance(x)
    if new_status == "complete" and prev_status != "complete":
        try:
            client_email = (x.get("client", {}) or {}).get("email", "")
            if client_email:
                _notify_client(
                    client_email, "Your inspection is complete — La Gala Construction",
                    "Your inspection is complete.",
                    "The walking-working-surfaces inspection for {} has been completed. "
                    "Your report and documentation are available in your client portal.".format(
                        x.get("property", {}).get("address", "") or "your property"),
                    cta_label="View documents",
                )
        except Exception:
            pass
    return jsonify({"ok": True, "inspection": x})


@app.get("/api/admin/inspection/<iid>/doc/<kind>")
def insp_doc(iid, kind):
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    if not _RL:
        return jsonify({"error": "pdf engine unavailable"}), 503
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    fn = DOC_BUILDERS.get(kind)
    if not fn:
        return jsonify({"error": "unknown doc"}), 400
    try:
        if kind == "compliance":
            refresh_property_compliance(x)
        else:
            x["_verify_url"] = _verify_url("document", _doc_token_for(x, kind))
        pdf = fn(x)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    base = (x.get("property", {}).get("name", "") or iid).replace(" ", "_")[:40]
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_WWS_%s_%s.pdf"' % (kind, base)
    # First-generation notification only (avoid re-emailing on every re-download/view).
    try:
        notified = x.get("docs_notified") or []
        if kind not in notified:
            client_email = (x.get("client", {}) or {}).get("email", "")
            DOC_LABEL = {"report": "inspection report", "checklist": "completed checklist",
                         "cert": "certification", "proposal": "proposal"}
            if client_email:
                sent = _notify_client(
                    client_email, "New document ready — La Gala Construction",
                    "A new document has been added to your file.",
                    "Your {} for {} is now available in your client portal.".format(
                        DOC_LABEL.get(kind, kind), x.get("property", {}).get("address", "") or "your property"),
                    cta_label="View in portal",
                )
                if sent:
                    notified.append(kind)
                    x["docs_notified"] = notified
                    x["last_doc"] = {"kind": kind, "label": DOC_LABEL.get(kind, kind), "ts": _now_ms()}
                    _insp_save(x)
    except Exception:
        pass
    return resp


# ---- SiteCam field-photo hook — read-only /api/ext/* contract (config-gated) ----
# Per-tenant isolation: the API key alone determines the SiteCam tenant server-side
# (no caller-supplied tenant). A WWS key only ever reaches the WWS tenant's data.
SITECAM_BASE = os.environ.get("SITECAM_BASE_URL", "").rstrip("/")
SITECAM_KEY = os.environ.get("SITECAM_API_KEY", "")


def _sitecam_on():
    return bool(SITECAM_BASE and SITECAM_KEY)


def _sitecam_headers():
    return {"x-api-key": SITECAM_KEY}


def _sitecam_get(path, params=None):
    r = requests.get(SITECAM_BASE + path, headers=_sitecam_headers(), params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _sitecam_search(q):
    data = _sitecam_get("/api/ext/projects", {"q": q})
    rows = data if isinstance(data, list) else (data.get("projects") or data.get("items") or [])
    out = []
    for p in rows:
        out.append({"id": p.get("id"), "name": p.get("name", ""), "address": p.get("address", ""),
                    "system": p.get("system", ""), "status": p.get("status", ""),
                    "crmJobId": p.get("crmJobId", ""), "photoCount": p.get("photoCount", 0)})
    return out


def _sitecam_fetch_photos(pid):
    data = _sitecam_get("/api/ext/projects/" + str(pid) + "/photos")
    raw = data.get("photos") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    out = []
    for p in (raw or []):
        desc = (p.get("description", "") or "").strip()
        d = desc.upper().replace(" ", "")
        anc = d if (d and len(d) <= 6 and ((d[0:1].isalpha() and d[1:].isdigit()) or d.isdigit())) else ""
        out.append({"url": p.get("url", ""), "thumbUrl": p.get("thumbUrl", ""),
                    "anchor": anc, "result": "",
                    "caption": p.get("description", ""), "gps": p.get("gps", ""),
                    "ts": p.get("capturedAt")})
    return out


def _sitecam_create(crm_job_id, name, address):
    r = requests.post(SITECAM_BASE + "/api/ext/projects", headers=_sitecam_headers(),
                      json={"name": name, "address": address, "crmJobId": crm_job_id}, timeout=20)
    r.raise_for_status()
    return r.json()


@app.get("/api/admin/sitecam/status")
def sitecam_status():
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"configured": _sitecam_on(), "base": SITECAM_BASE if _sitecam_on() else ""})


@app.get("/api/admin/inspection/<iid>/sitecam/search")
def sitecam_search_ep(iid):
    """Find SiteCam projects (read-only) to link to this inspection. Defaults the
    query to the inspection's property address/name."""
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    if not _sitecam_on():
        return jsonify({"ok": False, "configured": False, "results": [],
                        "message": "SiteCam isn't connected yet. Set SITECAM_BASE_URL + SITECAM_API_KEY once SiteCam is deployed."}), 200
    prop = x.get("property", {})
    q = (request.args.get("q") or prop.get("address") or prop.get("name") or "").strip()
    if not q:
        return jsonify({"ok": True, "configured": True, "results": [], "q": ""})
    try:
        return jsonify({"ok": True, "configured": True, "q": q, "results": _sitecam_search(q)})
    except Exception as e:
        return jsonify({"ok": False, "configured": True, "error": str(e), "results": []}), 502


@app.post("/api/admin/inspection/<iid>/sitecam/start")
def sitecam_start(iid):
    """One-click: create (idempotent on crmJobId) the SiteCam project for this
    inspection so field crews can shoot photos against it."""
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    if not _sitecam_on():
        return jsonify({"ok": False, "configured": False, "message": "SiteCam isn't connected yet."}), 200
    prop = x.get("property", {})
    name = prop.get("name") or prop.get("address") or ("WWS Inspection " + iid)
    try:
        data = _sitecam_create("wws-" + iid, name, prop.get("address", ""))
        pid = data.get("id")
        x["sitecam"] = {"projectId": pid, "name": data.get("name", name), "address": data.get("address", ""),
                        "crmJobId": data.get("crmJobId", "wws-" + iid),
                        "url": SITECAM_BASE + "/projects/" + str(pid), "linked_ts": _now_ms()}
        _insp_save(x)
        return jsonify({"ok": True, "configured": True, "sitecam": x["sitecam"]})
    except Exception as e:
        return jsonify({"ok": False, "configured": True, "error": str(e)}), 502


@app.post("/api/admin/inspection/<iid>/sitecam/link")
def sitecam_link(iid):
    """Link a chosen SiteCam project id to this inspection (so we can pull its photos)."""
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    if not _sitecam_on():
        return jsonify({"ok": False, "configured": False}), 200
    body = request.get_json(force=True, silent=True) or {}
    pid = body.get("projectId") or body.get("id")
    if not pid:
        return jsonify({"ok": False, "error": "projectId required"}), 400
    x["sitecam"] = {"projectId": pid, "name": body.get("name", ""), "address": body.get("address", ""),
                    "url": SITECAM_BASE + "/projects/" + str(pid), "linked_ts": _now_ms()}
    _insp_save(x)
    return jsonify({"ok": True, "configured": True, "sitecam": x["sitecam"]})


@app.post("/api/admin/inspection/<iid>/sitecam/pull")
def sitecam_pull(iid):
    """Pull the linked SiteCam project's photos into the inspection's photo log."""
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    sc = x.get("sitecam", {})
    if not _sitecam_on() or not sc.get("projectId"):
        return jsonify({"ok": False, "configured": _sitecam_on(), "photos": []}), 200
    try:
        photos = _sitecam_fetch_photos(sc["projectId"])
        x["photos"] = photos
        _insp_save(x)
        return jsonify({"ok": True, "configured": True, "photos": photos})
    except Exception as e:
        return jsonify({"ok": False, "configured": True, "error": str(e)}), 502


# ==========================================================================
# Portfolio compliance score + multi-year plan CTA
# ==========================================================================
# Simple compliance model derived from existing inspection records (no
# separate countdown/recert data model exists yet in this worktree):
#   - "compliant" property = an inspection whose status is complete/sealed
#     AND has zero unresolved deficiencies (findings with result == "def").
#   - anything else (draft/field status, or any open "def" finding) counts
#     as not-yet-compliant.
# This is intentionally simple v1 scoring, not a recert-date engine.
def _compliance_score(email):
    props = {}
    for iid in (_insp_index() or []):
        x = _insp_get(iid)
        if not x or not _client_owns(x, email):
            continue
        p = x.get("property", {})
        key = (p.get("address") or p.get("name") or x["id"]).strip().lower()
        defects = sum(1 for f in (x.get("findings") or []) if (f.get("result") or "").lower() == "def")
        compliant = (x.get("status") in ("complete", "sealed")) and defects == 0
        prev = props.get(key)
        if prev is None or x.get("updated_ts", 0) >= prev.get("_ts", 0):
            props[key] = {"name": p.get("name") or p.get("address") or "Property", "address": p.get("address", ""),
                          "compliant": compliant, "status": x.get("status", "draft"), "defects": defects,
                          "_ts": x.get("updated_ts", 0)}
    total = len(props)
    compliant_n = sum(1 for v in props.values() if v["compliant"])
    return {"total": total, "compliant": compliant_n,
            "properties": [{"name": v["name"], "address": v["address"], "compliant": v["compliant"],
                            "status": v["status"], "defects": v["defects"]} for v in props.values()]}


@app.get("/api/portal/compliance_score")
def portal_compliance_score():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False}), 200
    score = _compliance_score(s["email"])
    return jsonify({"authed": True, "email": s["email"], "score": score})


# ==========================================================================
# Referral credit ledger
# ==========================================================================
WWS_REFCODE_KEY = "wws:refcodes"        # JSON map { email: code }
WWS_REFCODE_REV_KEY = "wws:refcodes_rev"  # JSON map { code: email }
WWS_REFCREDIT_KEY = "wws:ref_credits"   # JSON map { email: {balance, referred:[emails/ids], updated} }


def _ref_code_for(email):
    email = (email or "").lower().strip()
    if not email:
        return ""
    raw, configured = _kv_cmd(["GET", WWS_REFCODE_KEY])
    if not configured:
        # degrade to a deterministic (non-persisted) code so the UI still works
        return (email.split("@")[0][:10] + "-" + hashlib.sha256(email.encode()).hexdigest()[:6]).upper()
    try:
        m = json.loads(raw) if raw else {}
    except Exception:
        m = {}
    code = m.get(email)
    if not code:
        code = (email.split("@")[0][:10] + "-" + hashlib.sha256(email.encode()).hexdigest()[:6]).upper()
        m[email] = code
        _kv_cmd(["SET", WWS_REFCODE_KEY, json.dumps(m)])
        rev_raw, _ = _kv_cmd(["GET", WWS_REFCODE_REV_KEY])
        try:
            rev = json.loads(rev_raw) if rev_raw else {}
        except Exception:
            rev = {}
        rev[code] = email
        _kv_cmd(["SET", WWS_REFCODE_REV_KEY, json.dumps(rev)])
    return code


def _ref_email_for_code(code):
    code = (code or "").strip().upper()
    if not code:
        return ""
    raw, configured = _kv_cmd(["GET", WWS_REFCODE_REV_KEY])
    if not configured or not raw:
        return ""
    try:
        rev = json.loads(raw)
    except Exception:
        rev = {}
    return rev.get(code, "")


def _ref_credit_get(email):
    email = (email or "").lower().strip()
    raw, configured = _kv_cmd(["GET", WWS_REFCREDIT_KEY])
    if not configured:
        return {"balance": 0, "referred": []}
    try:
        m = json.loads(raw) if raw else {}
    except Exception:
        m = {}
    return m.get(email, {"balance": 0, "referred": []})


def _ref_credit_add_referral(referrer_email, lead_id):
    """Tag a new lead as referred by referrer_email. Does not touch balance —
    admin manually adjusts credit (v1 keeps this visible-only)."""
    referrer_email = (referrer_email or "").lower().strip()
    if not referrer_email:
        return
    raw, configured = _kv_cmd(["GET", WWS_REFCREDIT_KEY])
    if not configured:
        return
    try:
        m = json.loads(raw) if raw else {}
    except Exception:
        m = {}
    rec = m.get(referrer_email, {"balance": 0, "referred": []})
    if lead_id and lead_id not in rec["referred"]:
        rec["referred"].append(lead_id)
    m[referrer_email] = rec
    _kv_cmd(["SET", WWS_REFCREDIT_KEY, json.dumps(m)])


@app.get("/api/portal/referral")
def portal_referral():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False}), 200
    email = s["email"]
    code = _ref_code_for(email)
    credit = _ref_credit_get(email)
    share_url = base_url() + "/wwslgc?ref=" + requests.utils.quote(code)
    return jsonify({"authed": True, "email": email, "code": code, "link": share_url,
                    "referral_count": len(credit.get("referred", [])), "credit_balance": credit.get("balance", 0)})


@app.post("/api/admin/referral/adjust")
def admin_referral_adjust():
    """Admin manually adjusts a client's referral credit balance (v1: visible-only,
    never auto-applied to invoices)."""
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "email required"}), 400
    try:
        delta = float(b.get("delta") or 0)
    except Exception:
        delta = 0
    raw, configured = _kv_cmd(["GET", WWS_REFCREDIT_KEY])
    if not configured:
        return jsonify({"ok": False, "error": "store not configured"}), 200
    try:
        m = json.loads(raw) if raw else {}
    except Exception:
        m = {}
    rec = m.get(email, {"balance": 0, "referred": []})
    rec["balance"] = round(rec.get("balance", 0) + delta, 2)
    rec["updated"] = _now_ms()
    m[email] = rec
    _kv_cmd(["SET", WWS_REFCREDIT_KEY, json.dumps(m)])
    _log_activity("referral_adjust", f"{email}: {'+' if delta>=0 else ''}{delta} → balance {rec['balance']}")
    return jsonify({"ok": True, "email": email, "balance": rec["balance"]})


@app.get("/api/admin/referral/<email>")
def admin_referral_lookup(email):
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    email = (email or "").strip().lower()
    credit = _ref_credit_get(email)
    return jsonify({"ok": True, "email": email, "code": _ref_code_for(email), "credit": credit})


# ==========================================================================
# In-portal messaging thread per inspection
# ==========================================================================
def _msg_key(iid):
    return "wws:insp_msgs:" + iid


def _msg_list(iid):
    raw, configured = _kv_cmd(["LRANGE", _msg_key(iid), 0, -1])
    if not configured:
        return []
    out = []
    for item in (raw or []):
        try:
            out.append(json.loads(item))
        except Exception:
            pass
    return out


def _msg_append(iid, author, author_name, text):
    entry = {"ts": _now_ms(), "author": author, "author_name": author_name[:120], "text": text[:3000]}
    _kv_cmd(["RPUSH", _msg_key(iid), json.dumps(entry)])
    return entry


@app.get("/api/portal/inspection/<iid>/messages")
def portal_inspection_messages_get(iid):
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "messages": []}), 200
    x = _insp_get(iid)
    if not x or not _client_owns(x, s.get("email", "")):
        return jsonify({"error": "not found"}), 404
    return jsonify({"authed": True, "messages": _msg_list(iid)})


@app.post("/api/portal/inspection/<iid>/message")
def portal_inspection_message_post(iid):
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
    x = _insp_get(iid)
    if not x or not _client_owns(x, s.get("email", "")):
        return jsonify({"ok": False, "error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "message required"}), 400
    entry = _msg_append(iid, "client", s.get("name") or s.get("email", ""), text)
    prop = x.get("property", {})
    _notify("WWS portal message — " + (prop.get("name") or prop.get("address") or iid),
            "{} <{}> replied on their inspection thread:\n\n{}\n\nOpen: {}/admin/inspection?id={}".format(
                s.get("name", ""), s.get("email", ""), text, base_url(), iid))
    return jsonify({"ok": True, "message": entry})


@app.get("/api/admin/inspection/<iid>/messages")
def admin_inspection_messages_get(iid):
    if not _is_admin():
        return jsonify({"error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True, "messages": _msg_list(iid)})


@app.post("/api/admin/inspection/<iid>/message")
def admin_inspection_message_post(iid):
    if not _is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    x = _insp_get(iid)
    if not x:
        return jsonify({"ok": False, "error": "not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "message required"}), 400
    entry = _msg_append(iid, "admin", _admin_name(), text)
    client = x.get("client", {})
    client_email = client.get("email", "")
    prop = x.get("property", {})
    if client_email:
        subj = "Update on your inspection — " + (prop.get("name") or prop.get("address") or "La Gala WWS")
        html = ("<p>Hi {},</p><p>{} left a new message on your inspection thread:</p>"
                "<blockquote style='border-left:3px solid #c9a227;padding-left:12px;color:#1f2733'>{}</blockquote>"
                "<p><a href='{}/portal'>Open your portal</a></p><p>— La Gala Construction</p>").format(
            _esc(client.get("name", "") or "there"), _esc(_admin_name()), _esc(text), base_url())
        try:
            _resend_send({"from": RESEND_FROM, "to": [client_email], "subject": subj, "html": html})
        except Exception:
            pass
    _log_activity("insp_message", f"Reply on inspection {iid[:8]}: {text[:80]}")
    return jsonify({"ok": True, "message": entry})


@app.get("/api/logout")
def logout():
    resp = make_response(redirect("/wwslgc"))
    clear_cookie(resp, SESSION_COOKIE)
    return resp


# ---- Microsoft sign-in ----
@app.get("/api/login")
def login_ms():
    flow = msal_app().initiate_auth_code_flow(MS_SCOPES, redirect_uri=ms_redirect_uri())
    resp = make_response(redirect(flow["auth_uri"]))
    set_temp(resp, FLOW_COOKIE, flow)
    set_temp(resp, "cc_next", _safe_next())
    return resp


@app.get("/api/auth/callback")
def callback_ms():
    flow = read_temp(FLOW_COOKIE)
    if not flow:
        return _err_page("Sign-in expired. Please try again.")
    result = msal_app().acquire_token_by_auth_code_flow(flow, dict(request.args))
    if "access_token" not in result:
        return _err_page("Sign-in failed: " + result.get("error_description", result.get("error", "unknown")))
    claims = result.get("id_token_claims", {})
    email = (claims.get("preferred_username") or claims.get("email") or "").lower()
    if ALLOWED_DOMAIN and not email.endswith("@" + ALLOWED_DOMAIN):
        return _err_page("Microsoft sign-in is restricted to @{} accounts.".format(ALLOWED_DOMAIN))
    resp = make_response(redirect(_safe_path(read_temp("cc_next"))))
    write_session(resp, {"provider": "microsoft", "access_token": result["access_token"],
                         "email": email, "name": claims.get("name", email)})
    clear_cookie(resp, FLOW_COOKIE)
    clear_cookie(resp, "cc_next")
    return resp


# ---- Google sign-in ----
@app.get("/api/login/google")
def login_google():
    cid = os.environ.get("GOOGLE_CLIENT_ID")
    if not cid:
        return _err_page("Google sign-in isn't configured yet (GOOGLE_CLIENT_ID missing).")
    state = secrets.token_urlsafe(24)
    # identity-only sign-in (admin dashboard / client portal) doesn't need Gmail
    basic = request.args.get("basic")
    scopes = ["openid", "email", "profile"] if basic else GOOGLE_SCOPES
    params = {
        "client_id": cid,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "online" if basic else "offline",
        "include_granted_scopes": "true",
        "prompt": "select_account" if basic else "consent",
        "state": state,
    }
    url = GOOGLE_AUTH + "?" + "&".join("{}={}".format(k, requests.utils.quote(v, safe="")) for k, v in params.items())
    resp = make_response(redirect(url))
    set_temp(resp, GSTATE_COOKIE, {"state": state, "next": _safe_next()})
    return resp


@app.get("/api/auth/google/callback")
def callback_google():
    saved = read_temp(GSTATE_COOKIE)
    if not saved or request.args.get("state") != saved.get("state"):
        return _err_page("Google sign-in could not be verified. Please try again.")
    if request.args.get("error"):
        return _err_page("Google sign-in failed: " + request.args.get("error"))
    code = request.args.get("code")
    try:
        tok = requests.post(GOOGLE_TOKEN, data={
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": google_redirect_uri(),
            "grant_type": "authorization_code",
        }, timeout=30).json()
    except requests.RequestException as e:
        return _err_page("Google token exchange failed: " + str(e))
    if "access_token" not in tok:
        return _err_page("Google sign-in failed: " + tok.get("error_description", tok.get("error", "unknown")))
    access = tok["access_token"]
    email, name = "", ""
    try:
        info = requests.get(GOOGLE_USERINFO, headers={"Authorization": "Bearer " + access}, timeout=20).json()
        email = (info.get("email") or "").lower()
        name = info.get("name", email)
    except requests.RequestException:
        pass
    resp = make_response(redirect(_safe_path(saved.get("next"))))
    write_session(resp, {"provider": "google", "access_token": access, "email": email, "name": name})
    clear_cookie(resp, GSTATE_COOKIE)
    return resp


# --------------------------------------------------------------------------
# Sending
# --------------------------------------------------------------------------
@app.post("/api/send")
def send():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"ok": False, "status": "not connected"}), 401

    body = request.get_json(force=True, silent=True) or {}
    mode = body.get("mode", "draft")               # draft | send | test
    rcpt = body.get("recipient", {})
    to_email = (rcpt.get("email") or "").strip()
    if mode == "test":
        to_email = s.get("email")
    if not to_email:
        return jsonify({"ok": False, "status": "no recipient"}), 400

    subject = rcpt.get("subject", "")
    html = _text_to_html(rcpt.get("body", ""))
    attachments = _fetch_attachments(body.get("attachments", []))

    try:
        if s.get("provider") == "google":
            ok, status = _gmail_send(s["access_token"], to_email, subject, html, attachments, mode)
        else:
            ok, status = _graph_send(s["access_token"], to_email, subject, html, attachments, mode)
        return jsonify({"ok": ok, "status": status, "email": to_email}), (200 if ok else 502)
    except requests.RequestException as e:
        return jsonify({"ok": False, "status": "network error: " + str(e), "email": to_email}), 502


def _graph_send(token, to_email, subject, html, attachments, mode):
    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
    }
    if attachments:
        message["attachments"] = [{
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name, "contentBytes": base64.b64encode(data).decode(),
        } for name, data in attachments]
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if mode == "send":
        r = requests.post(GRAPH + "/me/sendMail", headers=headers,
                          json={"message": message, "saveToSentItems": True}, timeout=30)
        return (r.status_code in (200, 202), "sent" if r.status_code in (200, 202) else _err(r))
    r = requests.post(GRAPH + "/me/messages", headers=headers, json=message, timeout=30)
    return (r.status_code in (200, 201), "draft created" if r.status_code in (200, 201) else _err(r))


def _gmail_send(token, to_email, subject, html, attachments, mode):
    raw = _build_mime(to_email, subject, html, attachments)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if mode == "send":
        r = requests.post(GMAIL_API + "/messages/send", headers=headers, json={"raw": raw}, timeout=30)
        return (r.status_code in (200, 202), "sent" if r.status_code in (200, 202) else _err(r))
    r = requests.post(GMAIL_API + "/drafts", headers=headers, json={"message": {"raw": raw}}, timeout=30)
    return (r.status_code in (200, 201), "draft created" if r.status_code in (200, 201) else _err(r))


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _text_to_html(text):
    from html import escape
    return escape(text or "").replace("\n", "<br>\n")


def _fetch_attachments(urls):
    """Fetch each (public) collateral URL -> list of (filename, bytes)."""
    out = []
    for u in urls or []:
        full = u if u.startswith("http") else base_url() + u
        try:
            r = requests.get(full, timeout=20)
            if r.status_code == 200 and r.content:
                out.append((full.rsplit("/", 1)[-1], r.content))
        except requests.RequestException:
            pass
    return out


def _build_mime(to_email, subject, html, attachments):
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(html, "html"))
        for name, data in attachments:
            part = MIMEApplication(data)
            part.add_header("Content-Disposition", "attachment", filename=name)
            msg.attach(part)
    else:
        msg = MIMEText(html, "html")
    msg["To"] = to_email
    msg["Subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def _err(r):
    try:
        j = r.json()
        return "API {}: {}".format(r.status_code, j.get("error", {}).get("message", str(j)[:200]))
    except ValueError:
        return "API {}: {}".format(r.status_code, r.text[:200])


def _err_page(msg):
    html = ("<!doctype html><meta charset=utf-8><title>WWSLGC sign-in</title>"
            "<body style='font-family:sans-serif;max-width:520px;margin:80px auto;color:#0B2340'>"
            "<h2>Sign-in problem</h2><p>{}</p>"
            "<p><a href='/wwslgc'>← Back to the portal</a></p></body>").format(msg)
    return make_response(html, 400)


# ─────────────────────────────────────────────────────────────────────────
# Casa Del Monte portal — file uploads via email attachment
#
# Each portal upload becomes a single Resend email with the file attached.
# Client is in `to`, staff in `cc` — Gmail/Outlook thread is the file record.
# No persistent file storage, no Blob bucket to maintain.
#
# Env vars (set in Vercel project settings):
#   RESEND_API_KEY          — from https://resend.com  (free, 100/day)
#   RESEND_FROM_EMAIL       — verified sender, e.g. updates@collaborativeconceptsfl.com
#   PORTAL_BASE_URL         — public URL, e.g. https://casadelmonte.collaborativeconceptsfl.com
#   PORTAL_STAFF_EMAILS     — comma-sep staff emails CC'd on every upload
# ─────────────────────────────────────────────────────────────────────────

import base64
import re
from datetime import datetime, timezone

RESEND_KEY  = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM_EMAIL", "updates@collaborativeconceptsfl.com")
PORTAL_BASE = os.environ.get("PORTAL_BASE_URL", "https://casadelmonte.collaborativeconceptsfl.com")

# Staff CC'd on every upload. Override via PORTAL_STAFF_EMAILS env.
_STAFF_DEFAULT = (
    "danny@lagalacon.com,"
    "keith@lagalacon.com,"
    "kailer.lagala824@gmail.com,"
    "natasharich1989@gmail.com,"
    "alex@lagalacon.com"
)
PORTAL_STAFF = [
    e.strip() for e in os.environ.get("PORTAL_STAFF_EMAILS", _STAFF_DEFAULT).split(",")
    if e.strip()
]

# Resend attachment size cap (Resend allows 40MB total per request)
MAX_FILE_BYTES = 40 * 1024 * 1024


def _safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120] or "file"


def _resend_send(payload):
    """Generic Resend send. Returns (ok, info)."""
    if not RESEND_KEY:
        return False, "RESEND_API_KEY not configured"
    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "authorization": "Bearer " + RESEND_KEY,
            "content-type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if r.ok:
        return True, r.json().get("id", "")
    return False, r.text[:300]


def _upload_email_html(uploaded_by, uploaded_role, category, lot, owner_name, filename, internal_only, client_addressed):
    """Branded HTML body for the upload-attachment email."""
    greeting = "Hi {}, ".format(owner_name) if client_addressed else "Team,"
    intro = (
        "<strong>{u}</strong> ({r}) just added a new document to your Casa Del Monte file:".format(
            u=uploaded_by, r=uploaded_role or "Staff"
        )
        if client_addressed
        else "<strong>{u}</strong> ({r}) uploaded a new document — file attached.".format(
            u=uploaded_by, r=uploaded_role or "Staff"
        )
    )
    internal_banner = (
        "<div style='background:#fee;border-left:3px solid #c0392b;padding:8px 12px;margin-bottom:14px;font-size:12px;color:#7a1a1a'>"
        "🔒 INTERNAL ONLY — not shared with client</div>"
        if internal_only
        else ""
    )
    cta = (
        "<p><a href='{p}' style='background:#3d7eaa;color:#fff;text-decoration:none;padding:12px 24px;border-radius:6px;display:inline-block;font-weight:600'>Open the portal</a></p>".format(
            p=PORTAL_BASE
        )
        if client_addressed
        else ""
    )
    return (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto'>"
        "<div style='background:#1a2332;padding:24px 32px'>"
        "<h1 style='color:#fff;font-size:20px;margin:0'>LA GALA CONSTRUCTION</h1>"
        "<p style='color:#3d7eaa;font-size:12px;margin:4px 0 0;letter-spacing:1px;text-transform:uppercase'>Casa Del Monte · File Update · Lot {lot}</p>"
        "</div>"
        "<div style='padding:28px 32px;color:#1a2332;font-size:14px;line-height:1.6;background:#fff'>"
        "{banner}"
        "<p>{greet}</p>"
        "<p>{intro}</p>"
        "<div style='background:#f0f9f4;border:1px solid #1a6b40;border-radius:8px;padding:16px 20px;margin:0 0 18px'>"
        "<p style='margin:0;font-size:12px;color:#1a6b40;letter-spacing:1px;text-transform:uppercase;font-weight:700'>📎 Attached</p>"
        "<p style='margin:6px 0 0;font-size:18px;color:#1a2332;font-weight:700'>{category}</p>"
        "<p style='margin:6px 0 0;font-size:13px;color:#444'>{filename}</p>"
        "<p style='margin:6px 0 0;font-size:12px;color:#666'>Case file · Lot {lot}</p>"
        "</div>"
        "{cta}"
        "<p style='font-size:12px;color:#666;margin-top:24px'>Questions? Call Daniel at (561) 475-8615.</p>"
        "<p style='margin:24px 0 4px'>— La Gala Construction</p>"
        "<p style='margin:0;color:#666;font-size:12px'>CGC 059211 · Licensed &amp; Insured</p>"
        "</div></div>"
    ).format(
        lot=lot, banner=internal_banner, greet=greeting, intro=intro,
        category=category, filename=filename, cta=cta,
    )


# CORS for the casadelmonte subdomain calling /api/portal/* cross-origin
_PORTAL_CORS_ORIGINS = {
    "https://casadelmonte.collaborativeconceptsfl.com",
    "https://collaborativeconceptsfl.com",
    "https://www.collaborativeconceptsfl.com",
}


def _apply_portal_cors(resp):
    origin = request.headers.get("origin", "")
    if origin in _PORTAL_CORS_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"]      = origin
        resp.headers["Access-Control-Allow-Methods"]     = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"]     = "Content-Type"
        resp.headers["Access-Control-Max-Age"]           = "86400"
        resp.headers["Vary"]                             = "Origin"
    return resp


@app.route("/api/portal/<path:_>", methods=["OPTIONS"])
def portal_preflight(_):
    return _apply_portal_cors(make_response("", 204))


@app.after_request
def _portal_cors_after(resp):
    if request.path.startswith("/api/portal/"):
        return _apply_portal_cors(resp)
    return resp


@app.route("/api/portal/status", methods=["GET"])
def portal_status():
    """Quick check that env vars are wired up."""
    return _apply_portal_cors(jsonify({
        "mode":              "email-attachment",
        "resend_configured": bool(RESEND_KEY),
        "from_email":        RESEND_FROM if RESEND_KEY else None,
        "portal_base":       PORTAL_BASE,
        "staff_count":       len(PORTAL_STAFF),
        "max_file_mb":       MAX_FILE_BYTES // (1024 * 1024),
    }))


@app.route("/api/portal/upload", methods=["POST"])
def portal_upload():
    f = request.files.get("file")
    if f is None:
        return jsonify({"error": "no file"}), 400
    lot           = (request.form.get("lot") or "").strip()
    category      = (request.form.get("category") or "Other").strip()
    uploaded_by   = (request.form.get("uploaded_by") or "Staff").strip()
    uploaded_role = (request.form.get("uploaded_by_role") or "").strip()
    internal_only = request.form.get("internal_only") == "1"
    notify        = request.form.get("notify_client") == "1"
    client_email  = (request.form.get("client_email") or "").strip()
    client_owner  = (request.form.get("client_owner") or "there").strip()

    if not lot:
        return jsonify({"error": "lot required"}), 400

    file_bytes = f.read()
    if len(file_bytes) > MAX_FILE_BYTES:
        return jsonify({
            "error": "file too large ({:.1f} MB) — max {} MB per send".format(
                len(file_bytes) / (1024 * 1024), MAX_FILE_BYTES // (1024 * 1024)
            )
        }), 413
    if len(file_bytes) == 0:
        return jsonify({"error": "empty file"}), 400

    filename = _safe_name(f.filename or "document.bin")
    client_addressed = (notify and not internal_only and bool(client_email))

    # Recipients
    to_list = [client_email] if client_addressed else (PORTAL_STAFF[:1] or [RESEND_FROM])
    if client_addressed:
        cc_list = list(PORTAL_STAFF)
    else:
        cc_list = PORTAL_STAFF[1:] if len(PORTAL_STAFF) > 1 else []

    subject_prefix = "[INTERNAL] " if internal_only else ""
    subject = "{}Casa Del Monte · Lot {} · {} ({})".format(
        subject_prefix, lot, category, uploaded_by
    )

    html = _upload_email_html(
        uploaded_by, uploaded_role, category, lot, client_owner,
        filename, internal_only, client_addressed,
    )

    payload = {
        "from":    RESEND_FROM,
        "to":      to_list,
        "subject": subject,
        "html":    html,
        "attachments": [{
            "filename":     filename,
            "content":      base64.b64encode(file_bytes).decode(),
            "content_type": f.content_type or "application/octet-stream",
        }],
    }
    if cc_list:
        payload["cc"] = cc_list

    ok, info = _resend_send(payload)
    if not ok:
        return jsonify({"ok": False, "error": info}), 502

    return jsonify({
        "ok":              True,
        "email_sent":      True,
        "to":              to_list,
        "cc":              cc_list,
        "lot":             lot,
        "category":        category,
        "uploaded_by":     uploaded_by,
        "uploaded_by_role": uploaded_role,
        "internal_only":   internal_only,
        "client_addressed": client_addressed,
        "file_bytes":      len(file_bytes),
        "uploaded_at":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resend_id":       info,
    })


# ==========================================================================
# Candy's Cake Pops — public site endpoints (Sweet List + corporate quotes)
# Static site origin differs (Vercel deploy / local preview), so these reply
# with permissive CORS. Notifications ride the existing Resend pipeline.
# ==========================================================================
CANDYS_NOTIFY_EMAIL = os.environ.get("CANDYS_NOTIFY_EMAIL", WWS_NOTIFY_EMAIL)


def _candys_resp(payload, code=200):
    resp = jsonify(payload)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp, code


@app.route("/api/candys/<path:_>", methods=["OPTIONS"])
def candys_preflight(_):
    return _candys_resp({"ok": True})


@app.post("/api/candys/subscribe")
def candys_subscribe():
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip()[:200]
    if "@" not in email:
        return _candys_resp({"ok": False, "error": "valid email required"}, 400)
    _notify("[CANDYS] Sweet List signup — " + email,
            "New 10%-off signup on the Candy's Cake Pops site:\n\n"
            "Email: {}\nSource: {}\n\n"
            "Send the welcome + 10% code (manual until Square Marketing/Mailchimp "
            "automation is connected).".format(email, (b.get("source") or "site")[:120]))
    return _candys_resp({"ok": True})


@app.post("/api/candys/quote")
def candys_quote():
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip()[:200]
    if "@" not in email:
        return _candys_resp({"ok": False, "error": "valid email required"}, 400)
    lines = []
    for k, label in (("name", "Name"), ("company", "Company"), ("email", "Email"),
                     ("quantity", "Quantity"), ("event_date", "Event date"), ("notes", "Notes")):
        v = (b.get(k) or "").strip()
        if v:
            lines.append("{}: {}".format(label, v[:2000]))
    _notify("[CANDYS] Corporate quote request — " + ((b.get("company") or email)[:120]),
            "New corporate quote request from the Candy's site "
            "(promised response: one business day):\n\n" + "\n".join(lines))
    return _candys_resp({"ok": True})


# ==========================================================================
# Dev Agent hook — the admin dashboard widget posts fix/change requests here.
# Each request is emailed to the owner inbox tagged [DEV-AGENT]; a scheduled
# local Claude agent polls that tag and executes the work in the right repo.
# ==========================================================================
@app.post("/api/admin/dev-request")
def admin_dev_request():
    if not _is_admin():
        return jsonify({"ok": False, "error": "not authorized"}), 403
    b = request.get_json(force=True, silent=True) or {}
    req_text = (b.get("request") or "").strip()
    if len(req_text) < 5:
        return jsonify({"ok": False, "error": "describe the fix or change"}), 400
    project = (b.get("project") or "unspecified")[:80]
    priority = (b.get("priority") or "normal")[:20]
    rid = _gen_id()
    requester = (read_session() or {}).get("email", "unknown")
    _notify("[DEV-AGENT] {} — {}".format(project, req_text[:70]),
            "Dev request from the collaborative dashboard.\n\n"
            "ID: {rid}\nProject: {project}\nPriority: {priority}\n"
            "Requested by: {requester}\n\n"
            "REQUEST:\n{req}\n\n"
            "-- Routing: a scheduled local Claude dev agent polls Gmail for "
            "[DEV-AGENT] subjects, executes the change in the matching repo, "
            "and labels this thread dev-agent/done with a reply draft."
            .format(rid=rid, project=project, priority=priority,
                    requester=requester, req=req_text[:8000]))
    try:
        _kv_cmd(["RPUSH", "dev:requests", json.dumps(
            {"id": rid, "ts": _now_ms(), "project": project,
             "priority": priority, "by": requester, "request": req_text[:8000]})])
    except Exception:
        pass
    return jsonify({"ok": True, "id": rid})


# ==========================================================================
# Candy's Cake Pops — orders, contact, and client portal
# Orders are requests (no payment rails yet): customer submits, Candice
# confirms + invoices via Square/PayPal. Portal lets a client watch progress
# notes and their recurring plan. KV-backed with graceful degrade + DEMO.
# ==========================================================================
CANDYS_ORDERS_KEY = "candys:orders"  # Redis HASH: code -> JSON order
CANDYS_STAGES = ["proof", "approved", "baking", "decorating", "packed", "delivered"]
CANDYS_PORTAL_BASE = "https://candys-cake-pops.vercel.app/portal"

CANDYS_DEMO_ORDER = {
    "code": "DEMO",
    "client": {"name": "The Gab Group", "email": "events@example.com"},
    "item": "10 dozen custom logo cake pops + 4 dozen branded Oreos",
    "total": "$648.00",
    "status": "decorating",
    "created": "2026-06-01",
    "event_date": "2026-06-20",
    "recurring": {"active": True, "freq": "Quarterly", "amount": "$648.00",
                  "next": "2026-09-15", "method": "Invoiced via Square"},
    "notes": [
        {"ts": "2026-06-02", "by": "Candice", "text": "Proof sent! Check your email for the edible-print mock-up of your logo pops."},
        {"ts": "2026-06-04", "by": "You", "text": "Proof approved — the gold drizzle version. So excited!"},
        {"ts": "2026-06-10", "by": "Candice", "text": "Batch one is baked and dipped. Logo decals go on tomorrow morning.",
         "photo": "https://www.cakepops.com/cdn/shop/products/ArrowCorporateLogoCakePopsBrandingCandy_sthinner.jpg?width=500"},
    ],
}


def _candys_get_order(code):
    raw, configured = _kv_cmd(["HGET", CANDYS_ORDERS_KEY, code])
    if raw:
        try:
            return json.loads(raw), configured
        except Exception:
            return None, configured
    return None, configured


def _candys_put_order(order):
    return _kv_cmd(["HSET", CANDYS_ORDERS_KEY, order["code"], json.dumps(order)])


@app.post("/api/candys/contact")
def candys_contact():
    b = request.get_json(force=True, silent=True) or {}
    email = (b.get("email") or "").strip()[:200]
    msg = (b.get("message") or "").strip()[:5000]
    if "@" not in email or len(msg) < 3:
        return _candys_resp({"ok": False, "error": "email and message required"}, 400)
    _notify("[CANDYS] Contact — " + (b.get("name") or email)[:80],
            "Message from the Candy's site contact page:\n\n"
            "Name: {}\nEmail: {}\nPhone: {}\n\n{}".format(
                (b.get("name") or "")[:200], email, (b.get("phone") or "")[:60], msg))
    return _candys_resp({"ok": True})


@app.post("/api/candys/order")
def candys_order():
    """Order request — JSON, or multipart when a design/logo/photo rides along.
    The attachment is forwarded on the notification email via Resend."""
    if request.content_type and "multipart" in request.content_type:
        b = request.form.to_dict()
        f = request.files.get("design")
    else:
        b = request.get_json(force=True, silent=True) or {}
        f = None
    email = (b.get("email") or "").strip()[:200]
    if "@" not in email:
        return _candys_resp({"ok": False, "error": "valid email required"}, 400)

    rid = _gen_id()
    lines = ["Order request from the Candy's site (no payment taken — confirm and invoice via Square):", ""]
    for k, label in (("name", "Name"), ("email", "Email"), ("phone", "Phone"),
                     ("item", "Item"), ("qty", "Quantity"), ("flavors", "Flavors"),
                     ("colors", "Colors / theme"), ("date", "Needed by"), ("notes", "Notes")):
        v = (b.get(k) or "").strip()
        if v:
            lines.append("{}: {}".format(label, v[:2000]))
    lines.append("")
    lines.append("Request ID: " + rid)
    subject = "[CANDYS] Order request — " + ((b.get("item") or email)[:90])

    if f and f.filename:
        data = f.read()
        if len(data) > 8 * 1024 * 1024:
            return _candys_resp({"ok": False, "error": "file over 8MB — email it instead"}, 400)
        lines.append("Attached design file: " + f.filename)
        ok, info = _resend_send({
            "from": RESEND_FROM,
            "to": [CANDYS_NOTIFY_EMAIL],
            "subject": subject,
            "text": "\n".join(lines),
            "attachments": [{
                "filename": f.filename[:120],
                "content": base64.b64encode(data).decode(),
                "content_type": f.content_type or "application/octet-stream",
            }],
        })
        if not ok:
            _notify(subject, "\n".join(lines) + "\n\n(Attachment failed to send: {})".format(info))
    else:
        _notify(subject, "\n".join(lines))
    return _candys_resp({"ok": True, "id": rid})


@app.get("/api/candys/portal/<code>")
def candys_portal(code):
    code = (code or "").strip().upper()[:24]
    if code == "DEMO":
        return _candys_resp({"ok": True, "order": CANDYS_DEMO_ORDER, "demo": True})
    order, configured = _candys_get_order(code)
    if not configured:
        return _candys_resp({"ok": False, "error": "Portal storage isn't switched on yet — ask us for your status by email.", "storage": False}, 503)
    if not order:
        return _candys_resp({"ok": False, "error": "No order found for that code. Check the code on your confirmation email."}, 404)
    return _candys_resp({"ok": True, "order": order})


# ---- admin: manage Candy's orders (gated by WWS_ADMIN_EMAILS) ----
@app.get("/api/admin/candys/orders")
def admin_candys_orders():
    if not _is_admin():
        return jsonify({"ok": False, "error": "not authorized"}), 403
    raw, configured = _kv_cmd(["HGETALL", CANDYS_ORDERS_KEY])
    orders = []
    if raw:
        # Upstash returns a flat [field, value, field, value, ...] array
        for i in range(0, len(raw) - 1, 2):
            try:
                orders.append(json.loads(raw[i + 1]))
            except Exception:
                pass
    orders.sort(key=lambda o: o.get("updated", o.get("created", "")), reverse=True)
    return jsonify({"ok": True, "configured": configured, "orders": orders,
                    "stages": CANDYS_STAGES, "portal_base": CANDYS_PORTAL_BASE})


@app.post("/api/admin/candys/order")
def admin_candys_order():
    if not _is_admin():
        return jsonify({"ok": False, "error": "not authorized"}), 403
    b = request.get_json(force=True, silent=True) or {}
    code = (b.get("code") or "").strip().upper()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if code:
        order, configured = _candys_get_order(code)
        if not configured:
            return jsonify({"ok": False, "error": "storage not enabled (Vercel -> Storage -> Upstash Redis)"}), 503
        if not order:
            return jsonify({"ok": False, "error": "unknown code"}), 404
    else:
        order = {"code": "CCP-" + secrets.token_hex(2).upper(), "created": today, "notes": []}
    for k in ("item", "total", "event_date"):
        if b.get(k) is not None:
            order[k] = str(b[k])[:400]
    if b.get("client") is not None:
        c = b["client"] or {}
        order["client"] = {"name": str(c.get("name", ""))[:200], "email": str(c.get("email", ""))[:200]}
    if b.get("status") in CANDYS_STAGES:
        order["status"] = b["status"]
    order.setdefault("status", "proof")
    if b.get("recurring") is not None:
        r = b["recurring"] or {}
        order["recurring"] = {
            "active": bool(r.get("active")), "freq": str(r.get("freq", ""))[:40],
            "amount": str(r.get("amount", ""))[:40], "next": str(r.get("next", ""))[:40],
            "method": "Invoiced via Square",
        }
    note = (b.get("note") or "").strip()
    if note:
        order.setdefault("notes", []).append({
            "ts": today, "by": (read_session() or {}).get("email", "admin").split("@")[0],
            "text": note[:2000], "photo": (b.get("note_photo") or "")[:500] or None,
        })
    order["updated"] = today
    _, configured = _candys_put_order(order)
    if not configured:
        return jsonify({"ok": False, "error": "storage not enabled (Vercel -> Storage -> Upstash Redis)"}), 503
    return jsonify({"ok": True, "order": order, "portal_url": CANDYS_PORTAL_BASE + "?code=" + order["code"]})


# ---- Pop Squad: portal sharing game (friend visits fill the meter) ----
@app.route("/api/candys/squad/<code>", methods=["GET", "POST"])
def candys_squad(code):
    code = (code or "").strip().upper()[:24]
    key = "candys:squad"
    if request.method == "POST":
        val, configured = _kv_cmd(["HINCRBY", key, code, 1])
        if not configured:
            return _candys_resp({"ok": True, "count": 0, "storage": False})
        count = int(val or 0)
        if count in (1, 3):  # heads-up when a squad starts and when it completes
            _notify("[CANDYS] Pop Squad {} — order {}".format(
                "complete!" if count >= 3 else "started", code),
                "Order {} squad count is now {}. {}".format(
                    code, count,
                    "Squad complete — honor the POP SQUAD flavor-upgrade mention on their next order." if count >= 3 else ""))
        return _candys_resp({"ok": True, "count": count})
    raw, configured = _kv_cmd(["HGET", key, code])
    count = int(raw or 0)
    if code == "DEMO":
        count = max(count, 2)  # demo shows a nearly-complete squad
    return _candys_resp({"ok": True, "count": count, "storage": configured})


# ==================================================================
#  The Range House — food-delivery affiliate referral program
#  Guests order in from the apps they already use; the venue runs each
#  as a partner referral link and earns a bonus per order. Links route
#  through /api/food/go so every click is tracked in KV, then 302 to the
#  partner's affiliate URL. Admin view at /admin/food-referrals reads
#  /api/food/stats. Real affiliate URLs come from env vars (never
#  committed) with the public site as a safe fallback; bonus-per-order
#  values are editable estimates until each partner program is finalized.
# ==================================================================
FOODREF_CLICKS_KEY = "rangehouse:foodref:clicks"   # hash  app -> click count
FOODREF_LOG_KEY = "rangehouse:foodref:log"         # list  recent click events
FOODREF_LOG_MAX = 1000

FOOD_PARTNERS = {
    "doordash":  {"name": "DoorDash",  "url_env": "FOODREF_DOORDASH_URL",  "fallback": "https://www.doordash.com/",  "bonus": 5.0},
    "ubereats":  {"name": "Uber Eats", "url_env": "FOODREF_UBEREATS_URL",  "fallback": "https://www.ubereats.com/",  "bonus": 5.0},
    "grubhub":   {"name": "Grubhub",   "url_env": "FOODREF_GRUBHUB_URL",   "fallback": "https://www.grubhub.com/",   "bonus": 5.0},
    "instacart": {"name": "Instacart", "url_env": "FOODREF_INSTACART_URL", "fallback": "https://www.instacart.com/", "bonus": 8.0},
}


def _foodref_is_admin():
    s = read_session() or {}
    return bool(s.get("pin_admin")) or s.get("email", "").lower() in WWS_ADMIN_EMAILS


def _foodref_url(app_key):
    p = FOOD_PARTNERS[app_key]
    return (os.environ.get(p["url_env"]) or "").strip() or p["fallback"]


@app.get("/api/food/go")
def food_go():
    """Track a food-app click, then redirect to that partner's affiliate URL."""
    app_key = (request.args.get("app") or "").strip().lower()
    if app_key not in FOOD_PARTNERS:
        return redirect("/projects/the-range-house")
    try:
        _kv_cmd(["HINCRBY", FOODREF_CLICKS_KEY, app_key, 1])
        entry = json.dumps({
            "ts": _now_ms(),
            "app": app_key,
            "ref": (request.args.get("ref") or "")[:40],
            "ip": ((request.headers.get("x-forwarded-for") or "") + " " + (request.remote_addr or "")).strip()[:80],
            "ua": (request.headers.get("user-agent") or "")[:160],
        })
        _kv_cmd(["LPUSH", FOODREF_LOG_KEY, entry])
        _kv_cmd(["LTRIM", FOODREF_LOG_KEY, 0, FOODREF_LOG_MAX - 1])
    except Exception:
        pass
    return redirect(_foodref_url(app_key), code=302)


@app.get("/api/food/partners")
def food_partners():
    """Public: active partners so the page (or other clients) can render cards."""
    return jsonify({"partners": [
        {"key": k, "name": p["name"], "go": "/api/food/go?app=" + k}
        for k, p in FOOD_PARTNERS.items()
    ]})


@app.get("/api/food/stats")
def food_stats():
    """Admin-only: click counts + estimated referral bonus per partner."""
    if not _foodref_is_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    counts_raw, configured = _kv_cmd(["HGETALL", FOODREF_CLICKS_KEY])
    counts = {}
    if isinstance(counts_raw, list):
        for i in range(0, len(counts_raw) - 1, 2):
            try:
                counts[counts_raw[i]] = int(counts_raw[i + 1])
            except Exception:
                pass
    elif isinstance(counts_raw, dict):
        for k, v in counts_raw.items():
            try:
                counts[k] = int(v)
            except Exception:
                pass
    partners, total_clicks, total_bonus = [], 0, 0.0
    for key, p in FOOD_PARTNERS.items():
        c = counts.get(key, 0)
        total_clicks += c
        total_bonus += c * p["bonus"]
        partners.append({
            "key": key, "name": p["name"], "clicks": c,
            "bonus_per": p["bonus"], "bonus_total": round(c * p["bonus"], 2),
            "url_configured": bool((os.environ.get(p["url_env"]) or "").strip()),
        })
    log_raw, _ = _kv_cmd(["LRANGE", FOODREF_LOG_KEY, 0, 99])
    recent = []
    for r in (log_raw or []):
        try:
            recent.append(json.loads(r))
        except Exception:
            pass
    return jsonify({
        "ok": True, "configured": configured,
        "partners": partners,
        "total_clicks": total_clicks,
        "total_bonus_estimate": round(total_bonus, 2),
        "recent": recent,
    })


# ---------------------------------------------------------------------------
# SoFlo Permit Leads — building-permit lead engine (Martin / Palm Beach /
# Broward / Miami-Dade). Routes live in api/permits.py.
# ---------------------------------------------------------------------------
try:
    from permits import register_permits_routes
except ImportError:  # when imported as a package (local tests)
    from api.permits import register_permits_routes

register_permits_routes(app)

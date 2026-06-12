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
    return bool(s and s.get("email", "").lower() in WWS_ADMIN_EMAILS)


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
        if k and not k.startswith("_") and str(v).strip():
            clean[k[:60]] = str(v)[:2000]
    lead = {
        "id": _gen_id(), "ts": _now_ms(), "name": name, "email": email, "phone": phone,
        "company": company, "property": prop, "message": message, "fields": clean,
        "source": (g("source") or request.headers.get("Referer", ""))[:300],
        "ua": request.headers.get("User-Agent", "")[:300],
    }
    try:
        _, configured = _kv_cmd(["RPUSH", WWS_LEADS_KEY, json.dumps(lead)])
    except Exception:
        configured = False
    _notify("New WWS lead — " + (name or company or email or phone),
            "New Free Assessment request from the WWS site:\n\n" + _lead_summary(lead))

    if request.is_json:
        return jsonify({"ok": True, "stored": bool(configured)}), 200
    return redirect("/?submitted=1#assessment")


# ---- admin (gated by WWS_ADMIN_EMAILS) ----
@app.get("/api/admin/session")
def admin_session():
    s = read_session() or {}
    return jsonify({
        "authed": bool(s.get("email")),
        "email": s.get("email", ""),
        "name": s.get("name", ""),
        "admin": s.get("email", "").lower() in WWS_ADMIN_EMAILS,
    })


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


# ---- customer portal (any signed-in user) ----
@app.post("/api/portal/request")
def portal_request():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"ok": False, "error": "sign in required"}), 401
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


@app.get("/api/portal/requests")
def portal_requests():
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"authed": False, "requests": []})
    mine = [r for r in _load_requests() if r.get("email", "").lower() == s.get("email", "").lower()]
    return jsonify({"authed": True, "email": s.get("email"), "name": s.get("name", ""), "requests": mine})


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
    email = s.get("email", "")
    out = []
    for iid in (_insp_index() or []):
        x = _insp_get(iid)
        if not x or not _client_owns(x, email):
            continue
        prop = x.get("property", {})
        photos = [{"thumbUrl": p.get("thumbUrl") or p.get("url"), "url": p.get("url") or p.get("thumbUrl"),
                   "caption": p.get("caption", "")} for p in (x.get("photos") or []) if (p.get("thumbUrl") or p.get("url"))]
        out.append({"id": x["id"], "created_ts": x.get("created_ts"), "status": x.get("status", "draft"),
                    "property": {"name": prop.get("name", ""), "address": prop.get("address", "")},
                    "photos": photos, "docs": ["report", "checklist", "proposal"]})
    out.sort(key=lambda i: i.get("created_ts", 0), reverse=True)
    return jsonify({"authed": True, "email": email, "name": s.get("name", ""), "inspections": out})


@app.get("/api/portal/inspection/<iid>/doc/<kind>")
def portal_inspection_doc(iid, kind):
    s = read_session()
    if not s or not s.get("email"):
        return jsonify({"error": "sign in required"}), 401
    x = _insp_get(iid)
    if not x or not _client_owns(x, s.get("email", "")):
        return jsonify({"error": "not found"}), 404
    if kind not in DOC_BUILDERS or not _RL:
        return jsonify({"error": "unavailable"}), 400
    try:
        pdf = DOC_BUILDERS[kind](x)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_WWS_%s.pdf"' % kind
    return resp


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
    """Fetch a durable public image URL into a BytesIO for PDF embedding. Best-effort."""
    try:
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


def _dfinish(buf, doc, story):
    doc.build(story, onFirstPage=_dfooter, onLaterPages=_dfooter)
    return buf.getvalue()


def _money(v):
    try:
        return "{:,.0f}".format(float(str(v).replace(",", "").replace("$", "")))
    except Exception:
        return str(v)


def doc_checklist(insp):
    st = _dstyles(); buf, doc = _dnew("Completed OSHA Subpart D Checklist"); story = []
    _dheader(story, st, "OSHA 1910 Subpart D - field compliance record", "Completed Inspection Checklist", insp)
    findings = insp.get("findings") or _seed_findings()
    secs, order = {}, []
    for f in findings:
        s = f.get("section", "Other")
        if s not in secs:
            secs[s] = []; order.append(s)
        secs[s].append(f)
    for s in order:
        std = secs[s][0].get("std", "")
        story.append(Paragraph(_esc(s) + "  ·  " + _esc(std), st["sect"]))
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
    story.append(Paragraph("Field compliance record only. Anchorage load-test certification (§1910.27) and any structural repair must be performed and sealed by a licensed Florida professional engineer. Thresholds per 29 CFR 1910 Subpart D.", st["disc"]))
    return _dfinish(buf, doc, story)


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
    photos = insp.get("photos") or []
    if photos:
        story.append(Paragraph("Photo log", st["sect"]))
        cells = []
        for ph in photos[:9]:
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
            cap = _esc(ph.get("caption", ""))
            if cap:
                flow.append(Paragraph(cap, st["tdc"]))
            cells.append(flow)
        while len(cells) % 3 != 0:
            cells.append("")
        grid = [cells[i:i + 3] for i in range(0, len(cells), 3)]
        gt = Table(grid, colWidths=[2.36 * inch] * 3)
        gt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                                ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
        story.append(gt)
        if len(photos) > 9:
            story.append(Paragraph("+ %d more photo(s) in SiteCam." % (len(photos) - 9), st["disc"]))
    if insp.get("recommendations"):
        story.append(Paragraph("Recommendations", st["sect"])); story.append(Paragraph(_esc(insp["recommendations"]), st["body"]))
    story.append(Paragraph("La Gala Construction provides licensed contracting services; engineered inspection and anchorage load-test certification are performed and sealed by an independent licensed Florida professional engineer. La Gala does not provide engineering services. Not legal advice.", st["disc"]))
    return _dfinish(buf, doc, story)


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
    return _dfinish(buf, doc, story)


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
    return _dfinish(buf, doc, story)


DOC_BUILDERS = {"checklist": doc_checklist, "report": doc_report, "cert": doc_cert, "proposal": doc_proposal}
DOC_LABEL = {"checklist": "Completed Subpart D Checklist", "report": "Inspection Report",
             "cert": "Engineer Certification Packet", "proposal": "Corrective-Work Proposal"}


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
        "summary": "", "recommendations": "", "corrective": [], "photos": [], "sitecam": {},
        "source_lead_id": b.get("lead_id", ""), "source_request_id": b.get("request_id", ""),
    }
    if not _insp_save(insp):
        return jsonify({"ok": False, "error": "store not configured", "inspection": insp}), 200
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
    for k in ("property", "client", "inspector", "pe", "findings", "corrective", "photos", "summary", "recommendations", "status", "sitecam"):
        if k in b:
            x[k] = b[k]
    _insp_save(x)
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
        pdf = fn(x)
    except Exception as e:
        return jsonify({"error": "pdf failed: " + str(e)}), 500
    base = (x.get("property", {}).get("name", "") or iid).replace(" ", "_")[:40]
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = 'inline; filename="LaGala_WWS_%s_%s.pdf"' % (kind, base)
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
        out.append({"url": p.get("url", ""), "thumbUrl": p.get("thumbUrl", ""),
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

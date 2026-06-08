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
    params = {
        "client_id": cid,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
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


@app.route("/api/portal/status", methods=["GET"])
def portal_status():
    """Quick check that env vars are wired up."""
    return jsonify({
        "mode":              "email-attachment",
        "resend_configured": bool(RESEND_KEY),
        "from_email":        RESEND_FROM if RESEND_KEY else None,
        "portal_base":       PORTAL_BASE,
        "staff_count":       len(PORTAL_STAFF),
        "max_file_mb":       MAX_FILE_BYTES // (1024 * 1024),
    })


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

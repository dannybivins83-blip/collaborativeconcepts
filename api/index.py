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
                    samesite="Lax", max_age=60 * 60 * 8, path="/")


def set_temp(resp, name, value, max_age=600):
    token = _fernet().encrypt(json.dumps(value).encode()).decode()
    resp.set_cookie(name, token, httponly=True, secure=True, samesite="Lax",
                    max_age=max_age, path="/")


def read_temp(name):
    raw = request.cookies.get(name)
    if not raw:
        return None
    try:
        return json.loads(_fernet().decrypt(raw.encode()))
    except (InvalidToken, ValueError, RuntimeError):
        return None


def clear_cookie(resp, name):
    resp.set_cookie(name, "", expires=0, path="/")


def base_url():
    host = request.headers.get("x-forwarded-host", request.host)
    proto = request.headers.get("x-forwarded-proto", "https")
    return "{}://{}".format(proto, host)


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
    return os.environ.get("WWSLGC_REDIRECT_URI") or (base_url() + "/api/auth/callback")


def google_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI") or (base_url() + "/api/auth/google/callback")


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
    resp = make_response(redirect("/wwslgc"))
    write_session(resp, {"provider": "microsoft", "access_token": result["access_token"],
                         "email": email, "name": claims.get("name", email)})
    clear_cookie(resp, FLOW_COOKIE)
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
    set_temp(resp, GSTATE_COOKIE, {"state": state})
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
    resp = make_response(redirect("/wwslgc"))
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

"""
WWSLGC portal API (Vercel Python / Flask).

Internal, login-gated. Microsoft 365 sign-in (Entra ID, restricted to the
lagalacon.com tenant) doubles as the portal login AND the authorization to
send mail via Microsoft Graph -- so drafts/sends land in the signed-in user's
real mailbox and sync to Outlook.

All routes are under /api/* (see vercel.json rewrite). No secrets live in the
repo; everything sensitive comes from Vercel environment variables.

Env vars (set in Vercel project settings):
  MS_CLIENT_ID          Entra app (client) ID
  MS_CLIENT_SECRET      Entra client secret value
  MS_TENANT_ID          Entra directory (tenant) ID  -> restricts sign-in to your org
  SESSION_SECRET        long random string (signs/encrypts the session cookie)
  WWSLGC_REDIRECT_URI   optional override, e.g. https://wwslgc.collaborativeconceptsfl.com/api/auth/callback
  ALLOWED_EMAIL_DOMAIN  optional, defaults to lagalacon.com
"""

import base64
import hashlib
import json
import os

import requests
from flask import Flask, request, redirect, jsonify, make_response
from cryptography.fernet import Fernet, InvalidToken
import msal

app = Flask(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["User.Read", "Mail.Send", "Mail.ReadWrite"]
SESSION_COOKIE = "wwslgc_session"
FLOW_COOKIE = "wwslgc_flow"
ALLOWED_DOMAIN = os.environ.get("ALLOWED_EMAIL_DOMAIN", "lagalacon.com").lower()

# Built-in templates (mirrors the local tool). Placeholders like {{First}} are
# merged client-side; the API only sends finished subject/body strings.
SIGNATURE = (
    "Daniel Bivins · Client Relations\n"
    "La Gala Construction / Tilt Patchers, Inc. · CGC059211 · in partnership with UES\n"
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
              "protection, concrete/coating repair, and anchor install/replacement — and our "
              "engineering partner UES provides the sealed inspection and the 5,000-lb anchor "
              "certification. One team for both the certificate and the fix.\n\nCan I set up a free "
              "walking-surface assessment this week and get you documentation for your file? "
              "Flyer attached.\n\n" + SIGNATURE)},
    {"name": "Free assessment offer",
     "subject": "Free walking-surface assessment for {{Company}}",
     "body": ("Hi {{First}},\n\nWe're offering a no-obligation walking-surface assessment for "
              "facilities in {{County}} County with open OSHA Subpart D items. La Gala (CGC059211) "
              "self-performs the surface, edge, and anchor work; UES seals the inspection and any "
              "anchor certification — one accountable team, one point of contact.\n\nYou'd get a "
              "clear written scope plus documentation for your case file. Do you have 20 minutes "
              "this week? Flyer attached.\n\n" + SIGNATURE)},
    {"name": "Follow-up — no reply",
     "subject": "Following up — {{Company}} walking-surface item",
     "body": ("Hi {{First}},\n\nCircling back on the open OSHA walking-surface item (§{{Standard}}) "
              "at {{Company}}. We can scope it this week and hand you documentation for your file at "
              "no cost — we self-perform the fix and UES seals the engineered sign-off where one is "
              "needed.\n\nWant me to set up the free assessment?\n\n" + SIGNATURE)},
    {"name": "Blank — write your own",
     "subject": "",
     "body": "Hi {{First}},\n\n\n\n" + SIGNATURE},
]


# --------------------------------------------------------------------------
# Session cookie crypto (Fernet, derived from SESSION_SECRET)
# --------------------------------------------------------------------------
def _fernet():
    secret = os.environ.get("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def read_session():
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = _fernet().decrypt(raw.encode())
        return json.loads(data)
    except (InvalidToken, ValueError, RuntimeError):
        return None


def write_session(resp, payload):
    token = _fernet().encrypt(json.dumps(payload).encode()).decode()
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, secure=True,
                    samesite="Lax", max_age=60 * 60 * 8, path="/")


def clear_cookie(resp, name):
    resp.set_cookie(name, "", expires=0, path="/")


# --------------------------------------------------------------------------
# MSAL helpers
# --------------------------------------------------------------------------
def msal_app():
    return msal.ConfidentialClientApplication(
        os.environ["MS_CLIENT_ID"],
        authority="https://login.microsoftonline.com/" + os.environ["MS_TENANT_ID"],
        client_credential=os.environ["MS_CLIENT_SECRET"],
    )


def redirect_uri():
    override = os.environ.get("WWSLGC_REDIRECT_URI")
    if override:
        return override
    host = request.headers.get("x-forwarded-host", request.host)
    proto = request.headers.get("x-forwarded-proto", "https")
    return "{}://{}/api/auth/callback".format(proto, host)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/api/me")
def me():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "email": s.get("email"), "name": s.get("name")})


@app.get("/api/templates")
def templates():
    return jsonify({"templates": TEMPLATES, "signature": SIGNATURE})


@app.get("/api/login")
def login():
    flow = msal_app().initiate_auth_code_flow(SCOPES, redirect_uri=redirect_uri())
    resp = make_response(redirect(flow["auth_uri"]))
    # the flow dict (state + PKCE verifier) must survive the round-trip
    token = _fernet().encrypt(json.dumps(flow).encode()).decode()
    resp.set_cookie(FLOW_COOKIE, token, httponly=True, secure=True,
                    samesite="Lax", max_age=600, path="/")
    return resp


@app.get("/api/auth/callback")
def callback():
    raw = request.cookies.get(FLOW_COOKIE)
    if not raw:
        return _err_page("Sign-in expired. Please try again.")
    try:
        flow = json.loads(_fernet().decrypt(raw.encode()))
    except (InvalidToken, ValueError, RuntimeError):
        return _err_page("Sign-in could not be verified. Please try again.")

    result = msal_app().acquire_token_by_auth_code_flow(flow, dict(request.args))
    if "access_token" not in result:
        return _err_page("Sign-in failed: " + result.get("error_description", result.get("error", "unknown")))

    claims = result.get("id_token_claims", {})
    # Defense in depth: tenant is already locked by authority, also check domain.
    email = (claims.get("preferred_username") or claims.get("email") or "").lower()
    if ALLOWED_DOMAIN and not email.endswith("@" + ALLOWED_DOMAIN):
        return _err_page("This portal is restricted to @{} accounts.".format(ALLOWED_DOMAIN))

    resp = make_response(redirect("/wwslgc"))
    write_session(resp, {
        "access_token": result["access_token"],
        "email": email,
        "name": claims.get("name", email),
    })
    clear_cookie(resp, FLOW_COOKIE)
    return resp


@app.get("/api/logout")
def logout():
    resp = make_response(redirect("/wwslgc"))
    clear_cookie(resp, SESSION_COOKIE)
    return resp


@app.post("/api/send")
def send():
    s = read_session()
    if not s or not s.get("access_token"):
        return jsonify({"ok": False, "status": "not signed in"}), 401

    body = request.get_json(force=True, silent=True) or {}
    mode = body.get("mode", "draft")               # draft | send | test
    rcpt = body.get("recipient", {})
    to_email = (rcpt.get("email") or "").strip()
    if mode == "test":
        to_email = s.get("email")
    if not to_email:
        return jsonify({"ok": False, "status": "no recipient"}), 400

    # Build Graph message
    message = {
        "subject": rcpt.get("subject", ""),
        "body": {"contentType": "HTML", "content": _text_to_html(rcpt.get("body", ""))},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
    }
    attachments = _build_attachments(body.get("attachments", []))
    if attachments:
        message["attachments"] = attachments

    headers = {"Authorization": "Bearer " + s["access_token"], "Content-Type": "application/json"}
    try:
        if mode == "send":
            r = requests.post(GRAPH + "/me/sendMail",
                              headers=headers, json={"message": message, "saveToSentItems": True},
                              timeout=30)
            ok = r.status_code in (200, 202)
            status = "sent" if ok else _graph_err(r)
        else:  # draft or test -> create a draft they can review/send
            r = requests.post(GRAPH + "/me/messages", headers=headers, json=message, timeout=30)
            ok = r.status_code in (200, 201)
            status = "draft created" if ok else _graph_err(r)
        return jsonify({"ok": ok, "status": status, "email": to_email}), (200 if ok else 502)
    except requests.RequestException as e:
        return jsonify({"ok": False, "status": "network error: " + str(e), "email": to_email}), 502


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _text_to_html(text):
    from html import escape
    return escape(text or "").replace("\n", "<br>\n")


def _build_attachments(urls):
    """Fetch each (public) collateral URL and inline it as a Graph fileAttachment."""
    out = []
    host = request.headers.get("x-forwarded-host", request.host)
    proto = request.headers.get("x-forwarded-proto", "https")
    for u in urls or []:
        full = u if u.startswith("http") else "{}://{}{}".format(proto, host, u)
        try:
            r = requests.get(full, timeout=20)
            if r.status_code == 200 and r.content:
                out.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": full.rsplit("/", 1)[-1],
                    "contentBytes": base64.b64encode(r.content).decode(),
                })
        except requests.RequestException:
            pass
    return out


def _graph_err(r):
    try:
        j = r.json()
        return "Graph {}: {}".format(r.status_code, j.get("error", {}).get("message", r.text[:200]))
    except ValueError:
        return "Graph {}: {}".format(r.status_code, r.text[:200])


def _err_page(msg):
    html = ("<!doctype html><meta charset=utf-8><title>WWSLGC sign-in</title>"
            "<body style='font-family:sans-serif;max-width:520px;margin:80px auto;color:#0B2340'>"
            "<h2>Sign-in problem</h2><p>{}</p>"
            "<p><a href='/wwslgc'>← Back to the portal</a></p></body>").format(msg)
    return make_response(html, 400)

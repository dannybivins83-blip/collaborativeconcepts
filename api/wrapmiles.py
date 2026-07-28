"""
WrapMiles portals API — admin matchmaking desk, driver portal, sponsor reports.

Routes live under /api/wrapmiles/* and are registered onto the main Flask app
via register_wrapmiles_routes(app) (same pattern as api/permits.py).

Storage: Postgres (Neon / Vercel Postgres) via WRAPMILES_DB_URL, POSTGRES_URL,
or DATABASE_URL. Until a database is attached the API answers with
{"error":"db_not_configured"} and the portal pages render a setup screen —
nothing crashes. sqlite:///<path> URLs are supported for offline tests.

Auth model (v1, no email infrastructure needed):
  - Admin signs in with WRAPMILES_ADMIN_KEY (Vercel env var).
  - Drivers/sponsors sign in with email + access code. Codes are generated in
    the admin panel; Danny texts/emails them out. No passwords stored.
  - Sessions are HMAC-signed tokens (SESSION_SECRET or the admin key as key
    material), sent as  Authorization: Bearer <token>.

Money is integer cents. Mileage is integer miles. Impressions are ESTIMATES
(EST_IMPRESSIONS_PER_MILE) and every payload labels them as such.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from urllib.parse import urlparse, parse_qs

from flask import jsonify, request

EST_IMPRESSIONS_PER_MILE = 50  # midpoint of the 30–70/urban-mile OOH benchmark
TOKEN_TTL = 30 * 24 * 3600     # 30 days
DEFAULT_CAP_MILES = 2000

DRIVER_STATUSES = ["new", "contacted", "qualified", "docs_verified",
                   "wrap_ready", "matched", "active", "churned", "rejected"]
SPONSOR_STATUSES = ["new", "contacted", "discovery", "proposal_sent",
                    "negotiating", "signed", "live", "renewed", "churned"]
CAMPAIGN_STATUSES = ["draft", "active", "completed", "cancelled"]
MATCH_STATUSES = ["proposed", "accepted", "wrapped", "active", "ended"]


# --------------------------------------------------------------------------
# database plumbing
# --------------------------------------------------------------------------

def _db_url():
    return (os.environ.get("WRAPMILES_DB_URL")
            or os.environ.get("POSTGRES_URL")
            or os.environ.get("DATABASE_URL") or "").strip()


def _is_sqlite(url):
    return url.startswith("sqlite:")


class DB:
    """Tiny dual-dialect (postgres/sqlite) helper. One instance per request."""

    def __init__(self, url):
        self.url = url
        self.sqlite = _is_sqlite(url)
        if self.sqlite:
            path = url.split("sqlite:///")[-1] or ":memory:"
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row
        else:
            import pg8000.dbapi as pg
            u = urlparse(url)
            kw = dict(user=u.username or "", password=u.password or "",
                      host=u.hostname, port=u.port or 5432,
                      database=(u.path or "/").lstrip("/") or "postgres")
            qs = parse_qs(u.query or "")
            if qs.get("sslmode", ["require"])[0] != "disable":
                import ssl
                ctx = ssl.create_default_context()
                kw["ssl_context"] = ctx
            self.conn = pg.Connection(**kw)

    def q(self, sql, params=()):
        """Run sql written with %s placeholders; returns list[dict]."""
        if self.sqlite:
            sql = sql.replace("%s", "?")
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        rows = []
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows

    def commit(self):
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS wm_drivers (
  id SERIAL PRIMARY KEY, created_at BIGINT NOT NULL,
  name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL UNIQUE, city_zip TEXT NOT NULL DEFAULT '',
  asset_type TEXT NOT NULL DEFAULT '', vehicle TEXT NOT NULL DEFAULT '',
  monthly_miles TEXT NOT NULL DEFAULT '', routes TEXT NOT NULL DEFAULT '',
  parking TEXT NOT NULL DEFAULT '', coverage TEXT NOT NULL DEFAULT '',
  referred_by TEXT NOT NULL DEFAULT '', score TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'new', access_code TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS wm_sponsors (
  id SERIAL PRIMARY KEY, created_at BIGINT NOT NULL,
  company TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL UNIQUE, phone TEXT NOT NULL DEFAULT '',
  budget TEXT NOT NULL DEFAULT '', fleet_size TEXT NOT NULL DEFAULT '',
  zones TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '',
  referred_by TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'new',
  access_code TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS wm_campaigns (
  id SERIAL PRIMARY KEY, created_at BIGINT NOT NULL,
  sponsor_id INTEGER NOT NULL, name TEXT NOT NULL DEFAULT '',
  zone TEXT NOT NULL DEFAULT '', cars_needed INTEGER NOT NULL DEFAULT 1,
  coverage TEXT NOT NULL DEFAULT '', rate_cents_per_mile INTEGER NOT NULL DEFAULT 0,
  flat_cents_month INTEGER NOT NULL DEFAULT 0,
  cap_miles INTEGER NOT NULL DEFAULT 2000,
  start_date TEXT NOT NULL DEFAULT '', end_date TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft'
);
CREATE TABLE IF NOT EXISTS wm_matches (
  id SERIAL PRIMARY KEY, created_at BIGINT NOT NULL,
  campaign_id INTEGER NOT NULL, driver_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed', wrapped_at TEXT NOT NULL DEFAULT '',
  UNIQUE (campaign_id, driver_id)
);
CREATE TABLE IF NOT EXISTS wm_mileage (
  id SERIAL PRIMARY KEY, created_at BIGINT NOT NULL,
  match_id INTEGER NOT NULL, period TEXT NOT NULL,
  miles INTEGER NOT NULL DEFAULT 0, odo_start INTEGER NOT NULL DEFAULT 0,
  odo_end INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'submitted',
  miles_approved INTEGER NOT NULL DEFAULT 0, reviewed_at BIGINT NOT NULL DEFAULT 0,
  UNIQUE (match_id, period)
);
"""


def _schema_sql(sqlite):
    sql = _SCHEMA_PG
    if sqlite:
        sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    return [s.strip() for s in sql.split(";") if s.strip()]


_schema_ready = set()

# columns added after first release: (table, column, ddl-type-with-default)
_MIGRATIONS = [
    ("wm_drivers", "ref_code", "TEXT NOT NULL DEFAULT ''"),
]


def get_db():
    """Open a DB for this request, creating the schema once per process."""
    url = _db_url()
    if not url:
        return None
    db = DB(url)
    if url not in _schema_ready:
        for stmt in _schema_sql(db.sqlite):
            db.q(stmt)
        for table, col, ddl in _MIGRATIONS:
            try:
                if db.sqlite:
                    db.q(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                else:
                    db.q(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}")
            except Exception:
                pass  # column already exists (sqlite has no IF NOT EXISTS)
        db.commit()
        _schema_ready.add(url)
    return db


def _no_db():
    return jsonify({"error": "db_not_configured",
                    "setup": "Attach a Postgres database to this Vercel project "
                             "(Storage → Create Database → Neon/Postgres) so a "
                             "POSTGRES_URL env var exists, then redeploy."}), 503


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

def _secret():
    s = os.environ.get("SESSION_SECRET") or os.environ.get("WRAPMILES_ADMIN_KEY") or ""
    return hashlib.sha256(("wrapmiles|" + s).encode()).digest()


def _admin_key():
    return (os.environ.get("WRAPMILES_ADMIN_KEY") or "").strip()


def make_token(role, ident):
    body = json.dumps({"r": role, "i": ident, "e": int(time.time()) + TOKEN_TTL},
                      separators=(",", ":")).encode()
    b = base64.urlsafe_b64encode(body).decode().rstrip("=")
    sig = hmac.new(_secret(), b.encode(), hashlib.sha256).hexdigest()[:32]
    return b + "." + sig


def read_token(tok):
    try:
        b, sig = tok.split(".", 1)
        good = hmac.new(_secret(), b.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good):
            return None
        pad = "=" * (-len(b) % 4)
        body = json.loads(base64.urlsafe_b64decode(b + pad))
        if body.get("e", 0) < time.time():
            return None
        return body
    except Exception:
        return None


def bearer():
    h = request.headers.get("Authorization", "")
    return read_token(h[7:]) if h.startswith("Bearer ") else None


def require(role):
    t = bearer()
    if not t or t.get("r") != role:
        return None
    return t


def new_code():
    # unambiguous alphabet, easy to read over the phone
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


SITE_BASE = os.environ.get("WRAPMILES_SITE_BASE", "https://collaborativeconceptsfl.com")


def new_ref_code(name):
    """Short, shareable, non-secret: first name + 4 chars (e.g. PETE-7K2M)."""
    first = re.sub(r"[^A-Za-z]", "", (name or "").split(" ")[0]).upper()[:6] or "DRIVE"
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return first + "-" + "".join(secrets.choice(alphabet) for _ in range(4))


def ref_link(code):
    return f"{SITE_BASE}/wrapmiles?ref={code}"


def ensure_ref_code(db, driver_row):
    """Backfill a ref_code for drivers created before the referral feature."""
    if driver_row.get("ref_code"):
        return driver_row["ref_code"]
    code = new_ref_code(driver_row.get("name"))
    db.q("UPDATE wm_drivers SET ref_code=%s WHERE id=%s", [code, driver_row["id"]])
    db.commit()
    driver_row["ref_code"] = code
    return code


def _clean(v, limit=500):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:limit]


def _email(v):
    e = _clean(v, 200).lower()
    return e if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e) else ""


def now():
    return int(time.time())


# --------------------------------------------------------------------------
# money helpers
# --------------------------------------------------------------------------

def driver_period_cents(campaign, m_row):
    """Approved cents for one mileage row under its campaign terms."""
    miles = min(int(m_row.get("miles_approved") or 0), int(campaign.get("cap_miles") or DEFAULT_CAP_MILES))
    per_mile = miles * int(campaign.get("rate_cents_per_mile") or 0)
    return per_mile + int(campaign.get("flat_cents_month") or 0)


# --------------------------------------------------------------------------
# route registration
# --------------------------------------------------------------------------

def register_wrapmiles_routes(app):

    P = "/api/wrapmiles"

    # ---------------- public ----------------

    @app.route(P + "/status", methods=["GET"])
    def wm_status():
        return jsonify({"db": bool(_db_url()), "admin_key_set": bool(_admin_key())})

    @app.route(P + "/qr", methods=["GET"])
    def wm_qr():
        """PNG QR of a referral link. Only encodes our own /wrapmiles?ref= URL."""
        code = _clean(request.args.get("ref"), 16).upper()
        if not re.match(r"^[A-Z0-9-]{3,16}$", code):
            return jsonify({"error": "bad ref code"}), 400
        try:
            import io
            import qrcode
            img = qrcode.make(ref_link(code), box_size=8, border=2)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            from flask import send_file
            resp = send_file(buf, mimetype="image/png")
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp
        except Exception:
            return jsonify({"error": "qr unavailable"}), 500

    @app.route(P + "/apply", methods=["POST"])
    def wm_apply():
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        if _clean(d.get("_honey")):
            return jsonify({"ok": True})  # bot
        email = _email(d.get("email"))
        if not email:
            db.close()
            return jsonify({"error": "valid email required"}), 400
        row = dict(created_at=now(), name=_clean(d.get("name")), phone=_clean(d.get("phone"), 40),
                   email=email, city_zip=_clean(d.get("city_zip")),
                   asset_type=_clean(d.get("asset_type")), vehicle=_clean(d.get("vehicle")),
                   monthly_miles=_clean(d.get("monthly_miles")), routes=_clean(d.get("main_routes")),
                   parking=_clean(d.get("daytime_parking")), coverage=_clean(d.get("wrap_coverage")),
                   referred_by=_clean(d.get("referred_by")))
        try:
            db.q("""INSERT INTO wm_drivers
                    (created_at,name,phone,email,city_zip,asset_type,vehicle,monthly_miles,
                     routes,parking,coverage,referred_by,ref_code)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 [row["created_at"], row["name"], row["phone"], row["email"], row["city_zip"],
                  row["asset_type"], row["vehicle"], row["monthly_miles"], row["routes"],
                  row["parking"], row["coverage"], row["referred_by"],
                  new_ref_code(row["name"])])
            db.commit()
        except Exception:
            # duplicate email → update the fresh details, keep pipeline status
            db.q("""UPDATE wm_drivers SET name=%s,phone=%s,city_zip=%s,asset_type=%s,vehicle=%s,
                    monthly_miles=%s,routes=%s,parking=%s,coverage=%s WHERE email=%s""",
                 [row["name"], row["phone"], row["city_zip"], row["asset_type"], row["vehicle"],
                  row["monthly_miles"], row["routes"], row["parking"], row["coverage"], email])
            db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/inquiry", methods=["POST"])
    def wm_inquiry():
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or request.form.to_dict() or {}
        if _clean(d.get("_honey")):
            return jsonify({"ok": True})
        email = _email(d.get("email"))
        if not email:
            db.close()
            return jsonify({"error": "valid email required"}), 400
        try:
            db.q("""INSERT INTO wm_sponsors
                    (created_at,company,contact,email,phone,budget,fleet_size,zones,message,referred_by)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 [now(), _clean(d.get("company")), _clean(d.get("name") or d.get("contact")),
                  email, _clean(d.get("phone"), 40), _clean(d.get("budget")),
                  _clean(d.get("fleet_size")), _clean(d.get("zones") or d.get("target_area")),
                  _clean(d.get("message"), 2000), _clean(d.get("referred_by"))])
            db.commit()
        except Exception:
            db.q("UPDATE wm_sponsors SET company=%s, phone=%s, budget=%s, message=%s WHERE email=%s",
                 [_clean(d.get("company")), _clean(d.get("phone"), 40),
                  _clean(d.get("budget")), _clean(d.get("message"), 2000), email])
            db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/login", methods=["POST"])
    def wm_login():
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        role = d.get("role")
        email = _email(d.get("email"))
        code = _clean(d.get("code"), 20).upper().replace(" ", "")
        table = {"driver": "wm_drivers", "sponsor": "wm_sponsors"}.get(role)
        if not table or not email or not code:
            db.close()
            return jsonify({"error": "role, email and access code required"}), 400
        rows = db.q(f"SELECT id, access_code FROM {table} WHERE email=%s", [email])
        db.close()
        if not rows or not rows[0]["access_code"] or \
           not hmac.compare_digest(rows[0]["access_code"], code):
            return jsonify({"error": "wrong email or access code"}), 401
        return jsonify({"token": make_token(role, rows[0]["id"])})

    @app.route(P + "/admin/login", methods=["POST"])
    def wm_admin_login():
        key = _admin_key()
        if not key:
            return jsonify({"error": "admin_key_not_set",
                            "setup": "Set the WRAPMILES_ADMIN_KEY env var in Vercel "
                                     "(Project → Settings → Environment Variables), redeploy, "
                                     "then sign in with that key."}), 503
        d = request.get_json(silent=True) or {}
        if not hmac.compare_digest(_clean(d.get("key"), 200), key):
            return jsonify({"error": "wrong key"}), 401
        return jsonify({"token": make_token("admin", 0)})

    # ---------------- admin ----------------

    def _admin_guard():
        if not require("admin"):
            return jsonify({"error": "unauthorized"}), 401
        return None

    @app.route(P + "/admin/overview", methods=["GET"])
    def wm_admin_overview():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        out = {}
        for label, table in [("drivers", "wm_drivers"), ("sponsors", "wm_sponsors")]:
            rows = db.q(f"SELECT status, COUNT(*) AS n FROM {table} GROUP BY status")
            out[label] = {r["status"]: int(r["n"]) for r in rows}
        out["campaigns"] = {r["status"]: int(r["n"]) for r in
                            db.q("SELECT status, COUNT(*) AS n FROM wm_campaigns GROUP BY status")}
        out["pending_mileage"] = int((db.q(
            "SELECT COUNT(*) AS n FROM wm_mileage WHERE status='submitted'") or [{"n": 0}])[0]["n"])
        db.close()
        return jsonify(out)

    @app.route(P + "/admin/drivers", methods=["GET"])
    def wm_admin_drivers():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        rows = db.q("SELECT * FROM wm_drivers ORDER BY created_at DESC")
        db.close()
        return jsonify({"drivers": rows, "statuses": DRIVER_STATUSES})

    @app.route(P + "/admin/drivers/<int:did>", methods=["PATCH"])
    def wm_admin_driver_patch(did):
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        sets, vals = [], []
        for field in ("score", "status", "notes"):
            if field in d:
                val = _clean(d[field], 4000)
                if field == "status" and val not in DRIVER_STATUSES:
                    db.close()
                    return jsonify({"error": "bad status"}), 400
                sets.append(f"{field}=%s")
                vals.append(val)
        code = None
        if d.get("reset_code"):
            code = new_code()
            sets.append("access_code=%s")
            vals.append(code)
        if not sets:
            db.close()
            return jsonify({"error": "nothing to update"}), 400
        vals.append(did)
        db.q(f"UPDATE wm_drivers SET {', '.join(sets)} WHERE id=%s", vals)
        db.commit()
        db.close()
        return jsonify({"ok": True, "access_code": code})

    @app.route(P + "/admin/sponsors", methods=["GET"])
    def wm_admin_sponsors():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        rows = db.q("SELECT * FROM wm_sponsors ORDER BY created_at DESC")
        db.close()
        return jsonify({"sponsors": rows, "statuses": SPONSOR_STATUSES})

    @app.route(P + "/admin/sponsors/<int:sid>", methods=["PATCH"])
    def wm_admin_sponsor_patch(sid):
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        sets, vals = [], []
        for field in ("status", "notes"):
            if field in d:
                val = _clean(d[field], 4000)
                if field == "status" and val not in SPONSOR_STATUSES:
                    db.close()
                    return jsonify({"error": "bad status"}), 400
                sets.append(f"{field}=%s")
                vals.append(val)
        code = None
        if d.get("reset_code"):
            code = new_code()
            sets.append("access_code=%s")
            vals.append(code)
        if not sets:
            db.close()
            return jsonify({"error": "nothing to update"}), 400
        vals.append(sid)
        db.q(f"UPDATE wm_sponsors SET {', '.join(sets)} WHERE id=%s", vals)
        db.commit()
        db.close()
        return jsonify({"ok": True, "access_code": code})

    @app.route(P + "/admin/campaigns", methods=["GET", "POST"])
    def wm_admin_campaigns():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        if request.method == "GET":
            camps = db.q("""SELECT c.*, s.company AS sponsor_company FROM wm_campaigns c
                            LEFT JOIN wm_sponsors s ON s.id=c.sponsor_id
                            ORDER BY c.created_at DESC""")
            matches = db.q("""SELECT m.*, d.name AS driver_name, d.vehicle AS driver_vehicle,
                                     d.email AS driver_email
                              FROM wm_matches m JOIN wm_drivers d ON d.id=m.driver_id""")
            db.close()
            by_camp = {}
            for m in matches:
                by_camp.setdefault(m["campaign_id"], []).append(m)
            for c in camps:
                c["matches"] = by_camp.get(c["id"], [])
            return jsonify({"campaigns": camps, "statuses": CAMPAIGN_STATUSES,
                            "match_statuses": MATCH_STATUSES})
        d = request.get_json(silent=True) or {}
        try:
            sponsor_id = int(d.get("sponsor_id"))
            rate = int(round(float(d.get("rate_per_mile") or 0) * 100))
            flat = int(round(float(d.get("flat_monthly") or 0) * 100))
            cars = max(1, int(d.get("cars_needed") or 1))
            cap = int(d.get("cap_miles") or DEFAULT_CAP_MILES)
        except (TypeError, ValueError):
            db.close()
            return jsonify({"error": "bad numbers"}), 400
        db.q("""INSERT INTO wm_campaigns
                (created_at,sponsor_id,name,zone,cars_needed,coverage,rate_cents_per_mile,
                 flat_cents_month,cap_miles,start_date,end_date,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')""",
             [now(), sponsor_id, _clean(d.get("name")), _clean(d.get("zone")), cars,
              _clean(d.get("coverage")), rate, flat, cap,
              _clean(d.get("start_date"), 20), _clean(d.get("end_date"), 20)])
        db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/admin/campaigns/<int:cid>", methods=["PATCH"])
    def wm_admin_campaign_patch(cid):
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        sets, vals = [], []
        if "status" in d:
            if d["status"] not in CAMPAIGN_STATUSES:
                db.close()
                return jsonify({"error": "bad status"}), 400
            sets.append("status=%s")
            vals.append(d["status"])
        for f in ("name", "zone", "coverage", "start_date", "end_date"):
            if f in d:
                sets.append(f + "=%s")
                vals.append(_clean(d[f]))
        for f, col in (("rate_per_mile", "rate_cents_per_mile"), ("flat_monthly", "flat_cents_month")):
            if f in d:
                try:
                    sets.append(col + "=%s")
                    vals.append(int(round(float(d[f]) * 100)))
                except (TypeError, ValueError):
                    db.close()
                    return jsonify({"error": "bad numbers"}), 400
        if not sets:
            db.close()
            return jsonify({"error": "nothing to update"}), 400
        vals.append(cid)
        db.q(f"UPDATE wm_campaigns SET {', '.join(sets)} WHERE id=%s", vals)
        db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/admin/matches", methods=["POST"])
    def wm_admin_match():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        try:
            cid, did = int(d.get("campaign_id")), int(d.get("driver_id"))
        except (TypeError, ValueError):
            db.close()
            return jsonify({"error": "campaign_id and driver_id required"}), 400
        try:
            db.q("INSERT INTO wm_matches (created_at,campaign_id,driver_id) VALUES (%s,%s,%s)",
                 [now(), cid, did])
            db.q("UPDATE wm_drivers SET status='matched' WHERE id=%s AND status IN ('wrap_ready','docs_verified','qualified')",
                 [did])
            db.commit()
        except Exception:
            db.close()
            return jsonify({"error": "already matched"}), 409
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/admin/matches/<int:mid>", methods=["PATCH"])
    def wm_admin_match_patch(mid):
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        status = d.get("status")
        if status not in MATCH_STATUSES:
            db.close()
            return jsonify({"error": "bad status"}), 400
        db.q("UPDATE wm_matches SET status=%s, wrapped_at=%s WHERE id=%s",
             [status, _clean(d.get("wrapped_at"), 20), mid])
        if status == "active":
            db.q("""UPDATE wm_drivers SET status='active' WHERE id=
                    (SELECT driver_id FROM wm_matches WHERE id=%s)""", [mid])
        db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/admin/mileage", methods=["GET"])
    def wm_admin_mileage():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        rows = db.q("""SELECT g.*, m.campaign_id, m.driver_id, d.name AS driver_name,
                              d.vehicle AS driver_vehicle, c.name AS campaign_name,
                              c.rate_cents_per_mile, c.flat_cents_month, c.cap_miles
                       FROM wm_mileage g
                       JOIN wm_matches m ON m.id=g.match_id
                       JOIN wm_drivers d ON d.id=m.driver_id
                       JOIN wm_campaigns c ON c.id=m.campaign_id
                       ORDER BY g.created_at DESC""")
        db.close()
        return jsonify({"mileage": rows})

    @app.route(P + "/admin/mileage/<int:gid>", methods=["PATCH"])
    def wm_admin_mileage_patch(gid):
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        status = d.get("status")
        if status not in ("approved", "rejected"):
            db.close()
            return jsonify({"error": "status must be approved or rejected"}), 400
        try:
            approved = max(0, int(d.get("miles_approved") or 0))
        except (TypeError, ValueError):
            db.close()
            return jsonify({"error": "bad miles_approved"}), 400
        db.q("UPDATE wm_mileage SET status=%s, miles_approved=%s, reviewed_at=%s WHERE id=%s",
             [status, approved if status == "approved" else 0, now(), gid])
        db.commit()
        db.close()
        return jsonify({"ok": True})

    @app.route(P + "/admin/ledger", methods=["GET"])
    def wm_admin_ledger():
        err = _admin_guard()
        if err:
            return err
        db = get_db()
        if not db:
            return _no_db()
        rows = db.q("""SELECT g.period, g.miles_approved, g.match_id, m.driver_id, m.campaign_id,
                              d.name AS driver_name, c.name AS campaign_name, c.sponsor_id,
                              c.rate_cents_per_mile, c.flat_cents_month, c.cap_miles,
                              s.company AS sponsor_company
                       FROM wm_mileage g
                       JOIN wm_matches m ON m.id=g.match_id
                       JOIN wm_drivers d ON d.id=m.driver_id
                       JOIN wm_campaigns c ON c.id=m.campaign_id
                       LEFT JOIN wm_sponsors s ON s.id=c.sponsor_id
                       WHERE g.status='approved'
                       ORDER BY g.period DESC""")
        db.close()
        ledger = []
        for r in rows:
            cents = driver_period_cents(r, r)
            ledger.append({"period": r["period"], "driver": r["driver_name"],
                           "driver_id": r["driver_id"], "campaign": r["campaign_name"],
                           "sponsor": r["sponsor_company"],
                           "miles_approved": int(r["miles_approved"] or 0),
                           "owed_cents": cents})
        return jsonify({"ledger": ledger,
                        "note": "owed = approved in-cap miles x rate + flat monthly, per period"})

    # ---------------- driver ----------------

    @app.route(P + "/driver/me", methods=["GET"])
    def wm_driver_me():
        t = require("driver")
        if not t:
            return jsonify({"error": "unauthorized"}), 401
        db = get_db()
        if not db:
            return _no_db()
        me = db.q("SELECT * FROM wm_drivers WHERE id=%s", [t["i"]])
        if not me:
            db.close()
            return jsonify({"error": "not found"}), 404
        me = me[0]
        me.pop("access_code", None)
        me.pop("notes", None)
        code = ensure_ref_code(db, me)
        ref_rows = db.q("""SELECT status, COUNT(*) AS n FROM wm_drivers
                           WHERE UPPER(referred_by)=UPPER(%s) AND id!=%s GROUP BY status""",
                        [code, me["id"]])
        ref_sponsors = db.q("SELECT COUNT(*) AS n FROM wm_sponsors WHERE UPPER(referred_by)=UPPER(%s)",
                            [code])
        applied = sum(int(r["n"]) for r in ref_rows)
        active = sum(int(r["n"]) for r in ref_rows if r["status"] in ("wrapped", "matched", "active"))
        referral = {"code": code, "link": ref_link(code),
                    "qr_url": f"/api/wrapmiles/qr?ref={code}",
                    "driver_signups": applied, "drivers_active": active,
                    "sponsor_signups": int((ref_sponsors or [{"n": 0}])[0]["n"])}
        matches = db.q("""SELECT m.id, m.status, m.wrapped_at, c.name AS campaign_name,
                                 c.zone, c.coverage, c.rate_cents_per_mile, c.flat_cents_month,
                                 c.cap_miles, c.start_date, c.end_date, c.status AS campaign_status
                          FROM wm_matches m JOIN wm_campaigns c ON c.id=m.campaign_id
                          WHERE m.driver_id=%s ORDER BY m.created_at DESC""", [t["i"]])
        mileage = db.q("""SELECT g.* FROM wm_mileage g JOIN wm_matches m ON m.id=g.match_id
                          WHERE m.driver_id=%s ORDER BY g.period DESC""", [t["i"]])
        db.close()
        earned = 0
        camp_by_match = {m["id"]: m for m in matches}
        for g in mileage:
            if g["status"] == "approved" and g["match_id"] in camp_by_match:
                earned += driver_period_cents(camp_by_match[g["match_id"]], g)
        return jsonify({"me": me, "matches": matches, "mileage": mileage,
                        "earned_cents_total": earned, "referral": referral})

    @app.route(P + "/driver/mileage", methods=["POST"])
    def wm_driver_mileage():
        t = require("driver")
        if not t:
            return jsonify({"error": "unauthorized"}), 401
        db = get_db()
        if not db:
            return _no_db()
        d = request.get_json(silent=True) or {}
        period = _clean(d.get("period"), 7)
        if not re.match(r"^\d{4}-\d{2}$", period):
            db.close()
            return jsonify({"error": "period must be YYYY-MM"}), 400
        try:
            match_id = int(d.get("match_id"))
            odo_start = max(0, int(d.get("odo_start") or 0))
            odo_end = max(0, int(d.get("odo_end") or 0))
            miles = int(d.get("miles") or (odo_end - odo_start))
        except (TypeError, ValueError):
            db.close()
            return jsonify({"error": "bad numbers"}), 400
        if miles <= 0 or miles > 20000:
            db.close()
            return jsonify({"error": "miles out of range"}), 400
        own = db.q("SELECT id FROM wm_matches WHERE id=%s AND driver_id=%s", [match_id, t["i"]])
        if not own:
            db.close()
            return jsonify({"error": "not your campaign"}), 403
        try:
            db.q("""INSERT INTO wm_mileage (created_at,match_id,period,miles,odo_start,odo_end,note)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                 [now(), match_id, period, miles, odo_start, odo_end, _clean(d.get("note"), 1000)])
            db.commit()
        except Exception:
            db.q("""UPDATE wm_mileage SET miles=%s, odo_start=%s, odo_end=%s, note=%s,
                    status='submitted', miles_approved=0
                    WHERE match_id=%s AND period=%s AND status!='approved'""",
                 [miles, odo_start, odo_end, _clean(d.get("note"), 1000), match_id, period])
            db.commit()
        db.close()
        return jsonify({"ok": True})

    # ---------------- sponsor ----------------

    @app.route(P + "/sponsor/me", methods=["GET"])
    def wm_sponsor_me():
        t = require("sponsor")
        if not t:
            return jsonify({"error": "unauthorized"}), 401
        db = get_db()
        if not db:
            return _no_db()
        me = db.q("SELECT id, company, contact, email, status FROM wm_sponsors WHERE id=%s", [t["i"]])
        if not me:
            db.close()
            return jsonify({"error": "not found"}), 404
        camps = db.q("SELECT * FROM wm_campaigns WHERE sponsor_id=%s ORDER BY created_at DESC", [t["i"]])
        out_camps = []
        for c in camps:
            vehicles = db.q("""SELECT m.id AS match_id, m.status, m.wrapped_at,
                                      d.vehicle, d.city_zip, d.name
                               FROM wm_matches m JOIN wm_drivers d ON d.id=m.driver_id
                               WHERE m.campaign_id=%s""", [c["id"]])
            for v in vehicles:
                # sponsors see first name + vehicle only
                v["driver"] = (v.pop("name") or "").split(" ")[0]
            periods = db.q("""SELECT g.period, SUM(g.miles_approved) AS miles
                              FROM wm_mileage g JOIN wm_matches m ON m.id=g.match_id
                              WHERE m.campaign_id=%s AND g.status='approved'
                              GROUP BY g.period ORDER BY g.period DESC""", [c["id"]])
            for p in periods:
                p["miles"] = int(p["miles"] or 0)
                p["est_impressions"] = p["miles"] * EST_IMPRESSIONS_PER_MILE
            out_camps.append({"campaign": c, "vehicles": vehicles, "periods": periods})
        db.close()
        return jsonify({"me": me[0], "campaigns": out_camps,
                        "impressions_note": f"Impressions are ESTIMATES at "
                                            f"{EST_IMPRESSIONS_PER_MILE}/verified mile "
                                            f"(industry OOH benchmark). Verified miles are measured."})

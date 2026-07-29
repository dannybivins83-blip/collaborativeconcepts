"""Offline tests for the Adometr portals API (api/adometr.py).

No network, no Postgres — runs the full flow against a temp sqlite file:
apply → admin triage → access codes → campaign → match → mileage → approval →
ledger → driver + sponsor portal payloads.  Run:  python3 _adometr_tests.py
"""

import json
import os
import sys
import tempfile

os.environ["WRAPMILES_DB_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
os.environ["WRAPMILES_ADMIN_KEY"] = "test-admin-key"
os.environ["SESSION_SECRET"] = "test-secret"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from api.adometr import register_adometr_routes

app = Flask(__name__)
register_adometr_routes(app)
client = app.test_client()

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f" FAIL {name} {extra}")


def j(res):
    return json.loads(res.data)


def auth(token):
    return {"Authorization": "Bearer " + token}


print("== status ==")
r = client.get("/api/adometr/status")
check("status 200", r.status_code == 200)
check("db configured", j(r)["db"] is True)
check("admin key set", j(r)["admin_key_set"] is True)

print("== intake ==")
r = client.post("/api/adometr/apply", json={
    "name": "Pool Guy Pete", "phone": "561-555-0001", "email": "pete@example.com",
    "city_zip": "Lake Worth 33460", "asset_type": "Car / SUV / Truck / Van (paid per mile)",
    "vehicle": "2019 Ford F-150 white", "monthly_miles": "1,500-2,500",
    "main_routes": "City & suburban streets", "daytime_parking": "Busy public lot / street",
    "wrap_coverage": "Full wrap (top pay)", "referred_by": ""})
check("driver apply 200", r.status_code == 200, r.data)
r = client.post("/api/adometr/apply", json={"email": "pete@example.com",
                                              "name": "Pete Updated", "vehicle": "2019 F-150"})
check("duplicate apply upserts", r.status_code == 200, r.data)
r = client.post("/api/adometr/apply", json={"email": "not-an-email"})
check("bad email rejected", r.status_code == 400)
r = client.post("/api/adometr/apply", json={"email": "bot@x.com", "_honey": "gotcha"})
check("honeypot swallowed", r.status_code == 200)

r = client.post("/api/adometr/inquiry", json={
    "company": "Delray Smiles Dental", "name": "Dr. Ray", "email": "ray@example.com",
    "phone": "561-555-0002", "budget": "$2,500-$10,000", "fleet_size": "1-5"})
check("sponsor inquiry 200", r.status_code == 200, r.data)

print("== admin auth ==")
r = client.post("/api/adometr/admin/login", json={"key": "wrong"})
check("wrong admin key 401", r.status_code == 401)
r = client.post("/api/adometr/admin/login", json={"key": "test-admin-key"})
check("admin login 200", r.status_code == 200)
admin = j(r)["token"]
r = client.get("/api/adometr/admin/drivers")
check("no token 401", r.status_code == 401)
r = client.get("/api/adometr/admin/drivers", headers=auth("garbage.token"))
check("bad token 401", r.status_code == 401)

print("== admin triage ==")
r = client.get("/api/adometr/admin/drivers", headers=auth(admin))
drivers = j(r)["drivers"]
check("driver listed", len(drivers) == 1 and drivers[0]["email"] == "pete@example.com")
check("honeypot bot not stored", all(d["email"] != "bot@x.com" for d in drivers))
did = drivers[0]["id"]
r = client.patch(f"/api/adometr/admin/drivers/{did}", headers=auth(admin),
                 json={"status": "wrap_ready", "score": "A", "reset_code": True})
check("driver patch + code", r.status_code == 200 and j(r)["access_code"], r.data)
driver_code = j(r)["access_code"]
r = client.patch(f"/api/adometr/admin/drivers/{did}", headers=auth(admin),
                 json={"status": "not-a-status"})
check("bad driver status 400", r.status_code == 400)

r = client.get("/api/adometr/admin/sponsors", headers=auth(admin))
sid = j(r)["sponsors"][0]["id"]
r = client.patch(f"/api/adometr/admin/sponsors/{sid}", headers=auth(admin),
                 json={"status": "signed", "reset_code": True})
sponsor_code = j(r)["access_code"]
check("sponsor patch + code", r.status_code == 200 and sponsor_code)

print("== campaign + match ==")
r = client.post("/api/adometr/admin/campaigns", headers=auth(admin), json={
    "sponsor_id": sid, "name": "Delray Smiles Spring", "zone": "Delray/Boynton",
    "cars_needed": 2, "coverage": "Partial", "rate_per_mile": 0.22,
    "flat_monthly": 0, "cap_miles": 2000, "start_date": "2026-08-01", "end_date": "2026-11-01"})
check("campaign created", r.status_code == 200, r.data)
r = client.get("/api/adometr/admin/campaigns", headers=auth(admin))
camp = j(r)["campaigns"][0]
check("rate stored in cents", camp["rate_cents_per_mile"] == 22)
cid = camp["id"]
r = client.post("/api/adometr/admin/matches", headers=auth(admin),
                json={"campaign_id": cid, "driver_id": did})
check("match created", r.status_code == 200, r.data)
r = client.post("/api/adometr/admin/matches", headers=auth(admin),
                json={"campaign_id": cid, "driver_id": did})
check("duplicate match 409", r.status_code == 409)
r = client.get("/api/adometr/admin/campaigns", headers=auth(admin))
mid = j(r)["campaigns"][0]["matches"][0]["id"]
r = client.patch(f"/api/adometr/admin/matches/{mid}", headers=auth(admin),
                 json={"status": "active", "wrapped_at": "2026-08-05"})
check("match activated", r.status_code == 200)
r = client.patch(f"/api/adometr/admin/campaigns/{cid}", headers=auth(admin),
                 json={"status": "active"})
check("campaign activated", r.status_code == 200)

print("== driver portal ==")
r = client.post("/api/adometr/login", json={"role": "driver",
                                              "email": "pete@example.com", "code": "WRONGCODE"})
check("wrong driver code 401", r.status_code == 401)
r = client.post("/api/adometr/login", json={"role": "driver",
                                              "email": "pete@example.com", "code": driver_code})
check("driver login", r.status_code == 200, r.data)
dtok = j(r)["token"]
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
me = j(r)
check("driver/me ok", r.status_code == 200 and me["me"]["email"] == "pete@example.com")
check("driver sees campaign", me["matches"][0]["campaign_name"] == "Delray Smiles Spring")
check("access code not leaked", "access_code" not in me["me"])
match_id = me["matches"][0]["id"]
r = client.post("/api/adometr/driver/mileage", headers=auth(dtok), json={
    "match_id": match_id, "period": "2026-08", "odo_start": 41000, "odo_end": 42800,
    "miles": 1800, "note": "mostly Atlantic Ave + I-95"})
check("mileage submitted", r.status_code == 200, r.data)
r = client.post("/api/adometr/driver/mileage", headers=auth(dtok), json={
    "match_id": match_id, "period": "bad", "miles": 100})
check("bad period 400", r.status_code == 400)
r = client.post("/api/adometr/driver/mileage", headers=auth(dtok), json={
    "match_id": 99999, "period": "2026-08", "miles": 100})
check("foreign match 403", r.status_code == 403)
r = client.post("/api/adometr/driver/mileage", headers=auth(admin), json={
    "match_id": match_id, "period": "2026-08", "miles": 100})
check("admin token not driver 401", r.status_code == 401)

print("== approval + money ==")
r = client.get("/api/adometr/admin/mileage", headers=auth(admin))
gid = j(r)["mileage"][0]["id"]
r = client.patch(f"/api/adometr/admin/mileage/{gid}", headers=auth(admin),
                 json={"status": "approved", "miles_approved": 1800})
check("mileage approved", r.status_code == 200)
r = client.get("/api/adometr/admin/ledger", headers=auth(admin))
ledger = j(r)["ledger"]
check("ledger row", len(ledger) == 1)
check("owed = 1800mi x $0.22 = $396", ledger[0]["owed_cents"] == 39600,
      ledger[0].get("owed_cents"))
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
check("driver earned total", j(r)["earned_cents_total"] == 39600, j(r)["earned_cents_total"])

print("== cap enforcement ==")
r = client.post("/api/adometr/driver/mileage", headers=auth(dtok), json={
    "match_id": match_id, "period": "2026-09", "miles": 3000})
check("september submitted", r.status_code == 200)
r = client.get("/api/adometr/admin/mileage", headers=auth(admin))
gid2 = [m for m in j(r)["mileage"] if m["period"] == "2026-09"][0]["id"]
client.patch(f"/api/adometr/admin/mileage/{gid2}", headers=auth(admin),
             json={"status": "approved", "miles_approved": 3000})
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
# 2026-09 pays capped 2000 mi x 22c = 44000; plus august 39600
check("cap limits payout to 2000 mi", j(r)["earned_cents_total"] == 39600 + 44000,
      j(r)["earned_cents_total"])

print("== sponsor portal ==")
r = client.post("/api/adometr/login", json={"role": "sponsor",
                                              "email": "ray@example.com", "code": sponsor_code})
check("sponsor login", r.status_code == 200, r.data)
stok = j(r)["token"]
r = client.get("/api/adometr/sponsor/me", headers=auth(stok))
sp = j(r)
check("sponsor/me ok", r.status_code == 200 and sp["me"]["company"] == "Delray Smiles Dental")
camp0 = sp["campaigns"][0]
check("sponsor sees fleet", camp0["vehicles"][0]["vehicle"].startswith("2019"))
check("sponsor sees first name only", camp0["vehicles"][0]["driver"] == "Pete")
check("driver email hidden from sponsor", "email" not in camp0["vehicles"][0])
periods = {p["period"]: p for p in camp0["periods"]}
check("verified miles reported", periods["2026-08"]["miles"] == 1800)
check("impressions estimated at 50/mi", periods["2026-08"]["est_impressions"] == 90000)
check("impressions labeled estimate", "ESTIMATE" in sp["impressions_note"].upper())
r = client.get("/api/adometr/sponsor/me", headers=auth(dtok))
check("driver token not sponsor 401", r.status_code == 401)

print("== referral links ==")
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
ref = j(r).get("referral") or {}
check("ref code generated", bool(ref.get("code")) and ref["code"].startswith("POOL"),
      ref.get("code"))
check("ref link built", ref.get("link", "").endswith("/adometr?ref=" + ref.get("code", "")))
check("qr url present", ref.get("qr_url", "").startswith("/api/adometr/qr"))
check("zero referrals initially", ref["driver_signups"] == 0 and ref["sponsor_signups"] == 0)

r = client.post("/api/adometr/apply", json={
    "name": "Referred Rita", "email": "rita@example.com", "vehicle": "2021 Kia Soul",
    "referred_by": ref["code"].lower()})   # case-insensitive credit
check("referred driver applies", r.status_code == 200)
r = client.post("/api/adometr/inquiry", json={
    "company": "Rita's Gym", "email": "gym@example.com", "referred_by": ref["code"]})
check("referred sponsor applies", r.status_code == 200)

r = client.get("/api/adometr/driver/me", headers=auth(dtok))
ref2 = j(r)["referral"]
check("driver signup credited", ref2["driver_signups"] == 1, ref2)
check("sponsor signup credited", ref2["sponsor_signups"] == 1, ref2)
check("not active yet", ref2["drivers_active"] == 0)

r = client.get("/api/adometr/admin/drivers", headers=auth(admin))
rows = {d["email"]: d for d in j(r)["drivers"]}
check("admin sees ref codes", bool(rows["pete@example.com"]["ref_code"]))
check("admin sees who referred rita",
      rows["rita@example.com"]["referred_by"].upper() == ref["code"])
check("new applicant gets own code", bool(rows["rita@example.com"]["ref_code"]))

r = client.get("/api/adometr/qr?ref=" + ref["code"])
check("qr endpoint", r.status_code == 200 and r.data[:4] == b"\x89PNG", r.status_code)
r = client.get("/api/adometr/qr?ref=<script>")
check("qr rejects junk", r.status_code == 400)

print("== docs checklist ==")
r = client.patch(f"/api/adometr/admin/drivers/{did}", headers=auth(admin),
                 json={"docs": {"license_ok": True, "insurance_ok": True,
                                "mvr_consent": True, "bogus_key": True}})
check("docs saved", r.status_code == 200)
r = client.get("/api/adometr/admin/drivers", headers=auth(admin))
docs = json.loads({d["id"]: d for d in j(r)["drivers"]}[did]["docs"])
check("docs round-trip", docs["license_ok"] is True and docs["insurance_ok"] is True)
check("unknown keys dropped", "bogus_key" not in docs)
check("mvr_pulled defaults false", docs["mvr_pulled"] is False)
check("doc_keys served", "mvr_consent" in j(r)["doc_keys"])

print("== photos ==")
import base64 as b64
tiny_png = b64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c62f8cfc0f01f00050001ff5ccc2a"
    "590000000049454e44ae426082")).decode()
data_url = "data:image/png;base64," + tiny_png
r = client.post("/api/adometr/driver/photos", headers=auth(dtok),
                json={"kind": "odometer", "period": "2026-07", "image": data_url})
check("photo uploaded", r.status_code == 200, r.data)
r = client.post("/api/adometr/driver/photos", headers=auth(dtok),
                json={"kind": "selfie", "image": data_url})
check("bad kind rejected", r.status_code == 400)
r = client.post("/api/adometr/driver/photos", headers=auth(dtok),
                json={"kind": "vehicle", "image": "data:text/html;base64,PGI+"})
check("non-image rejected", r.status_code == 400)
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
photos = j(r)["photos"]
check("photo listed in driver/me", len(photos) == 1 and photos[0]["kind"] == "odometer")
pid = photos[0]["id"]
r = client.get(f"/api/adometr/photos/{pid}", headers=auth(dtok))
check("owner fetches photo", r.status_code == 200 and r.data[:4] == b"\x89PNG")
r = client.get(f"/api/adometr/photos/{pid}?t={admin}")
check("admin fetches via ?t=", r.status_code == 200)
r = client.get(f"/api/adometr/photos/{pid}")
check("anon photo denied", r.status_code == 401)
r = client.post("/api/adometr/login", json={"role": "driver",
                                              "email": "rita@example.com", "code": "X"})
r = client.get("/api/adometr/admin/photos?driver_id=" + str(did), headers=auth(admin))
check("admin photo list", len(j(r)["photos"]) == 1)

print("== gps per-car toggle ==")
r = client.patch(f"/api/adometr/admin/matches/{mid}", headers=auth(admin),
                 json={"gps_enabled": True})
check("gps toggled on", r.status_code == 200, r.data)
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
check("driver sees gps flag", j(r)["matches"][0]["gps_enabled"] in (1, True))
r = client.get("/api/adometr/sponsor/me", headers=auth(stok))
check("sponsor sees gps flag",
      j(r)["campaigns"][0]["vehicles"][0]["gps_enabled"] in (1, True))
r = client.patch(f"/api/adometr/admin/matches/{mid}", headers=auth(admin),
                 json={"gps_enabled": False})
r = client.get("/api/adometr/driver/me", headers=auth(dtok))
check("gps toggled off", j(r)["matches"][0]["gps_enabled"] in (0, False))

print("== ambassadors ==")
r = client.post("/api/adometr/admin/ambassadors", headers=auth(admin),
                json={"name": "Chase Burns", "territory": "Melbourne / Space Coast",
                      "phone": "321-555-0100"})
check("ambassador created (no email needed)", r.status_code == 200, r.data)
chase_code = j(r)["ref_code"]
check("ambassador code from name", chase_code.startswith("CHASE"))
check("ambassador link built", j(r)["link"].endswith("?ref=" + chase_code))
r = client.post("/api/adometr/admin/ambassadors", headers=auth(admin),
                json={"name": "Jonathan Simpson", "email": "jon@example.com",
                      "territory": "Orlando"})
check("second ambassador", r.status_code == 200)
r = client.post("/api/adometr/admin/ambassadors", headers=auth(admin),
                json={"name": "Dup Jon", "email": "jon@example.com"})
check("duplicate ambassador email 409", r.status_code == 409)
r = client.post("/api/adometr/admin/ambassadors", headers=auth(admin), json={"email": "x@y.co"})
check("nameless ambassador 400", r.status_code == 400)

client.post("/api/adometr/apply", json={"name": "Melbourne Mike",
                                        "email": "mike-melb@example.com",
                                        "vehicle": "2020 Tacoma",
                                        "referred_by": chase_code.lower()})
r = client.get("/api/adometr/admin/ambassadors", headers=auth(admin))
ambs = {a["name"]: a for a in j(r)["ambassadors"]}
check("ambassador signup credited", ambs["Chase Burns"]["driver_signups"] == 1,
      ambs["Chase Burns"])
check("ambassador qr url", ambs["Chase Burns"]["qr_url"].startswith("/api/adometr/qr"))
aid = ambs["Jonathan Simpson"]["id"]
r = client.patch(f"/api/adometr/admin/ambassadors/{aid}", headers=auth(admin),
                 json={"status": "paused", "notes": "on vacation"})
check("ambassador patched", r.status_code == 200)
r = client.patch(f"/api/adometr/admin/ambassadors/{aid}", headers=auth(admin),
                 json={"status": "not-real"})
check("bad ambassador status 400", r.status_code == 400)
r = client.get("/api/adometr/admin/ambassadors")
check("ambassadors need admin auth", r.status_code == 401)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

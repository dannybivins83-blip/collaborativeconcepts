"""Seed the LIVE Adometr database with clearly-marked TEST data.

Creates 5 test drivers, 5 test sponsors, 5 campaigns, matches, and mileage
(submitted + approved) so every portal screen shows real rows. All names are
prefixed "TEST" and all emails are dannybivins83+wmtest-*@gmail.com aliases,
so they're unmistakable and easy to filter/reject later (there is no delete
endpoint; retire test rows by setting status rejected/churned in the admin UI).

Run from any machine that can reach the site (NOT the cloud sandbox):

    WRAPMILES_ADMIN_KEY=<the key> python3 _adometr_seed.py

Optional: WRAPMILES_BASE=https://collaborativeconceptsfl.com (default).
Prints every access code at the end so Danny can log into the driver/sponsor
portals as each test user. Idempotent: re-running upserts by email.
"""

import json
import os
import sys
import urllib.request

BASE = os.environ.get("WRAPMILES_BASE", "https://collaborativeconceptsfl.com").rstrip("/")
KEY = os.environ.get("WRAPMILES_ADMIN_KEY", "")
API = BASE + "/api/adometr"

if not KEY:
    sys.exit("Set WRAPMILES_ADMIN_KEY (never hardcode it).")


def call(path, payload=None, token=None, method=None):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


DRIVERS = [
    dict(name="TEST Maria Santos", phone="561-555-0101",
         email="dannybivins83+wmtest-d1@gmail.com", city_zip="West Palm Beach 33401",
         asset_type="Car / SUV / Truck / Van (paid per mile)", vehicle="2021 Toyota RAV4, white",
         monthly_miles="1,500-2,500", main_routes="I-95 / Turnpike / toll roads",
         daytime_parking="Busy public lot / street", wrap_coverage="Full wrap (top pay)",
         referred_by=""),
    dict(name="TEST Big Mike Johnson", phone="561-555-0102",
         email="dannybivins83+wmtest-d2@gmail.com", city_zip="Lake Worth 33460",
         asset_type="Car / SUV / Truck / Van (paid per mile)", vehicle="2018 Ford F-250, silver",
         monthly_miles="2,500+", main_routes="City & suburban streets",
         daytime_parking="Busy public lot / street", wrap_coverage="Partial wrap",
         referred_by=""),
    dict(name="TEST Keisha Brown", phone="954-555-0103",
         email="dannybivins83+wmtest-d3@gmail.com", city_zip="Fort Lauderdale 33301",
         asset_type="Car / SUV / Truck / Van (paid per mile)", vehicle="2022 Honda Civic, blue",
         monthly_miles="800-1,500", main_routes="Mixed",
         daytime_parking="Mixed", wrap_coverage="Partial wrap",
         referred_by=""),
    dict(name="TEST Carlos Rivera", phone="305-555-0104",
         email="dannybivins83+wmtest-d4@gmail.com", city_zip="Miami 33130",
         asset_type="Car / SUV / Truck / Van (paid per mile)", vehicle="2020 Ram ProMaster van, white",
         monthly_miles="2,500+", main_routes="I-95 / Turnpike / toll roads",
         daytime_parking="Busy public lot / street", wrap_coverage="Full wrap (top pay)",
         referred_by=""),
    dict(name="TEST Golf Cart Gary", phone="561-555-0105",
         email="dannybivins83+wmtest-d5@gmail.com", city_zip="Delray Beach 33444",
         asset_type="Golf cart / LSV (flat monthly)", vehicle="2023 Club Car Onward, black",
         monthly_miles="N/A — golf cart / trailer / boat", main_routes="City & suburban streets",
         daytime_parking="Busy public lot / street", wrap_coverage="Full wrap (top pay)",
         referred_by=""),
]

SPONSORS = [
    dict(company="TEST Tony's Pizza Palace", name="Tony Marinara", phone="561-555-0201",
         email="dannybivins83+wmtest-s1@gmail.com", budget="$2,500-$10,000", fleet_size="1-5",
         zones="Lake Worth / Lantana", referred_by=""),
    dict(company="TEST Gold Coast Injury Law", name="Sarah Goldstein", phone="561-555-0202",
         email="dannybivins83+wmtest-s2@gmail.com", budget="$10,000-$50,000", fleet_size="5-15",
         zones="I-95 corridor PBC", referred_by=""),
    dict(company="TEST Iron Temple Gym", name="Dave Flex", phone="954-555-0203",
         email="dannybivins83+wmtest-s3@gmail.com", budget="Under $2,500", fleet_size="1-5",
         zones="Fort Lauderdale", referred_by=""),
    dict(company="TEST SunShield Roofing", name="Roberta Shingle", phone="561-555-0204",
         email="dannybivins83+wmtest-s4@gmail.com", budget="$2,500-$10,000", fleet_size="1-5",
         zones="Boca / Delray", referred_by=""),
    dict(company="TEST Delray Downtown Alliance", name="Pat Commissioner", phone="561-555-0205",
         email="dannybivins83+wmtest-s5@gmail.com", budget="$2,500-$10,000", fleet_size="1-5",
         zones="Atlantic Ave district", referred_by=""),
]

# (campaign, sponsor-email, driver-emails, rate $/mi, flat $/mo, months of mileage to seed)
CAMPAIGNS = [
    ("TEST Tony's Pizza — Lake Worth loop", "dannybivins83+wmtest-s1@gmail.com",
     ["dannybivins83+wmtest-d2@gmail.com"], 0.18, 0, [("2026-06", 1900, 1800), ("2026-07", 2300, 2000)]),
    ("TEST Gold Coast Law — I-95 swarm", "dannybivins83+wmtest-s2@gmail.com",
     ["dannybivins83+wmtest-d1@gmail.com", "dannybivins83+wmtest-d4@gmail.com"],
     0.28, 0, [("2026-07", 1600, 1600)]),
    ("TEST Iron Temple — FTL partial", "dannybivins83+wmtest-s3@gmail.com",
     ["dannybivins83+wmtest-d3@gmail.com"], 0.15, 0, [("2026-07", 1100, 1050)]),
    ("TEST SunShield — Boca/Delray", "dannybivins83+wmtest-s4@gmail.com",
     [], 0.22, 0, []),  # draft campaign, no cars yet — shows the matching flow
    ("TEST Delray Alliance — Atlantic Ave cart", "dannybivins83+wmtest-s5@gmail.com",
     ["dannybivins83+wmtest-d5@gmail.com"], 0.0, 350.0, [("2026-07", 240, 240)]),
]


def main():
    print(f"Seeding {BASE} ...")
    for d in DRIVERS:
        s, r = call("/apply", d)
        print(f"  driver {d['name']}: {s}")
    for sp in SPONSORS:
        s, r = call("/inquiry", sp)
        print(f"  sponsor {sp['company']}: {s}")

    s, r = call("/admin/login", {"key": KEY})
    if s != 200:
        sys.exit(f"admin login failed: {s} {r}")
    adm = r["token"]

    _, dr = call("/admin/drivers", token=adm)
    _, sr = call("/admin/sponsors", token=adm)
    drivers = {d["email"]: d for d in dr["drivers"]}
    sponsors = {x["email"]: x for x in sr["sponsors"]}

    codes = {}
    for d in DRIVERS:
        row = drivers[d["email"]]
        s, r = call(f"/admin/drivers/{row['id']}",
                    {"status": "wrap_ready", "score": "A", "reset_code": True}, adm, "PATCH")
        codes[d["name"]] = ("driver", d["email"], r.get("access_code"))
    for sp in SPONSORS:
        row = sponsors[sp["email"]]
        s, r = call(f"/admin/sponsors/{row['id']}",
                    {"status": "signed", "reset_code": True}, adm, "PATCH")
        codes[sp["company"]] = ("sponsor", sp["email"], r.get("access_code"))

    for name, sp_email, drv_emails, rate, flat, periods in CAMPAIGNS:
        s, r = call("/admin/campaigns", {
            "sponsor_id": sponsors[sp_email]["id"], "name": name,
            "zone": name.split("—")[-1].strip(), "cars_needed": max(1, len(drv_emails)),
            "coverage": "Flat placement" if flat else "Partial",
            "rate_per_mile": rate, "flat_monthly": flat, "cap_miles": 2000,
            "start_date": "2026-06-01", "end_date": "2026-12-01"}, adm)
        print(f"  campaign {name}: {s}")
        _, cr = call("/admin/campaigns", token=adm)
        camp = next(c for c in cr["campaigns"] if c["name"] == name)
        if drv_emails:
            call(f"/admin/campaigns/{camp['id']}", {"status": "active"}, adm, "PATCH")
        for de in drv_emails:
            call("/admin/matches", {"campaign_id": camp["id"], "driver_id": drivers[de]["id"]}, adm)
        _, cr = call("/admin/campaigns", token=adm)
        camp = next(c for c in cr["campaigns"] if c["name"] == name)
        for m in camp["matches"]:
            call(f"/admin/matches/{m['id']}", {"status": "active", "wrapped_at": "2026-06-05"}, adm, "PATCH")
            # driver submits mileage via their own login, then admin approves
            demail = m["driver_email"]
            dname = next(d["name"] for d in DRIVERS if d["email"] == demail)
            _, lg = call("/login", {"role": "driver", "email": demail, "code": codes[dname][2]})
            dtok = lg.get("token")
            for period, claimed, approved in periods:
                call("/driver/mileage", {"match_id": m["id"], "period": period,
                                         "miles": claimed, "note": "TEST seed"}, dtok)
        _, gr = call("/admin/mileage", token=adm)
        for g in gr["mileage"]:
            if g["status"] == "submitted" and g["campaign_name"] == name:
                approved = next((a for p, c, a in periods if p == g["period"]), None)
                if approved is not None:
                    call(f"/admin/mileage/{g['id']}",
                         {"status": "approved", "miles_approved": approved}, adm, "PATCH")

    print("\n=== PORTAL LOGINS (give these to Danny) ===")
    for who, (role, email, code) in codes.items():
        print(f"  {role:8} {who:38} {email:42} code: {code}")
    print("\nDone. Admin panel should now show 5 drivers, 5 sponsors, 5 campaigns,")
    print("matches, approved mileage, and a ledger with owed amounts.")


if __name__ == "__main__":
    main()

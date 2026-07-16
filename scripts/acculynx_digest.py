#!/usr/bin/env python3
"""AccuLynx daily job-file digest for Danny Bivins (SeaBreeze Roofing).

Pulls recently-modified jobs from the AccuLynx API v2 and prints a markdown
digest of job-file activity: status changes, new documents, and jobs with
missing paperwork. Designed to run headlessly from a scheduled Claude Code
Routine.

Setup (one-time, admin required):
  1. In AccuLynx: user icon -> Company Settings -> API -> generate an API key.
  2. Add it to the Claude Code environment as ACCULYNX_API_KEY
     (claude.ai/code -> environment settings -> environment variables).

Usage:
  ACCULYNX_API_KEY=... python3 scripts/acculynx_digest.py [--days 1]

The script is defensive: AccuLynx API surface varies by plan/version, so any
endpoint that 404s is reported rather than fatal, and --probe prints the API
root so the integration can be adjusted on first run.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("ACCULYNX_API_BASE", "https://api.acculynx.com/api/v2")
KEY = os.environ.get("ACCULYNX_API_KEY", "").strip()

# Danny's job-number prefix; leads/jobs assigned to these reps also match.
REP_NAMES = ("danny bivins",)


def _get(path, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as e:
        return None, f"{e.code} {e.reason} for GET {path}"
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
        return None, f"network error for GET {path}: {e}"


def _items(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    return payload.get("items") or payload.get("data") or []


def _mine(job):
    reps = json.dumps(job).lower()
    return any(name in reps for name in REP_NAMES)


def main():
    if not KEY:
        print("ERROR: ACCULYNX_API_KEY is not set. See setup notes in this "
              "script's docstring.")
        return 2

    days = 1
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    if "--probe" in sys.argv:
        root, err = _get("")
        print(json.dumps(root, indent=2) if root else f"probe failed: {err}")
        return 0

    errors = []
    jobs, err = _get("/jobs", {
        "sortBy": "modifiedDate", "sortDirection": "descending",
        "pageSize": 100, "pageStartIndex": 0,
    })
    if err:
        errors.append(err)

    print(f"# AccuLynx digest — since {since}\n")
    mine, recent = [], []
    for job in _items(jobs):
        modified = (job.get("modifiedDate") or job.get("modifiedAt") or "")[:10]
        if modified and modified < since:
            continue
        recent.append(job)
        if _mine(job):
            mine.append(job)

    if not recent and errors:
        print("Could not list jobs from the API:\n")
        for e in errors:
            print(f"- {e}")
        print("\nRun with --probe to inspect the API root, or check the key's "
              "permissions.")
        return 1

    print(f"{len(recent)} job(s) modified in the last {days} day(s); "
          f"{len(mine)} belong to Danny.\n")

    for job in mine:
        jid = job.get("id") or job.get("jobId")
        number = job.get("jobNumber") or job.get("number") or "?"
        name = (job.get("jobName") or job.get("name")
                or job.get("contactName") or "?")
        status = (job.get("milestone") or {}).get("name") if isinstance(
            job.get("milestone"), dict) else job.get("milestone") or job.get("status")
        print(f"## {number} — {name}")
        print(f"- Status/milestone: {status}")
        if jid:
            docs, derr = _get(f"/jobs/{jid}/documents", {"pageSize": 25})
            if derr:
                errors.append(derr)
            else:
                names = [d.get("fileName") or d.get("name") or "?"
                         for d in _items(docs)]
                print(f"- Documents on file ({len(names)}): "
                      + (", ".join(names[:15]) or "NONE — flag this"))
        print()

    if errors:
        print("## API warnings\n")
        for e in sorted(set(errors)):
            print(f"- {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

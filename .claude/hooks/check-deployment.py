#!/usr/bin/env python3
"""Verify each subdomain referenced in vercel.json is actually served from this repo.

Writes mismatched subdomains to .claude/state/mismatched-subdomains for the
PreToolUse hook to consume. Prints a human-readable summary to stdout so the
agent (and the user) see it at session start.
"""
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

REPO   = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
MARKER = b'x-claude-source-repo'
EXPECT = b'dannybivins83-blip/collaborativeconcepts'
STATE  = REPO / ".claude" / "state" / "mismatched-subdomains"


def hosts_from_vercel():
    """Map host -> destination folder, as declared in vercel.json."""
    try:
        v = json.loads((REPO / "vercel.json").read_text())
    except FileNotFoundError:
        return {}
    out = {}
    for section in ("rewrites", "redirects"):
        for rule in v.get(section, []) or []:
            for h in (rule.get("has") or []):
                if h.get("type") != "host" or not h.get("value"):
                    continue
                host = h["value"]
                dest = (rule.get("destination") or "").lstrip("/")
                if not dest:
                    continue
                # Strip trailing wildcards/captures like "$1"
                folder = re.sub(r"/?\$\d+$", "", dest).rstrip("/")
                if not folder:
                    continue
                out.setdefault(host, folder)
    return out


def fetch(host, timeout=8):
    """Return (status, body, title) for https://host/ or (None, b'', '') on error."""
    url = f"https://{host}/"
    req = urllib.request.Request(url, headers={
        "user-agent": "claude-code-deployment-guardrail/1.0",
        "accept": "text/html,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(64 * 1024)  # only need the head
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
        body = b""
    except Exception:
        return None, b"", ""
    m = re.search(rb"<title[^>]*>([^<]+)", body, re.IGNORECASE)
    title = (m.group(1).decode("utf-8", errors="replace").strip()[:70]) if m else ""
    return status, body, title


def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text("")

    hosts = hosts_from_vercel()
    if not hosts:
        return 0

    print()
    print("── Deployment guardrail · subdomain ↔ project check ──")
    mismatches = []
    unknown   = []
    for host, folder in sorted(hosts.items()):
        status, body, title = fetch(host)
        title_str = f"[{title}]" if title else ""
        if status is None:
            print(f"  ? {host}  →  unreachable from this container — UNKNOWN")
            unknown.append(host)
            continue
        if status >= 400 and not body:
            print(f"  ? {host}  →  HTTP {status} with no body — UNKNOWN  {title_str}")
            unknown.append(host)
            continue
        served_by_this_repo = MARKER in body and EXPECT in body
        if served_by_this_repo:
            print(f"  ✓ {host}  →  this repo  {title_str}")
        else:
            print(f"  ✗ {host}  →  NOT served from this repo  {title_str}")
            mismatches.append((host, folder))

    if unknown:
        print()
        print("  Note: unreachable hosts are NOT flagged — only confirmed mismatches block.")

    if mismatches:
        with STATE.open("w") as f:
            for host, folder in mismatches:
                f.write(f"{host}|{folder}\n")
        print()
        print("‼️  STOP before editing files in these folders — they are NOT live")
        print("    anywhere served by this Vercel project:")
        for host, folder in mismatches:
            print(f"    · /{folder}/  (vercel.json maps {host} here, but the live")
            print(f"      site at {host} is bound to a DIFFERENT project)")
        print()
        print("  If asked to edit anything in those folders, FIRST confirm with the")
        print("  user whether to repoint the subdomain to this Vercel project, OR")
        print("  get repo access for the project that actually serves that subdomain.")
        print()
        print("  The PreToolUse hook (.claude/hooks/pre-tool-use.sh) will refuse")
        print("  Edit/Write calls into those folders until this is resolved.")
        print("───────────────────────────────────────────────────────────")
    else:
        print("  All subdomains match — safe to edit.")
        print("───────────────────────────────────────────────────────────")
    return 0


if __name__ == "__main__":
    sys.exit(main())

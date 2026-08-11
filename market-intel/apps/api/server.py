#!/usr/bin/env python3
"""Stdlib dev server — runs with zero installed dependencies.

    python3 apps/api/server.py --db sqlite:///data/dev.db --port 8787

It serves the same handlers as the FastAPI target (`fastapi_app.py`) plus the
static stock page from apps/web, so the whole slice is demonstrable on a
machine with nothing but Python. This is the dev/proof server: FastAPI +
uvicorn is the production path.
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.api.handlers import dispatch          # noqa: E402
from packages import database                   # noqa: E402

WEB_DIR = ROOT / "apps" / "web"


class Handler(BaseHTTPRequestHandler):
    db_url = "sqlite:///data/dev.db"
    server_version = "MarketIntelDev/1.0"

    def _send(self, status, payload, content_type="application/json"):
        body = (json.dumps(payload, indent=2).encode() if content_type.startswith(
            "application/json") else payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            # A connection per request: SQLite handles this fine at dev scale
            # and it keeps the handler free of connection-pool concerns.
            with database.Database.open(self.db_url) as db:
                status, payload = dispatch(db, "GET", path, params)
            return self._send(status, payload)

        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())) or not target.is_file():
            return self._send(404, {"error": "not found"})
        ctype = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
                 ".css": "text/css", ".json": "application/json"}.get(
                     target.suffix, "application/octet-stream")
        return self._send(200, target.read_bytes(), ctype)

    def log_message(self, fmt, *args):
        if os.environ.get("MI_HTTP_LOG"):
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


def serve(db_url, port=8787, host="127.0.0.1"):
    Handler.db_url = db_url
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Market Intel dev server  http://{host}:{port}  (db={db_url})")
    print(f"  stock page : http://{host}:{port}/?ticker=NVDA")
    print(f"  api        : http://{host}:{port}/api/v1/health")
    return httpd


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("MI_DATABASE_URL",
                                                   "sqlite:///data/dev.db"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MI_PORT", 8787)))
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    httpd = serve(args.db, args.port, args.host)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

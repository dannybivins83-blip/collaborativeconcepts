# Local dev server: the real Flask API + the static dashboard, so /permits/ can be
# exercised end-to-end (Vercel does this split via vercel.json rewrites in prod).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))
from index import app  # noqa: E402
from flask import send_from_directory  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


@app.route("/permits/")
@app.route("/permits/index.html")
def _permits_page():
    return send_from_directory(os.path.join(ROOT, "permits"), "index.html")


@app.route("/<path:rest>")
def _static_any(rest):
    full = os.path.join(ROOT, rest)
    if os.path.isdir(full):
        return send_from_directory(full, "index.html")
    return send_from_directory(ROOT, rest)


if __name__ == "__main__":
    app.run(port=8330, debug=False, threaded=True)

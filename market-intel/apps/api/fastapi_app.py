"""FastAPI adapter — the production API target.

STATUS: written but NOT executed in this environment (fastapi/pydantic/uvicorn
are not installed here and there is no network to install them). Treat it as
unverified until `make api` runs green in a container. See docs/BUILD_STATUS.md.

It deliberately contains no business logic: every route delegates to the same
`handlers` functions the stdlib dev server uses, so the two can never drift.

    uvicorn apps.api.fastapi_app:app --reload --port 8000
"""
from typing import Optional

try:
    from fastapi import Depends, FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover - documented dependency gap
    raise SystemExit(
        "FastAPI is not installed. Use the stdlib dev server instead:\n"
        "  python3 apps/api/server.py --db sqlite:///data/dev.db\n"
        f"(original import error: {e})")

from apps.api.handlers import API_VERSION, dispatch
from packages import database

app = FastAPI(title="Market Intelligence Terminal API", version=API_VERSION,
              description="Entity/tag/signal intelligence over lawful public data.")


class Health(BaseModel):
    status: str
    version: str
    counts: dict
    data: dict


def get_db():
    db = database.Database.open()
    try:
        yield db
    finally:
        db.close()


def _call(db, path, params=None):
    status, payload = dispatch(db, "GET", path, params or {})
    if status >= 400:
        raise HTTPException(status_code=status, detail=payload.get("error"))
    return payload


@app.get("/api/v1/health", response_model=Health)
def health(db=Depends(get_db)):
    return _call(db, "/api/v1/health")


@app.get("/api/v1/data-health")
def data_health(db=Depends(get_db)):
    return _call(db, "/api/v1/data-health")


@app.get("/api/v1/search")
def search(q: str = Query(..., min_length=1), db=Depends(get_db)):
    return _call(db, "/api/v1/search", {"q": q})


@app.get("/api/v1/stocks")
def stocks(limit: int = 50, db=Depends(get_db)):
    return _call(db, "/api/v1/stocks", {"limit": limit})


@app.get("/api/v1/stocks/{ticker}")
def stock(ticker: str, db=Depends(get_db)):
    return _call(db, f"/api/v1/stocks/{ticker}")


@app.get("/api/v1/stocks/{ticker}/{section}")
def stock_section(ticker: str, section: str, limit: int = 100, db=Depends(get_db)):
    allowed = {"financials", "filings", "filing-changes", "tags", "signals",
               "score", "relationships"}
    if section not in allowed:
        raise HTTPException(404, f"unknown section '{section}'")
    return _call(db, f"/api/v1/stocks/{ticker}/{section}", {"limit": limit})


@app.get("/api/v1/themes")
def themes(db=Depends(get_db)):
    return _call(db, "/api/v1/themes")


@app.get("/api/v1/themes/{slug}")
def theme(slug: str, db=Depends(get_db)):
    return _call(db, f"/api/v1/themes/{slug}")


@app.get("/api/v1/signals")
def signals(db=Depends(get_db)):
    return _call(db, "/api/v1/signals")


@app.get("/api/v1/screener")
def screener(tag: Optional[str] = None, signal: Optional[str] = None,
             min_score: Optional[float] = None, min_zscore: Optional[float] = None,
             limit: int = 50, db=Depends(get_db)):
    params = {k: v for k, v in
              {"tag": tag, "signal": signal, "min_score": min_score,
               "min_zscore": min_zscore, "limit": limit}.items() if v is not None}
    return _call(db, "/api/v1/screener", params)

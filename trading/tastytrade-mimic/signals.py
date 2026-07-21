"""Signal sources: where "a followed trader just made a trade" events come from.

The primary source is tastylive's PUBLIC follow-feed endpoint (captured
2026-07-21, confirmed unauthenticated — no cookies or tokens involved):

  GET https://follow.tastylive.com/api/public_orders?traders[]=...&attrs[open_close]=O

Response shape: {"public_orders": [{id, order_type: "net_credit"|"net_debit",
price, strategy, reason, placed_at, filled_at, trader_id,
order_legs: [{symbol: "SPXW 260721P07435000", action: "selltoopen",
quantity: "1.0", underlying_symbol, ...}], ...}]}

Internal signal dict produced here:
  {"id": "43227967", "trader": "Tom Preston", "symbol": "SPX",
   "description": "...", "order_type": "Limit", "price": 0.2,
   "price_effect": "Credit",
   "legs": [{"instrument_type": "Equity Option",
             "symbol": "SPXW  260721P07435000",   # OCC: root padded to 6
             "action": "Sell to Open", "quantity": 1}, ...]}

Leg quantities are ratio-reduced (smallest leg = 1) so a 10-lot from a
followed trader becomes a 1-lot-per-unit copy; main.py applies MAX_CONTRACTS
as a multiplier cap on top.
"""
import json
import os
from datetime import datetime, timezone

DEFAULT_FOLLOW_FEED_URL = (
    "https://follow.tastylive.com/api/public_orders"
    "?traders[]=Tom Preston&traders[]=Jim Schultz&traders[]=Mike"
    "&traders[]=Jermal&traders[]=Chris&traders[]=Ilya&traders[]=Errol"
    "&traders[]=Gus&traders[]=Katie&traders[]=Tony MX&traders[]=Tom C"
    "&attrs[open_close]=O"
)

ACTION_MAP = {
    "buytoopen": "Buy to Open",
    "selltoopen": "Sell to Open",
    "buytoclose": "Buy to Close",
    "selltoclose": "Sell to Close",
}

ORDER_TYPE_MAP = {
    "net_credit": ("Limit", "Credit"),
    "net_debit": ("Limit", "Debit"),
}


class SignalSource:
    def poll(self) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError


class FileSignalSource(SignalSource):
    """Reads pre-shaped signal dicts from a JSON list file (paper testing /
    external drop-point). Malformed files return no signals rather than crash."""

    def __init__(self, path: str):
        self.path = path

    def poll(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return [s for s in data if isinstance(s, dict) and validate_signal(s) == []]


class FollowFeedSource(SignalSource):
    """Polls the public tastylive follow-feed endpoint (read-only, no auth)."""

    def __init__(self, url: str, headers: dict, max_age_min: int, trader_names: dict):
        self.url = url or DEFAULT_FOLLOW_FEED_URL
        self.headers = headers
        self.max_age_min = max_age_min
        self.trader_names = trader_names

    def poll(self) -> list[dict]:
        import urllib.parse
        import urllib.request

        # the captured URL contains spaces and [] — quote them for urllib
        url = urllib.parse.quote(self.url, safe=":/?&=%")
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
        return parse_follow_feed(raw, max_age_min=self.max_age_min,
                                 trader_names=self.trader_names)


def occ_symbol(feed_symbol: str) -> str | None:
    """'SPXW 260721P07435000' -> 'SPXW  260721P07435000' (OCC root padded to 6)."""
    parts = feed_symbol.split()
    if len(parts) != 2:
        return None
    root, rest = parts
    if len(rest) != 15 or len(root) > 6:  # YYMMDD + C/P + 8-digit strike
        return None
    return f"{root:<6}{rest}"


def _reduce_ratio(quantities: list[float]) -> list[int] | None:
    """[10, 10, 20] -> [1, 1, 2]; smallest leg becomes 1 unit."""
    if not quantities or any(q <= 0 for q in quantities):
        return None
    smallest = min(quantities)
    reduced = [round(q / smallest) for q in quantities]
    if any(r < 1 for r in reduced):
        return None
    return reduced


def parse_follow_feed(raw, max_age_min: int = 180, trader_names: dict | None = None,
                      now: datetime | None = None) -> list[dict]:
    """Map tastylive public_orders onto internal signals.

    Only FILLED orders are copied (a placed-but-unfilled order may be canceled),
    and only fills newer than max_age_min (so a restart doesn't replay history).
    Orders that can't be mapped cleanly are skipped, never guessed at.
    """
    trader_names = trader_names or {}
    now = now or datetime.now(timezone.utc)
    orders = raw.get("public_orders", []) if isinstance(raw, dict) else []
    signals = []
    for o in orders:
        if not isinstance(o, dict) or not o.get("filled_at") or not o.get("id"):
            continue
        try:
            filled = datetime.fromisoformat(str(o["filled_at"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - filled).total_seconds() > max_age_min * 60:
            continue
        mapped = ORDER_TYPE_MAP.get(o.get("order_type"))
        if not mapped:
            continue
        order_type, price_effect = mapped
        raw_legs = o.get("order_legs") or []
        legs, quantities = [], []
        for leg in raw_legs:
            symbol = occ_symbol(str(leg.get("symbol", "")))
            action = ACTION_MAP.get(str(leg.get("action", "")).lower())
            try:
                qty = float(leg.get("quantity", 0))
            except (TypeError, ValueError):
                qty = 0
            if not symbol or not action or qty <= 0:
                legs = []
                break
            legs.append({"instrument_type": "Equity Option", "symbol": symbol,
                         "action": action})
            quantities.append(qty)
        reduced = _reduce_ratio(quantities) if legs else None
        if not legs or reduced is None:
            continue
        for leg, q in zip(legs, reduced):
            leg["quantity"] = q
        underlying = raw_legs[0].get("underlying_symbol", "?")
        trader = trader_names.get(str(o.get("trader_id")), f"Trader {o.get('trader_id')}")
        desc_bits = [o.get("strategy", ""), o.get("reason", "")]
        pop = o.get("probability_of_profit")
        if pop:
            try:
                desc_bits.append(f"POP {float(pop):.0f}%")
            except (TypeError, ValueError):
                pass
        try:
            price = float(o.get("price"))
        except (TypeError, ValueError):
            continue
        signals.append({
            "id": str(o["id"]),
            "trader": trader,
            "symbol": underlying,
            "description": " — ".join(b for b in desc_bits if b),
            "order_type": order_type,
            "price": price,
            "price_effect": price_effect,
            "legs": legs,
        })
    return signals


def validate_signal(sig: dict) -> list[str]:
    problems = []
    for key in ("id", "trader", "symbol", "legs"):
        if not sig.get(key):
            problems.append(f"missing {key}")
    legs = sig.get("legs") or []
    if not isinstance(legs, list) or not legs:
        problems.append("legs must be a non-empty list")
    else:
        for i, leg in enumerate(legs):
            if not isinstance(leg, dict):
                problems.append(f"leg {i} not an object")
                continue
            for key in ("instrument_type", "symbol", "action", "quantity"):
                if not leg.get(key):
                    problems.append(f"leg {i} missing {key}")
    return problems


def make_source(cfg) -> SignalSource:
    if cfg.signal_source == "follow-feed":
        return FollowFeedSource(
            cfg.follow_feed_url,
            json.loads(cfg.follow_feed_headers_json),
            cfg.max_signal_age_min,
            json.loads(cfg.trader_names_json),
        )
    return FileSignalSource(cfg.signal_file)

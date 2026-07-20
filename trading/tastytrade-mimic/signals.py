"""Signal sources: where "a followed trader just made a trade" events come from.

A signal dict:
  {"id": "unique-string", "trader": "Tom", "symbol": "SPY", "description": "...",
   "order_type": "Limit", "price": 1.05, "price_effect": "Credit",
   "legs": [{"instrument_type": "Equity Option", "symbol": "SPY   260821P00550000",
             "action": "Sell to Open", "quantity": 1}, ...]}

Leg symbols use the OCC format the tastytrade API expects.
"""
import json
import os


class SignalSource:
    def poll(self) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError


class FileSignalSource(SignalSource):
    """Reads signals from a JSON file (a list of signal dicts).

    Used for paper-cycle testing, and as the drop-point for any external watcher
    that writes signals it captures. Malformed files return no signals rather
    than crashing the loop.
    """

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
    """Polls the follow-feed endpoint captured from a logged-in browser session.

    The Follow Feed is not part of the public Open API, so the URL + headers must
    be captured once via DevTools (see README). Read-only: this source never
    posts anything to tastytrade.
    """

    def __init__(self, url: str, headers: dict):
        if not url:
            raise ValueError(
                "FOLLOW_FEED_URL not set — capture the endpoint per README, "
                "or use SIGNAL_SOURCE=file for paper testing."
            )
        self.url = url
        self.headers = headers

    def poll(self) -> list[dict]:
        import urllib.request

        req = urllib.request.Request(self.url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
        return parse_follow_feed(raw)


def parse_follow_feed(raw) -> list[dict]:
    """Map the platform's feed payload onto our signal shape.

    The exact payload shape is unknown until the endpoint is captured, so this
    handles the conventional tastytrade envelope ({"data": {"items": [...]}})
    and passes through items that already carry the fields we need. Anything it
    can't map is skipped, never guessed.
    """
    items = raw
    if isinstance(raw, dict):
        items = raw.get("data", raw)
        if isinstance(items, dict):
            items = items.get("items", [])
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and validate_signal(i) == []]


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
        return FollowFeedSource(cfg.follow_feed_url, json.loads(cfg.follow_feed_headers_json))
    return FileSignalSource(cfg.signal_file)

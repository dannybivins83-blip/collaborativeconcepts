"""tastytrade Open API adapter — official OAuth2 API only, no password logins.

Every order goes through the API's /orders/dry-run first. A real order is
submitted ONLY when armed=True, which main.py sets only for MODE=live plus the
--execute flag, after a per-trade human approval.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


class TastytradeBroker:
    def __init__(self, cfg):
        self.cfg = cfg
        self._access_token = None
        self._token_expiry = 0.0

    # -- auth ---------------------------------------------------------------
    def _token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expiry - 60:
            return self._access_token
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.cfg.tt_refresh_token,
            "client_secret": self.cfg.tt_client_secret,
        }
        # tastytrade provisions a client_id alongside the secret (TT_CLIENT_ID is
        # already in the VM's .env); include it when set — standard OAuth2 refresh
        # grant. Absent -> legacy secret-only body, behavior unchanged. If the
        # sandbox ever rejects with invalid_client, unset TT_CLIENT_ID to revert.
        if getattr(self.cfg, "tt_client_id", ""):
            params["client_id"] = self.cfg.tt_client_id
        body = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(
            f"{self.cfg.api_base}/oauth/token", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        # Wrap every failure as BrokerError so the caller notifies instead of
        # dying silently. Auth failure is the most common first-run problem —
        # e.g. a production refresh token 401s against the cert/sandbox base.
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:500]
            low = detail.lower()
            if e.code == 400 or "invalid_grant" in low or "revok" in low:
                hint = (" -> refresh token REVOKED or invalid; regenerate it at "
                        "developer.tastytrade.com and set the new TT_REFRESH_TOKEN on the VM "
                        "(an account lock/unlock or password reset revokes OAuth grants)")
            elif e.code in (401, 403):
                hint = (f" -> auth rejected at {self.cfg.api_base}; note a production "
                        f"refresh token will fail against the cert/sandbox base")
            else:
                hint = ""
            raise BrokerError(f"OAuth token refresh -> HTTP {e.code}: {detail}{hint}", code=e.code) from e
        except (urllib.error.URLError, OSError) as e:
            raise BrokerError(f"OAuth token refresh -> network error reaching "
                              f"{self.cfg.api_base}: {e}") from e
        if not isinstance(data, dict) or "access_token" not in data:
            raise BrokerError(f"OAuth token refresh returned no access_token: {str(data)[:200]}")
        self._access_token = data["access_token"]
        self._token_expiry = time.monotonic() + int(data.get("expires_in", 900))
        return self._access_token

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        body = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{self.cfg.api_base}{path}", data=body, method=method,
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:500]
            raise BrokerError(f"{method} {path} -> HTTP {e.code}: {detail}", code=e.code) from e

    # -- accounts -----------------------------------------------------------
    def account_number(self) -> str:
        if self.cfg.tt_account:
            return self.cfg.tt_account
        data = self._request("GET", "/customers/me/accounts")
        items = data.get("data", {}).get("items", [])
        if not items:
            raise BrokerError("no accounts returned for this login")
        return items[0]["account"]["account-number"]

    # -- orders -------------------------------------------------------------
    @staticmethod
    def build_order(sig: dict, multiplier: int) -> dict:
        """Leg quantities are the signal's ratio-reduced values times multiplier."""
        order = {
            "order-type": sig.get("order_type", "Limit"),
            "time-in-force": "Day",
            "legs": [{
                "instrument-type": leg["instrument_type"],
                "symbol": leg["symbol"],
                "action": leg["action"],
                "quantity": int(leg["quantity"]) * multiplier,
            } for leg in sig["legs"]],
        }
        if sig.get("price") is not None:
            order["price"] = str(sig["price"])
            order["price-effect"] = sig.get("price_effect", "Credit")
        return order

    def live_positions(self) -> list:
        """Fetch OPEN positions with current marks. Read-only. Returns a list of
        {symbol, qty, dir, mark, multiplier, instrument_type}. mark is None if the
        broker isn't marking it (e.g. the cert sandbox returns 0)."""
        acct = self.account_number()
        items = self._request("GET", f"/accounts/{acct}/positions").get("data", {}).get("items", [])
        out = []
        for p in items:
            mark = p.get("mark-price")
            if mark in (None, "", "0", "0.0", "0.00"):
                mark = p.get("close-price")
            out.append({
                "symbol": p.get("symbol"),
                "qty": abs(float(p.get("quantity") or 0)),
                "dir": p.get("quantity-direction"),
                "mark": (float(mark) if mark not in (None, "") else None),
                "multiplier": float(p.get("multiplier") or 100),
                "instrument_type": p.get("instrument-type", "Equity Option"),
            })
        return out

    def close_from_legs(self, legs_live: list, net_price: float, net_effect: str) -> dict:
        """Place a CLOSING order built from live legs: Long -> Sell to Close, Short ->
        Buy to Close. Validates via dry-run first, then submits. armed only."""
        order_legs = [{
            "instrument-type": l.get("instrument_type", "Equity Option"),
            "symbol": l["symbol"],
            "action": "Buy to Close" if str(l.get("dir", "")).lower().startswith("short") else "Sell to Close",
            "quantity": int(abs(float(l.get("qty") or 1))),
        } for l in legs_live]
        order = {"order-type": "Limit", "time-in-force": "Day", "legs": order_legs,
                 "price": str(abs(round(float(net_price), 2))),
                 "price-effect": net_effect}
        acct = self.account_number()
        self._request("POST", f"/accounts/{acct}/orders/dry-run", order)  # validate first
        placed = self._request("POST", f"/accounts/{acct}/orders", order)
        return {"status": "submitted",
                "order_id": placed.get("data", {}).get("order", {}).get("id")}

    def order_status(self, order_id) -> str:
        """Current status of an order (Filled/Expired/Cancelled/Rejected/Live/Received/...),
        or None if unknown. Read-only."""
        if not order_id:
            return None
        try:
            acct = self.account_number()
            data = self._request("GET", f"/accounts/{acct}/orders/{order_id}")
            return (data.get("data", {}) or {}).get("status")
        except Exception:
            return None


    def margin_preview(self, sig: dict, multiplier: int) -> dict:
        """Read-only: dry-run the order to get tastytrade's REAL buying-power requirement.
        Places NOTHING. Parses the margin from a success response OR a 422 preflight body
        (a rejected order still returns the buying-power-effect). Returns:
        {ok, required, current, affordable} or {ok: False}."""
        import re as _re, json as _json
        def _extract(text: str):
            def grab(key):
                m = _re.search(r'"%s":"?(-?[0-9.]+)' % key, text)
                return float(m.group(1)) if m else None
            req = grab("isolated-order-margin-requirement")
            if req is None:
                req = grab("change-in-margin-requirement")
            return req, grab("current-buying-power")
        try:
            order = self.build_order(sig, multiplier)
            acct = self.account_number()
            dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
            required, current = _extract(_json.dumps(dry))
        except BrokerError as e:
            required, current = _extract(str(e))   # 422 body carries the margin effect
        except Exception:
            return {"ok": False}
        if required is None:
            return {"ok": False}
        affordable = current is not None and current >= required
        return {"ok": True, "required": required, "current": current, "affordable": affordable}


    def place(self, sig: dict, multiplier: int, armed: bool) -> dict:
        order = self.build_order(sig, multiplier)
        if not armed:
            # Disarmed/paper: the approval card IS the product and nothing is placed.
            # An auth/connectivity OUTAGE (dead grant, 5xx, network) must NOT hard-fail
            # the notification loop -> degrade to notification-only. But a 4xx from the
            # dry-run engine is the broker REJECTING this specific order — real
            # validation feedback, not an outage — so surface the reason instead.
            def _outage(e):
                return {"status": "notification-only", "order": order,
                        "warnings": [f"broker offline ({e}); no validation performed — "
                                     "notification-only until the cert grant is restored"]}
            try:
                acct = self.account_number()          # auth happens here
            except BrokerError as e:
                return _outage(e)                     # can't even authenticate -> outage
            try:
                dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
            except BrokerError as e:
                if e.code is not None and 400 <= e.code < 500 and e.code not in (401, 403):
                    return {"status": "rejected", "order": order,
                            "warnings": [f"order rejected: {e}"]}
                return _outage(e)                     # 5xx / auth / network -> outage
            data = dry.get("data", {})
            return {"status": "dry-run-only", "warnings": data.get("warnings", []),
                    "order": order, **_cost_fields(data)}
        # Armed/live: any broker failure MUST propagate (never a fake OK, never a silent
        # skip). BrokerError raised here bubbles to the caller and places nothing.
        acct = self.account_number()
        dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
        warnings = dry.get("data", {}).get("warnings", [])
        placed = self._request("POST", f"/accounts/{acct}/orders", order)
        return {"status": "submitted", "warnings": warnings, **_cost_fields(dry.get("data", {})),
                "order_id": placed.get("data", {}).get("order", {}).get("id")}


def _cost_fields(data: dict) -> dict:
    """Pull the human-facing cost numbers out of a tastytrade dry-run response."""
    bp = data.get("buying-power-effect", {}) or {}
    fees = data.get("fee-calculation", {}) or {}
    return {
        "bp_change": bp.get("change-in-buying-power"),
        "bp_effect": bp.get("change-in-buying-power-effect"),
        "fees": fees.get("total-fees"),
    }


class BrokerError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code  # HTTP status when known (None for network/other), used to
        #                   tell an order REJECTION (4xx) from an outage (5xx/auth/net)

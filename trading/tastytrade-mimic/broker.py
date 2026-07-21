"""tastytrade Open API adapter — official OAuth2 API only, no password logins.

Every order goes through the API's /orders/dry-run first. A real order is
submitted ONLY when armed=True, which main.py sets only for MODE=live plus the
--execute flag, after a per-trade human approval.
"""
import json
import time
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
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.cfg.tt_refresh_token,
            "client_secret": self.cfg.tt_client_secret,
        }).encode()
        req = urllib.request.Request(
            f"{self.cfg.api_base}/oauth/token", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
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
            raise BrokerError(f"{method} {path} -> HTTP {e.code}: {detail}") from e

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

    def place(self, sig: dict, multiplier: int, armed: bool) -> dict:
        acct = self.account_number()
        order = self.build_order(sig, multiplier)
        dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
        warnings = dry.get("data", {}).get("warnings", [])
        if not armed:
            return {"status": "dry-run-only", "warnings": warnings, "order": order}
        placed = self._request("POST", f"/accounts/{acct}/orders", order)
        return {"status": "submitted", "warnings": warnings,
                "order_id": placed.get("data", {}).get("order", {}).get("id")}


class BrokerError(Exception):
    pass

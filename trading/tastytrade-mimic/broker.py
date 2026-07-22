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
            raise BrokerError(f"OAuth token refresh -> HTTP {e.code}: {detail}{hint}") from e
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
        order = self.build_order(sig, multiplier)
        if not armed:
            # Disarmed/paper: the approval card IS the product and nothing is placed.
            # Validate against the broker when reachable, but a broker/auth outage
            # (e.g. a revoked cert grant) must NOT hard-fail the notification loop —
            # degrade to notification-only instead of a loud error on every tap.
            try:
                acct = self.account_number()
                dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
                warnings = dry.get("data", {}).get("warnings", [])
                return {"status": "dry-run-only", "warnings": warnings, "order": order}
            except BrokerError as e:
                return {"status": "notification-only",
                        "warnings": [f"broker offline ({e}); no validation performed — "
                                     "notification-only until the cert grant is restored"],
                        "order": order}
        # Armed/live: any broker failure MUST propagate (never a fake OK, never a silent
        # skip). BrokerError raised here bubbles to the caller and places nothing.
        acct = self.account_number()
        dry = self._request("POST", f"/accounts/{acct}/orders/dry-run", order)
        warnings = dry.get("data", {}).get("warnings", [])
        placed = self._request("POST", f"/accounts/{acct}/orders", order)
        return {"status": "submitted", "warnings": warnings,
                "order_id": placed.get("data", {}).get("order", {}).get("id")}


class BrokerError(Exception):
    pass

"""Environment-driven config. Secrets stay in env vars — never logged, never committed.

CREDENTIAL WALL: there are TWO fully separate credential slots.
  - CERT / sandbox (fake money): TT_CLIENT_SECRET / TT_REFRESH_TOKEN / TT_CLIENT_ID / TT_ACCOUNT
  - PRODUCTION (REAL money):      TT_PROD_CLIENT_SECRET / TT_PROD_REFRESH_TOKEN / TT_PROD_CLIENT_ID / TT_PROD_ACCOUNT
The tt_* properties resolve to the PROD slot ONLY when mode == "live"; otherwise the CERT
slot. api_base does the same. A sandbox credential can therefore never reach production,
and the prod credential is dormant unless mode is deliberately set to "live".
"""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    mode: str = field(default_factory=lambda: os.environ.get("MODE", "paper").lower())
    # PAPER_EXECUTE=1 -> actually SUBMIT approved orders to the cert SANDBOX (fake money).
    # This can never touch production: api_base is cert whenever mode != "live".
    paper_execute: bool = field(default_factory=lambda: os.environ.get("PAPER_EXECUTE", "0") == "1")

    # --- CERT/sandbox credential slot (fake money) — used when mode != "live" ---
    _cert_secret: str = field(default_factory=lambda: os.environ.get("TT_CLIENT_SECRET", ""))
    _cert_refresh: str = field(default_factory=lambda: os.environ.get("TT_REFRESH_TOKEN", ""))
    _cert_client_id: str = field(default_factory=lambda: os.environ.get("TT_CLIENT_ID", ""))
    _cert_account: str = field(default_factory=lambda: os.environ.get("TT_ACCOUNT", ""))
    # --- PRODUCTION credential slot (REAL money) — used ONLY when mode == "live" ---
    _prod_secret: str = field(default_factory=lambda: os.environ.get("TT_PROD_CLIENT_SECRET", ""))
    _prod_refresh: str = field(default_factory=lambda: os.environ.get("TT_PROD_REFRESH_TOKEN", ""))
    _prod_client_id: str = field(default_factory=lambda: os.environ.get("TT_PROD_CLIENT_ID", ""))
    _prod_account: str = field(default_factory=lambda: os.environ.get("TT_PROD_ACCOUNT", ""))

    telegram_bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", ""))
    kill_switch_file: str = field(default_factory=lambda: os.environ.get("KILL_SWITCH_FILE", "KILL_SWITCH"))
    _max_contracts: int = field(default_factory=lambda: int(os.environ.get("MAX_CONTRACTS", "1")))
    # HARD ceiling on LIVE (real-money) size, independent of MAX_CONTRACTS. First real
    # trades stay tiny; raising this is a deliberate act.
    live_max_contracts: int = field(default_factory=lambda: int(os.environ.get("LIVE_MAX_CONTRACTS", "1")))
    approval_timeout_s: int = field(default_factory=lambda: int(os.environ.get("APPROVAL_TIMEOUT_S", "900")))
    alert_cooldown_s: int = field(default_factory=lambda: int(os.environ.get("ALERT_COOLDOWN_S", "21600")))
    signal_source: str = field(default_factory=lambda: os.environ.get("SIGNAL_SOURCE", "follow-feed"))
    signal_file: str = field(default_factory=lambda: os.environ.get("SIGNAL_FILE", "signals.json"))
    follow_feed_url: str = field(default_factory=lambda: os.environ.get("FOLLOW_FEED_URL", ""))
    follow_feed_headers_json: str = field(default_factory=lambda: os.environ.get("FOLLOW_FEED_HEADERS_JSON", "{}"))
    max_signal_age_min: int = field(default_factory=lambda: int(os.environ.get("MAX_SIGNAL_AGE_MIN", "180")))
    trader_names_json: str = field(default_factory=lambda: os.environ.get("TRADER_NAMES_JSON", "{}"))
    poll_interval_s: int = field(default_factory=lambda: int(os.environ.get("POLL_INTERVAL_S", "30")))
    state_file: str = field(default_factory=lambda: os.environ.get("STATE_FILE", "state.json"))
    # Paper trade ledger + P&L scorecard (pure record-keeping, no orders placed).
    ledger_file: str = field(default_factory=lambda: os.environ.get("LEDGER_FILE", "trades.jsonl"))
    positions_file: str = field(default_factory=lambda: os.environ.get("POSITIONS_FILE", "positions.json"))
    follow_feed_close_url: str = field(default_factory=lambda: os.environ.get("FOLLOW_FEED_CLOSE_URL", ""))
    track_pnl: bool = field(default_factory=lambda: os.environ.get("TRACK_PNL", "1") != "0")
    # API hosts are env-overridable so the path stays turnkey if tastytrade ever
    # consolidates domains. Defaults are the current canonical hosts (both verified
    # reachable). NOTE — the prod/sandbox subdomain mismatch is INTENTIONAL, not a
    # typo: tastytrade rebranded only production to tastytrade.com; the cert/sandbox
    # environment stayed on the legacy tastyworks.com domain. Do not "fix" it.
    api_base_live: str = field(default_factory=lambda: os.environ.get("TT_API_BASE_LIVE", "https://api.tastytrade.com"))
    api_base_paper: str = field(default_factory=lambda: os.environ.get("TT_API_BASE_PAPER", "https://api.cert.tastyworks.com"))

    # --- the wall: mode selects which credential/host/account is used ---
    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def tt_client_secret(self) -> str:
        return self._prod_secret if self.is_live else self._cert_secret

    @property
    def tt_refresh_token(self) -> str:
        return self._prod_refresh if self.is_live else self._cert_refresh

    @property
    def tt_client_id(self) -> str:
        return self._prod_client_id if self.is_live else self._cert_client_id

    @property
    def tt_account(self) -> str:
        return self._prod_account if self.is_live else self._cert_account

    @property
    def max_contracts(self) -> int:
        # LIVE (real money) is hard-capped at live_max_contracts regardless of MAX_CONTRACTS.
        if self.is_live:
            return max(1, min(self._max_contracts, self.live_max_contracts))
        return self._max_contracts

    @property
    def api_base(self) -> str:
        # Paper mode ALWAYS points at the sandbox; only live touches production.
        return self.api_base_live if self.is_live else self.api_base_paper

    def kill_switch_engaged(self) -> bool:
        return os.path.exists(self.kill_switch_file)

    def validate(self) -> list:
        """Return a list of missing/unsafe-config problems (names only — never values)."""
        problems = []
        if self.mode not in ("paper", "live"):
            problems.append(f"MODE must be 'paper' or 'live', got '{self.mode}'")
        # Check credentials for the ACTIVE mode's slot only.
        if self.is_live:
            need = {"TT_PROD_CLIENT_SECRET": self._prod_secret,
                    "TT_PROD_REFRESH_TOKEN": self._prod_refresh}
        else:
            need = {"TT_CLIENT_SECRET": self._cert_secret,
                    "TT_REFRESH_TOKEN": self._cert_refresh}
        need["TELEGRAM_BOT_TOKEN"] = self.telegram_bot_token
        need["TELEGRAM_CHAT_ID"] = self.telegram_chat_id
        for name, val in need.items():
            if not val:
                problems.append(f"{name} is not set")
        if self.max_contracts < 1:
            problems.append("MAX_CONTRACTS must be >= 1")
        # SAFETY: live must NEVER run on the sandbox credential. If the prod slot is empty
        # or accidentally equals the cert secret, refuse to go live.
        if self.is_live:
            if not self._prod_secret or not self._prod_refresh:
                problems.append("LIVE requires the PROD credential slot (TT_PROD_*) — refusing to run on sandbox creds")
            elif self._cert_secret and self._prod_secret == self._cert_secret:
                problems.append("LIVE refuses: prod credential is identical to the sandbox credential")
        return problems

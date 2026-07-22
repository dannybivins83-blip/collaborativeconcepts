"""Environment-driven config. Secrets stay in env vars — never logged, never committed."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    mode: str = field(default_factory=lambda: os.environ.get("MODE", "paper").lower())
    # PAPER_EXECUTE=1 -> actually SUBMIT approved orders to the cert SANDBOX (fake money).
    # This can never touch production: api_base is cert whenever mode != "live".
    paper_execute: bool = field(default_factory=lambda: os.environ.get("PAPER_EXECUTE", "0") == "1")
    tt_client_secret: str = field(default_factory=lambda: os.environ.get("TT_CLIENT_SECRET", ""))
    tt_refresh_token: str = field(default_factory=lambda: os.environ.get("TT_REFRESH_TOKEN", ""))
    tt_client_id: str = field(default_factory=lambda: os.environ.get("TT_CLIENT_ID", ""))
    tt_account: str = field(default_factory=lambda: os.environ.get("TT_ACCOUNT", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", ""))
    kill_switch_file: str = field(default_factory=lambda: os.environ.get("KILL_SWITCH_FILE", "KILL_SWITCH"))
    max_contracts: int = field(default_factory=lambda: int(os.environ.get("MAX_CONTRACTS", "1")))
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

    @property
    def api_base(self) -> str:
        # Paper mode ALWAYS points at the sandbox; only live touches production.
        return self.api_base_live if self.mode == "live" else self.api_base_paper

    def kill_switch_engaged(self) -> bool:
        return os.path.exists(self.kill_switch_file)

    def validate(self) -> list[str]:
        """Return a list of missing-config problems (names only — never values)."""
        problems = []
        if self.mode not in ("paper", "live"):
            problems.append(f"MODE must be 'paper' or 'live', got '{self.mode}'")
        for name in ("TT_CLIENT_SECRET", "TT_REFRESH_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
            if not getattr(self, name.lower()):
                problems.append(f"{name} is not set")
        if self.max_contracts < 1:
            problems.append("MAX_CONTRACTS must be >= 1")
        return problems

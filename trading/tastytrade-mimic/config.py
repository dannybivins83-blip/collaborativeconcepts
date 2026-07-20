"""Environment-driven config. Secrets stay in env vars — never logged, never committed."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    mode: str = field(default_factory=lambda: os.environ.get("MODE", "paper").lower())
    tt_client_secret: str = field(default_factory=lambda: os.environ.get("TT_CLIENT_SECRET", ""))
    tt_refresh_token: str = field(default_factory=lambda: os.environ.get("TT_REFRESH_TOKEN", ""))
    tt_account: str = field(default_factory=lambda: os.environ.get("TT_ACCOUNT", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", ""))
    kill_switch_file: str = field(default_factory=lambda: os.environ.get("KILL_SWITCH_FILE", "KILL_SWITCH"))
    max_contracts: int = field(default_factory=lambda: int(os.environ.get("MAX_CONTRACTS", "1")))
    approval_timeout_s: int = field(default_factory=lambda: int(os.environ.get("APPROVAL_TIMEOUT_S", "900")))
    signal_source: str = field(default_factory=lambda: os.environ.get("SIGNAL_SOURCE", "file"))
    signal_file: str = field(default_factory=lambda: os.environ.get("SIGNAL_FILE", "signals.json"))
    follow_feed_url: str = field(default_factory=lambda: os.environ.get("FOLLOW_FEED_URL", ""))
    follow_feed_headers_json: str = field(default_factory=lambda: os.environ.get("FOLLOW_FEED_HEADERS_JSON", "{}"))
    poll_interval_s: int = field(default_factory=lambda: int(os.environ.get("POLL_INTERVAL_S", "30")))
    state_file: str = field(default_factory=lambda: os.environ.get("STATE_FILE", "state.json"))

    @property
    def api_base(self) -> str:
        # Paper mode ALWAYS points at the sandbox; only live touches production.
        if self.mode == "live":
            return "https://api.tastytrade.com"
        return "https://api.cert.tastyworks.com"

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

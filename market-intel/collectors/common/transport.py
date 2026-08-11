"""HTTP transport: rate limiting, retry/backoff, and an offline fixture mode.

The fixture transport is not a mock of the collector — the collector code path
is identical either way. Only the bytes-over-the-wire step is swapped, so an
offline test exercises the real parsing, validation and persistence logic.
That is what lets this pipeline be *proven* in a sandbox with no network.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from packages.shared.errors import CollectorError


class RateLimiter:
    """Simple minimum-interval limiter. SEC asks for <= 10 requests/second and
    will block a client that ignores it, so this is a correctness feature."""

    def __init__(self, per_second=5.0):
        self.min_interval = 1.0 / per_second if per_second else 0.0
        self._last = 0.0

    def wait(self):
        if not self.min_interval:
            return
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()


class Transport:
    def get(self, url, headers=None) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def get_json(self, url, headers=None):
        raw = self.get(url, headers=headers)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise CollectorError(f"invalid JSON from {url}: {e}", retryable=False) from e


class HttpTransport(Transport):
    """Live HTTP with backoff. 429/5xx retry; 4xx fails fast (retrying a 403
    just gets you banned harder)."""

    def __init__(self, user_agent, per_second=5.0, retries=4, timeout=30, opener=None):
        if not user_agent or "@" not in user_agent:
            # SEC requires a declared contact; other sources tolerate it.
            raise ValueError("user_agent must include a contact email, e.g. "
                             "'MarketIntel/1.0 (you@example.com)'")
        self.user_agent = user_agent
        self.limiter = RateLimiter(per_second)
        self.retries = retries
        self.timeout = timeout
        self._opener = opener or urllib.request.urlopen

    def get(self, url, headers=None) -> bytes:
        hdrs = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        hdrs.update(headers or {})
        last = None
        for attempt in range(self.retries):
            self.limiter.wait()
            req = urllib.request.Request(url, headers=hdrs)
            try:
                with self._opener(req, timeout=self.timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                if e.code in (429, 500, 502, 503, 504) and attempt < self.retries - 1:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                raise CollectorError(f"{url}: {last}", retryable=e.code in (429, 503)) from e
            except (urllib.error.URLError, OSError) as e:
                last = str(e)
                if attempt < self.retries - 1:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                raise CollectorError(f"{url}: {last}", retryable=True) from e
        raise CollectorError(f"{url}: {last}", retryable=True)


class FixtureTransport(Transport):
    """Serves recorded payloads from tests/fixtures by URL mapping.

    Used when MI_OFFLINE=1 (or no network). Every fixture is clearly labeled
    DEMO/SYNTHETIC inside the file itself so demo data can never be mistaken
    for live data downstream.
    """

    def __init__(self, root, mapping=None):
        self.root = Path(root)
        self.mapping = mapping or {}
        self.calls = []

    def _path_for(self, url):
        if url in self.mapping:
            return self.root / self.mapping[url]
        for pattern, name in self.mapping.items():
            if pattern.endswith("*") and url.startswith(pattern[:-1]):
                return self.root / name
        return None

    def get(self, url, headers=None) -> bytes:
        self.calls.append(url)
        path = self._path_for(url)
        if path is None or not path.exists():
            raise CollectorError(f"no fixture for {url} (looked in {self.root})",
                                 retryable=False)
        return path.read_bytes()


def default_transport(fixtures_root=None, mapping=None, user_agent=None, per_second=5.0):
    """Live transport when a contact UA is configured and MI_OFFLINE is unset."""
    import os
    if os.environ.get("MI_OFFLINE", "").lower() in ("1", "true", "yes"):
        return FixtureTransport(fixtures_root, mapping)
    ua = user_agent or os.environ.get("MI_USER_AGENT", "")
    if not ua:
        raise ValueError(
            "MI_USER_AGENT is not set. SEC requires a declared contact, e.g. "
            "'MarketIntel/1.0 (you@example.com)'. Set MI_OFFLINE=1 to run on fixtures.")
    return HttpTransport(ua, per_second=per_second)

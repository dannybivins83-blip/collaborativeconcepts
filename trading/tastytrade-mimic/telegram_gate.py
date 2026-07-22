"""The human gate: one-tap per-trade approval over Telegram.

HARD RAIL (overlord directive 2026-07-20): this gate must NEVER auto-approve.
No batch approvals, no per-trader trust bypass, and an unanswered request
EXPIRES TO SKIP. There is deliberately no code path that returns approval
without a human tapping the Approve button for this specific trade.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"

_MAX_ATTEMPTS = 3


def _sleep(seconds: float) -> None:  # indirection so tests can patch the wait
    time.sleep(seconds)


def _call(token: str, method: str, params: dict, attempts: int = _MAX_ATTEMPTS) -> dict:
    """POST to the Telegram Bot API, retrying on 429/5xx with backoff.

    Telegram rate-limits with HTTP 429 (+ Retry-After). Without backoff a burst
    would raise and could crash the loop — the same failure class that killed
    the shared-ntfy-topic processes on the VM. Retry-After is honored; 4xx
    other than 429 fail fast.
    """
    data = urllib.parse.urlencode(params).encode()
    last_exc = None
    for attempt in range(max(1, attempts)):
        req = urllib.request.Request(API.format(token=token, method=method), data=data)
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_exc = e
            retryable = e.code == 429 or 500 <= e.code < 600
            if not retryable or attempt == attempts - 1:
                raise
            retry_after = e.headers.get("Retry-After") if e.headers else None
            delay = int(retry_after) if (retry_after and str(retry_after).isdigit()) else 2 ** attempt
            _sleep(min(delay, 30))
    raise last_exc  # pragma: no cover - loop always returns or raises above


def _occ_strike(symbol: str) -> float:
    """Strike price from an OCC option symbol (last 8 digits = strike x 1000)."""
    s = symbol.replace(" ", "")
    return int(s[-8:]) / 1000.0


def _spread_economics(sig: dict, multiplier: int):
    """For a 2-leg vertical spread, return (total_investment, max_profit, roi_pct).
    total_investment = capital at risk (max loss). None if not a priceable 2-leg vertical."""
    legs = sig.get("legs", [])
    price = sig.get("price")
    if price is None or len(legs) != 2:
        return None
    try:
        p = float(price)
        width = abs(_occ_strike(legs[0]["symbol"]) - _occ_strike(legs[1]["symbol"]))
        if width <= 0:
            return None
        c = max(1, int(multiplier))
        if (sig.get("price_effect") or "").lower() == "credit":
            invest = (width - p) * 100 * c   # max loss on a credit spread
            profit = p * 100 * c             # max profit = credit kept
        else:                                 # debit spread
            invest = p * 100 * c             # premium paid
            profit = (width - p) * 100 * c   # max profit = width - debit
        if invest <= 0:
            return None
        return invest, profit, (profit / invest * 100)
    except (TypeError, ValueError, KeyError, IndexError):
        return None


def format_trade_card(sig: dict, multiplier: int, mode: str) -> str:
    lines = [
        f"📣 {sig['trader']} traded {sig['symbol']}",
        sig.get("description", ""),
        "",
    ]
    for leg in sig["legs"]:
        qty = int(leg.get("quantity", 1)) * multiplier
        lines.append(f"  • {leg['action']} {qty}x {leg['symbol']}")
    price = sig.get("price")
    if price is not None:
        lines.append(f"  @ {price} {sig.get('price_effect', '')}".rstrip())
        try:
            total = float(price) * multiplier * 100  # options: 100 shares/contract
            eff = (sig.get("price_effect") or "").lower()
            if eff == "credit":
                lines.append(f"  💰 Est. credit received: +${total:,.0f}")
            elif eff == "debit":
                lines.append(f"  💰 Est. cost: -${total:,.0f}")
            else:
                lines.append(f"  💰 Est. amount: ${total:,.0f}")
        except (TypeError, ValueError):
            pass
        econ = _spread_economics(sig, multiplier)
        if econ:
            invest, profit, roi = econ
            lines.append(f"  📊 Total investment: ${invest:,.0f}")
            lines.append(f"  📈 Best case: +${profit:,.0f} ({roi:.0f}% ROI)")
    lines.append("")
    lines.append("🧪 PAPER account" if mode != "live" else "💵 LIVE account")
    return "\n".join(line for line in lines if line is not None)


def request_approval(cfg, sig: dict, multiplier: int) -> bool:
    """Send the trade card with Approve/Skip buttons; block until a tap or expiry.

    Returns True ONLY on an explicit Approve tap for this trade. Expiry, Skip,
    errors, and anything unexpected all return False.
    """
    approve_data = f"approve:{sig['id']}"
    skip_data = f"skip:{sig['id']}"
    keyboard = {"inline_keyboard": [[
        {"text": "✅ Copy this trade", "callback_data": approve_data},
        {"text": "❌ Skip", "callback_data": skip_data},
    ]]}
    try:
        sent = _call(cfg.telegram_bot_token, "sendMessage", {
            "chat_id": cfg.telegram_chat_id,
            "text": format_trade_card(sig, multiplier, cfg.mode),
            "reply_markup": json.dumps(keyboard),
        })
    except OSError:
        return False  # can't reach the human gate -> no approval -> SKIP (never yes)
    if not sent.get("ok"):
        return False
    message_id = sent["result"]["message_id"]

    deadline = time.monotonic() + cfg.approval_timeout_s
    offset = None
    decision = False
    answered = False
    while time.monotonic() < deadline and not answered:
        params = {"timeout": 25, "allowed_updates": '["callback_query"]'}
        if offset is not None:
            params["offset"] = offset
        try:
            updates = _call(cfg.telegram_bot_token, "getUpdates", params)
        except OSError:
            time.sleep(5)
            continue
        for upd in updates.get("result", []):
            offset = upd["update_id"] + 1
            cq = upd.get("callback_query")
            if not cq:
                continue
            data = cq.get("data", "")
            if str(cq.get("message", {}).get("chat", {}).get("id")) != str(cfg.telegram_chat_id):
                continue  # only the owner's chat can answer
            if data == approve_data:
                decision, answered = True, True
            elif data == skip_data:
                decision, answered = False, True
            else:
                continue
            _call(cfg.telegram_bot_token, "answerCallbackQuery", {"callback_query_id": cq["id"]})

    outcome = "✅ Approved" if decision else ("❌ Skipped" if answered else "⏰ Expired → skipped")
    try:  # cosmetic status edit — never let it override or crash the decision
        _call(cfg.telegram_bot_token, "editMessageText", {
            "chat_id": cfg.telegram_chat_id,
            "message_id": message_id,
            "text": format_trade_card(sig, multiplier, cfg.mode) + f"\n\n{outcome}",
        })
    except OSError:
        pass
    return decision


_recent_alerts = {}  # dedupe key -> monotonic time last sent


def notify(cfg, text: str, key: str = None, cooldown_s: int = 0) -> None:
    """Send a Telegram message (best-effort). With a `key` + `cooldown_s`, a
    repeat of the same key is suppressed within the window — so a persistent
    failure (e.g. a revoked credential on every poll) pings ONCE, not forever."""
    if key is not None and cooldown_s > 0:
        now = time.monotonic()
        last = _recent_alerts.get(key)
        if last is not None and (now - last) < cooldown_s:
            return
        _recent_alerts[key] = now
    try:
        _call(cfg.telegram_bot_token, "sendMessage", {"chat_id": cfg.telegram_chat_id, "text": text})
    except OSError:
        pass

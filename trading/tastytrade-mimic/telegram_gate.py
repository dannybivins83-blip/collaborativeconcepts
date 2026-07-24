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


def _occ_expiration(symbol: str):
    """(expiration_date_str 'YYYY-MM-DD', dte_int) from an OCC symbol, or (None, None).
    OCC: root + yymmdd + C/P + strike8. dte is days from today (server clock)."""
    import datetime
    s = symbol.replace(" ", "")
    try:
        # strike is last 8; C/P is char before that; yymmdd is the 6 before that
        core = s[:-9]                      # strip C/P + 8-digit strike
        ymd = core[-6:]
        exp = datetime.date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
        dte = (exp - datetime.date.today()).days
        return "%s %d, %d" % (exp.strftime("%b"), exp.day, exp.year), dte
    except (ValueError, IndexError):
        return None, None


def _occ_strike(symbol: str) -> float:
    """Strike price from an OCC option symbol (last 8 digits = strike x 1000)."""
    s = symbol.replace(" ", "")
    return int(s[-8:]) / 1000.0


def _occ_type(symbol: str) -> str:
    """'C' or 'P' from an OCC option symbol (char before the 8-digit strike)."""
    s = symbol.replace(" ", "")
    return s[-9:-8].upper()


def _spread_economics(sig: dict, multiplier: int):
    """Return (total_investment, max_profit, roi_pct) for a defined-risk options trade —
    a 2-leg vertical OR a 4-leg iron condor/fly. total_investment = capital at risk (max
    loss). Groups legs into call/put pairs and uses the widest wing. None if it can't
    price the structure (e.g. a naked single leg or a stock leg)."""
    legs = sig.get("legs", [])
    price = sig.get("price")
    if price is None or len(legs) < 2:
        return None
    try:
        p = float(price)
        c = max(1, int(multiplier))
        # strikes of the option legs, grouped by call/put
        calls, puts = [], []
        for leg in legs:
            sym = leg["symbol"]
            (calls if _occ_type(sym) == "C" else puts).append(_occ_strike(sym))
        widths = []
        if len(calls) >= 2:
            widths.append(abs(max(calls) - min(calls)))
        if len(puts) >= 2:
            widths.append(abs(max(puts) - min(puts)))
        if not widths:
            return None
        width = max(widths)          # widest wing = the defined risk on that side
        if width <= 0:
            return None
        if (sig.get("price_effect") or "").lower() == "credit":
            invest = (width - p) * 100 * c   # max loss on the wide wing minus credit kept
            profit = p * 100 * c             # max profit = credit
        else:                                 # debit
            invest = p * 100 * c             # premium paid = max loss
            profit = (width - p) * 100 * c   # max profit = wing width - debit
        if invest <= 0:
            return None
        return invest, profit, (profit / invest * 100)
    except (TypeError, ValueError, KeyError, IndexError):
        return None

def format_trade_card(sig: dict, multiplier: int, mode: str, margin: dict = None) -> str:
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
        exp_str, dte = _occ_expiration(sig["legs"][0]["symbol"]) if sig.get("legs") else (None, None)
        if dte is not None:
            lines.append(f"  📅 Duration: {dte} days (exp {exp_str})")
    if margin and margin.get("ok") and margin.get("required") is not None:
        req = margin["required"]; cur = margin.get("current")
        if margin.get("affordable"):
            lines.append(f"  🏦 Buying power required: ${req:,.0f}" + (f" (you have ${cur:,.0f})" if cur is not None else ""))
        else:
            lines.append(f"  ⚠️ NEEDS ${req:,.0f} buying power" + (f" — you have ${cur:,.0f} (would be rejected)" if cur is not None else ""))
    lines.append("")
    lines.append("🧪 PAPER account" if mode != "live" else "💵 LIVE account")
    return "\n".join(line for line in lines if line is not None)


def _keyboard(sig: dict) -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Copy this trade", "callback_data": f"approve:{sig['id']}"},
        {"text": "❌ Skip", "callback_data": f"skip:{sig['id']}"},
    ]]}


def send_card(cfg, sig: dict, multiplier: int, margin: dict = None):
    """Send a trade card with Approve/Skip buttons. NON-BLOCKING.
    Returns the Telegram message_id, or None if it could not be sent."""
    try:
        sent = _call(cfg.telegram_bot_token, "sendMessage", {
            "chat_id": cfg.telegram_chat_id,
            "text": format_trade_card(sig, multiplier, cfg.mode, margin),
            "reply_markup": json.dumps(_keyboard(sig)),
        })
        return sent.get("result", {}).get("message_id")
    except OSError:
        return None


def poll_callbacks(cfg, offset):
    """Poll getUpdates ONCE for button taps. Returns (new_offset, taps) where
    taps is a list of dicts {sig_id, decision('approve'|'skip'), callback_id}.
    ALWAYS answers each callback so the button never spins silently."""
    params = {"timeout": 0, "allowed_updates": '["callback_query"]'}
    if offset is not None:
        params["offset"] = offset
    try:
        updates = _call(cfg.telegram_bot_token, "getUpdates", params)
    except OSError:
        return offset, []
    taps = []
    for upd in updates.get("result", []):
        offset = upd["update_id"] + 1
        cq = upd.get("callback_query")
        if not cq:
            continue
        # answer immediately: the button always gets feedback, even if unknown/expired
        try:
            _call(cfg.telegram_bot_token, "answerCallbackQuery", {"callback_query_id": cq["id"]})
        except OSError:
            pass
        if str(cq.get("message", {}).get("chat", {}).get("id")) != str(cfg.telegram_chat_id):
            continue  # only the owner's chat can answer
        data = cq.get("data", "")
        if ":" not in data:
            continue
        decision, _, sig_id = data.partition(":")
        if decision in ("approve", "skip", "closeyes", "closeno", "closeleg"):
            taps.append({"sig_id": sig_id, "decision": decision})
    return offset, taps


def finalize_card(cfg, sig: dict, multiplier: int, message_id, status: str) -> None:
    """Edit a card in place to show its final status (Approved/Skipped/Expired + result)."""
    if not message_id:
        return
    try:
        _call(cfg.telegram_bot_token, "editMessageText", {
            "chat_id": cfg.telegram_chat_id,
            "message_id": message_id,
            "text": format_trade_card(sig, multiplier, cfg.mode) + "\n\n" + status,
        })
    except OSError:
        pass


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


def _leg_label(leg: dict) -> str:
    """Short button label from an OCC leg: e.g. '714P S' (strike, put/call, Short/Long)."""
    s = str(leg.get("symbol", "")).replace(" ", "")
    strike = cp = ""
    try:
        strike = str(int(int(s[-8:]) / 1000))
        cp = s[-9]  # 'P' or 'C'
    except (ValueError, IndexError):
        pass
    side = "S" if str(leg.get("dir", "")).lower().startswith("short") else "L"
    return f"{strike}{cp} {side}".strip()


def _close_keyboard(pid, legs_live=None) -> dict:
    rows = [[
        {"text": "✅ Close ALL", "callback_data": f"closeyes:{pid}"},
        {"text": "Hold", "callback_data": f"closeno:{pid}"},
    ]]
    # one button per leg for partial (per-leg) closes
    for i, leg in enumerate(legs_live or []):
        rows.append([{"text": f"Close leg {i+1}: {_leg_label(leg)}",
                      "callback_data": f"closeleg:{pid}:{i}"}])
    return {"inline_keyboard": rows}


def send_close_card(cfg, position: dict, pct: float, pnl: float, cost_to_close: float, legs_live=None):
    """Profit-target CLOSE alert with Close-ALL / Hold / per-leg buttons. Returns message_id."""
    sym = position.get("symbol", "?"); tr = position.get("trader", "?")
    sign = "+" if (pnl or 0) >= 0 else ""
    acct = "🧪 PAPER" if cfg.mode != "live" else "💵 LIVE account"
    txt = "\n".join([
        f"🎯 CLOSE ALERT — {sym} ({tr})",
        f"Captured +{pct:.0f}% of the credit  ({sign}${pnl:,.0f})",
        f"Close ALL to buy it back for ~${cost_to_close:,.0f}, or close a single leg.",
        "",
        acct,
    ])
    try:
        sent = _call(cfg.telegram_bot_token, "sendMessage", {
            "chat_id": cfg.telegram_chat_id, "text": txt,
            "reply_markup": json.dumps(_close_keyboard(position["id"], legs_live)),
        })
        return sent.get("result", {}).get("message_id")
    except OSError:
        return None


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

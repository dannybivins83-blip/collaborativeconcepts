"""The human gate: one-tap per-trade approval over Telegram.

HARD RAIL (overlord directive 2026-07-20): this gate must NEVER auto-approve.
No batch approvals, no per-trader trust bypass, and an unanswered request
EXPIRES TO SKIP. There is deliberately no code path that returns approval
without a human tapping the Approve button for this specific trade.
"""
import json
import time
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API.format(token=token, method=method), data=data)
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode())


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
    sent = _call(cfg.telegram_bot_token, "sendMessage", {
        "chat_id": cfg.telegram_chat_id,
        "text": format_trade_card(sig, multiplier, cfg.mode),
        "reply_markup": json.dumps(keyboard),
    })
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
    _call(cfg.telegram_bot_token, "editMessageText", {
        "chat_id": cfg.telegram_chat_id,
        "message_id": message_id,
        "text": format_trade_card(sig, multiplier, cfg.mode) + f"\n\n{outcome}",
    })
    return decision


def notify(cfg, text: str) -> None:
    try:
        _call(cfg.telegram_bot_token, "sendMessage", {"chat_id": cfg.telegram_chat_id, "text": text})
    except OSError:
        pass

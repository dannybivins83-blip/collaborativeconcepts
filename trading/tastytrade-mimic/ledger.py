"""Trade ledger + paper P&L scorecard for tt-mimic.

Every copied (approved) trade is appended to an append-only JSONL ledger
(documentation) and tracked as an open position in positions.json. A position
closes when the followed trader's CLOSING order appears in the feed, matched by
trader + leg symbols; realized P&L = open cash flow + close cash flow
(credit +, debit -), rolled up into a per-trader scorecard. No orders are ever
placed — this is pure record-keeping over the paper approvals.

Honest limits: positions the trader lets EXPIRE without an explicit close are
marked "expired" and excluded from realized P&L (no settlement data); there is
no intraday mark-to-market (unrealized) P&L.
"""
import json
import os


def cashflow(price, price_effect, contracts):
    """Signed cash for one options order: credit=+, debit=-, 100 shares/contract."""
    try:
        p = float(price)
        c = int(contracts)
    except (TypeError, ValueError):
        return 0.0
    sign = 1.0 if str(price_effect or "").lower() == "credit" else -1.0
    return round(p * 100.0 * c * sign, 2)


def leg_key(legs):
    """Order-independent match key: sorted set of leg symbols (spaces stripped)."""
    return sorted(str(leg.get("symbol", "")).replace(" ", "")
                  for leg in (legs or []) if leg.get("symbol"))


def _expiry(legs):
    """YYMMDD from the first OCC leg symbol (root padded to 6, then YYMMDD)."""
    for leg in (legs or []):
        s = str(leg.get("symbol", ""))
        if len(s) >= 12 and s[6:12].isdigit():
            return s[6:12]
    return ""


def record_open(sig, multiplier, result, ts):
    """A position record for a just-copied (approved) trade."""
    result = result if isinstance(result, dict) else {}
    return {
        "id": str(sig.get("id")),
        "trader": sig.get("trader", "?"),
        "symbol": sig.get("symbol", "?"),
        "legs": leg_key(sig.get("legs", [])),
        "expiry": _expiry(sig.get("legs", [])),
        "multiplier": int(multiplier),
        "open_price": sig.get("price"),
        "open_effect": sig.get("price_effect"),
        "open_cashflow": cashflow(sig.get("price"), sig.get("price_effect"), multiplier),
        "open_ts": ts,
        "order_id": result.get("order_id"),
        # A submitted order is NOT a position until tastytrade confirms the FILL.
        # order_id present -> pending (must be reconciled); none -> notional what-if.
        "status": "pending" if result.get("order_id") else "notional",
        "dry_status": result.get("status"),
        "bp_change": result.get("bp_change"),
        "fees": result.get("fees"),
    }



_TERMINAL_UNFILLED = {"Expired", "Cancelled", "Canceled", "Rejected", "Removed"}
_FILLED = {"Filled"}


def reconcile_fills(positions, broker):
    """Confirm pending orders against the broker: Filled -> real 'open' position;
    Expired/Cancelled/Rejected -> 'unfilled' (never counts for P&L). Returns changed list."""
    changed = []
    for pos in positions.values():
        if pos.get("status") != "pending":
            continue
        st = broker.order_status(pos.get("order_id"))
        if st in _FILLED:
            pos["status"] = "open"; changed.append(pos)
        elif st in _TERMINAL_UNFILLED:
            pos["status"] = "unfilled"; changed.append(pos)
        # else still working (Live/Received/Routed) -> leave pending
    return changed


def match_and_close(positions, close_sig, ts):
    """Close the first OPEN position matching close_sig by trader + leg set.
    Returns the closed position dict (with realized_pnl) or None."""
    ckey = leg_key(close_sig.get("legs", []))
    if not ckey:
        return None
    ctrader = close_sig.get("trader")
    for pos in positions.values():
        if pos.get("status") != "open" or pos.get("trader") != ctrader:
            continue
        if list(pos.get("legs", [])) != list(ckey):
            continue
        close_cf = cashflow(close_sig.get("price"), close_sig.get("price_effect"),
                            pos.get("multiplier", 1))
        pos.update({
            "status": "closed",
            "close_price": close_sig.get("price"),
            "close_effect": close_sig.get("price_effect"),
            "close_cashflow": close_cf,
            "close_ts": ts,
            "realized_pnl": round(float(pos.get("open_cashflow", 0.0)) + close_cf, 2),
        })
        return pos
    return None


def mark_expired(positions, today_yymmdd):
    """Mark still-open positions whose expiry has passed as 'expired' (unresolved)."""
    changed = []
    for pos in positions.values():
        if pos.get("status") == "open" and pos.get("expiry") and pos["expiry"] < str(today_yymmdd):
            pos["status"] = "expired"
            changed.append(pos)
    return changed


def scorecard(positions):
    """Per-trader + overall realized P&L, win rate, open/expired counts."""
    blank = lambda: {"realized_pnl": 0.0, "wins": 0, "losses": 0,
                     "closed": 0, "open": 0, "expired": 0,
                     "notional": 0, "unfilled": 0, "pending": 0}
    per, overall = {}, blank()
    for pos in positions.values():
        d = per.setdefault(pos.get("trader", "?"), blank())
        st = pos.get("status")
        if st == "closed":
            pnl = float(pos.get("realized_pnl", 0.0))
            for agg in (d, overall):
                agg["realized_pnl"] = round(agg["realized_pnl"] + pnl, 2)
                agg["closed"] += 1
                agg["wins" if pnl >= 0 else "losses"] += 1
        elif st == "expired":
            d["expired"] += 1; overall["expired"] += 1
        elif st in ("notional", "unfilled", "pending"):
            d[st] += 1; overall[st] += 1
        else:
            d["open"] += 1; overall["open"] += 1
    return {"per_trader": per, "overall": overall}


def _money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


def format_scorecard(sc):
    o = sc["overall"]
    wr = (o["wins"] / o["closed"] * 100) if o["closed"] else 0.0
    lines = ["📊 tt-mimic paper scorecard (realized P&L, closed trades only)",
             f"Overall: {_money(o['realized_pnl'])} | {o['closed']} closed, {wr:.0f}% win "
             f"| {o['open']} open, {o['expired']} expired-unresolved"]
    for t, d in sorted(sc["per_trader"].items(), key=lambda kv: kv[1]["realized_pnl"], reverse=True):
        twr = (d["wins"] / d["closed"] * 100) if d["closed"] else 0.0
        lines.append(f"  • {t}: {_money(d['realized_pnl'])} "
                     f"({d['closed']} closed, {twr:.0f}% win, {d['open']} open)")
    if not sc["per_trader"]:
        lines.append("  (no trades copied yet)")
    return "\n".join(lines)


# -- file-backed wrappers (pure fns above are unit-tested) ------------------
def append_jsonl(path, record):
    if not path:
        return
    try:
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def load_positions(path):
    if path and os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_positions(path, positions):
    if not path:
        return
    try:
        with open(path, "w") as f:
            json.dump(positions, f)
    except OSError:
        pass

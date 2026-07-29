"""Trade ledger + paper P&L scorecard for tt-mimic.

Every APPROVED trade is appended to an append-only JSONL ledger and tracked as a
position. When PAPER_EXECUTE is on the approval also SUBMITS a sandbox order
(order_id), reconciled against real fills; a disarmed approval places no order
and is tracked as a notional "what-if". A position closes when the followed
trader's CLOSING order appears in the feed (matched by trader + leg symbols).

Realized P&L = open cash flow + close cash flow (credit +, debit -), **NET of
estimated round-trip fees**. IMPORTANT: prices come from the TRADER'S feed — a
mirror estimate — NOT your exact sandbox fills. So the scorecard answers "would
mirroring this trader have made money", not "what your account's ledger literally
shows". Slippage between the trader's fill and yours is not captured.

Honest limits: expired-without-close trades are excluded from realized P&L (no
settlement data); no intraday unrealized mark-to-market; fees are ESTIMATED (the
feed doesn't price the close leg).
"""
import json
import os

# Round-trip commission+fee estimate per contract per leg, used when the broker's
# actual open fee wasn't captured. tastytrade ~ $1 commission (open only) +
# ~$0.15/side exchange+clearing; ~$1.30 round-trip per contract is a fair default.
FEE_PER_CONTRACT_ROUNDTRIP = float(os.environ.get("FEE_PER_CONTRACT_ROUNDTRIP", "1.30"))


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
        "status": "pending" if result.get("order_id") else "open",
        "dry_status": result.get("status"),
        "bp_change": result.get("bp_change"),
        "fees": result.get("fees"),
    }



_TERMINAL_UNFILLED = {"Expired", "Cancelled", "Canceled", "Rejected", "Removed"}
_FILLED = {"Filled"}


def round_trip_fees(pos):
    """Estimated round-trip commissions+fees for the WHOLE position. Prefer the
    broker's captured open fee (doubled for the unpriced close); else a
    per-contract-per-leg model. Callers scale by the fraction of legs closed."""
    try:
        of = float(pos.get("fees"))
        if of > 0:
            return round(of * 2.0, 2)
    except (TypeError, ValueError):
        pass
    n_legs = len(pos.get("legs") or [])
    contracts = int(pos.get("multiplier", 1) or 1)
    return round(n_legs * contracts * FEE_PER_CONTRACT_ROUNDTRIP, 2)


def _book_close(pos, price, effect, ckey, ts):
    """Realize P&L for closing legs `ckey` of an OPEN position. A full leg match
    closes it; a strict subset is a PARTIAL close (proportional-by-leg — an
    estimate, since the feed doesn't price legs individually). Realized P&L is
    NET of estimated round-trip fees. Returns the realized amount for this slice."""
    plegs = list(pos.get("legs", []))
    full = set(ckey) == set(plegs)
    frac = 1.0 if (full or not plegs) else len(ckey) / len(plegs)
    open_cf_all = float(pos.get("open_cashflow", 0.0))
    open_cf_part = round(open_cf_all * frac, 2)
    close_cf = cashflow(price, effect, pos.get("multiplier", 1))
    fees = round(round_trip_fees(pos) * frac, 2)
    realized = round(open_cf_part + close_cf - fees, 2)
    pos["realized_pnl_total"] = round(float(pos.get("realized_pnl_total", 0.0)) + realized, 2)
    pos.setdefault("closes", []).append({
        "close_price": price, "close_effect": effect, "close_ts": ts, "closed_legs": ckey,
        "close_cashflow": close_cf, "gross_pnl": round(open_cf_part + close_cf, 2),
        "fees_roundtrip": fees, "realized_pnl": realized})
    if full:
        pos["legs"] = []
    else:
        pos["legs"] = [l for l in plegs if l not in set(ckey)]
        pos["open_cashflow"] = round(open_cf_all - open_cf_part, 2)
    if not pos["legs"]:
        pos.update({"status": "closed", "realized_pnl": pos["realized_pnl_total"],
                    "close_price": price, "close_effect": effect, "close_ts": ts})
    else:
        pos["status"] = "partial"   # remainder still open; booked P&L counts already
    return realized


def reconcile_fills(positions, broker):
    """Confirm pending orders against the broker: Filled -> real 'open' position
    (and immediately apply any queued close — see match_and_close bug-1 fix);
    Expired/Cancelled/Rejected -> 'unfilled' (discards any queued close — never
    phantom P&L on an order that didn't fill). Returns changed list."""
    changed = []
    for pos in positions.values():
        if pos.get("status") != "pending":
            continue
        st = broker.order_status(pos.get("order_id"))
        if st in _FILLED:
            pos["status"] = "open"
            pc = pos.pop("pending_close", None)
            if pc:  # a close arrived while we were pending — book it now that we're filled
                _book_close(pos, pc.get("price"), pc.get("effect"), pc.get("legs", []), pc.get("ts", ""))
            changed.append(pos)
        elif st in _TERMINAL_UNFILLED:
            pos["status"] = "unfilled"
            pos.pop("pending_close", None)   # no fill -> no P&L, ever
            changed.append(pos)
        # else still working (Live/Received/Routed) -> leave pending
    return changed


def match_and_close(positions, close_sig, ts):
    """Apply a trader's CLOSE to a matching open/pending position.

    Fixes: (1) if our order is still PENDING (not confirmed filled), QUEUE the
    close and apply it only once the fill confirms — so a fast trader close is
    never lost, and an unfilled order never books phantom P&L. (2) match a SUBSET
    of legs (partial close, e.g. one side of a condor) instead of requiring the
    exact full leg set. Returns the affected position, or None."""
    ckey = leg_key(close_sig.get("legs", []))
    if not ckey:
        return None
    ctrader = close_sig.get("trader")
    for pos in positions.values():
        if pos.get("status") not in ("open", "pending", "partial") or pos.get("trader") != ctrader:
            continue
        if not (set(ckey) <= set(pos.get("legs", []))):   # close legs must be within the position
            continue
        if pos.get("status") == "pending":
            pos["pending_close"] = {"price": close_sig.get("price"),
                                    "effect": close_sig.get("price_effect"),
                                    "legs": ckey, "ts": ts}   # queued, not booked yet
            return pos
        _book_close(pos, close_sig.get("price"), close_sig.get("price_effect"), ckey, ts)
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


def is_real_fill(pos):
    """A position is REAL money only if it was a placed order (has an order_id)
    that actually filled. Disarmed/paper positions have no order_id = notional what-if."""
    return bool(pos.get("order_id"))


def scorecard(positions):
    """Splits P&L into REAL (an order was placed) vs WHAT-IF (approved only, no
    order). A breakeven ($0) is a SCRATCH, not a win. Partial closes book their
    realized slice already. 'overall' = combined (back-compat)."""
    blank = lambda: {"realized_pnl": 0.0, "wins": 0, "losses": 0, "scratches": 0,
                     "closed": 0, "open": 0, "partial": 0, "expired": 0,
                     "unfilled": 0, "pending": 0}
    per, overall, real, whatif = {}, blank(), blank(), blank()
    for pos in positions.values():
        d = per.setdefault(pos.get("trader", "?"), blank())
        split = real if is_real_fill(pos) else whatif
        st = pos.get("status")
        if st == "closed":
            pnl = float(pos.get("realized_pnl", 0.0))
            bucket = "wins" if pnl > 0 else ("losses" if pnl < 0 else "scratches")
            for agg in (d, overall, split):
                agg["realized_pnl"] = round(agg["realized_pnl"] + pnl, 2)
                agg["closed"] += 1
                agg[bucket] += 1
        elif st == "partial":   # remainder open, but the closed slice's P&L is real
            pnl = float(pos.get("realized_pnl_total", 0.0))
            for agg in (d, overall, split):
                agg["realized_pnl"] = round(agg["realized_pnl"] + pnl, 2)
                agg["partial"] += 1
        elif st in ("expired", "unfilled", "pending", "open"):
            for agg in (d, overall, split): agg[st] += 1
        else:
            for agg in (d, overall, split): agg["open"] += 1
    return {"per_trader": per, "overall": overall, "real": real, "whatif": whatif}


def _money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


def _winrate(a):
    return (a["wins"] / a["closed"] * 100) if a.get("closed") else 0.0


def format_scorecard(sc):
    r, w = sc.get("real", sc["overall"]), sc.get("whatif", {})
    lines = ["📊 tt-mimic scorecard",
             f"💵 REAL orders placed: {_money(r['realized_pnl'])} | {r['closed']} closed "
             f"({_winrate(r):.0f}% win, {r.get('scratches', 0)} scratch) "
             f"| {r['open']} open, {r.get('partial', 0)} partial"]
    if w and (w.get("closed") or w.get("open") or w.get("partial")):
        lines.append(f"🧪 WHAT-IF (approved only, no order): {_money(w['realized_pnl'])} "
                     f"| {w['closed']} closed ({_winrate(w):.0f}% win)")
    for t, d in sorted(sc["per_trader"].items(), key=lambda kv: kv[1]["realized_pnl"], reverse=True):
        lines.append(f"  • {t}: {_money(d['realized_pnl'])} "
                     f"({d['closed']} closed, {_winrate(d):.0f}% win, {d['open']} open)")
    if not sc["per_trader"]:
        lines.append("  (no trades copied yet)")
    lines.append("ℹ️ 'REAL' = an order was placed; P&L still MIRRORS the traders' fill prices "
                 "(not your exact fills, so slippage is excluded), net of estimated fees.")
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

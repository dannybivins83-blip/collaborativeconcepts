"""Profit-target EXIT manager for copied positions.

Watches the broker's LIVE position marks and, when an open position's captured
profit crosses a configured target (e.g. 20/30/50% of the credit received),
emits a CLOSE alert. Closing still requires a human tap — nothing auto-closes.

Profit convention (credit spreads, tastytrade "manage at X%"):
  credit received = |open_cashflow| (positive).
  cost_to_close   = what you'd pay now to buy the spread back =
                    sum(short leg marks) - sum(long leg marks), x100 x qty.
  captured        = credit - cost_to_close.
  pct             = captured / credit * 100.
For a net-DEBIT position, pct = (current_value - debit) / debit * 100.
Marks missing/zero -> return None (no alert; never fire on stale data).
"""
import json


def _mark_value(legs_marks):
    """Sum signed mark value to CLOSE: Short legs cost (+), Long legs credit (-)."""
    total = 0.0
    for m in legs_marks:
        mark = m.get("mark")
        if mark is None:
            return None  # any missing mark -> can't value the position
        qty = abs(float(m.get("qty") or 0))
        mult = float(m.get("multiplier") or 100)
        sign = 1.0 if (m.get("dir") or "").lower().startswith("short") else -1.0
        total += mark * qty * mult * sign
    return round(total, 2)


def captured_pct(position, legs_marks):
    """Return (pct, pnl_dollars) captured, or (None, None) if unvaluable.
    position is a ledger record with open_cashflow; legs_marks are the live marks
    of that position's legs [{mark, qty, dir, multiplier}]."""
    cost_to_close = _mark_value(legs_marks)
    if cost_to_close is None:
        return None, None
    credit = float(position.get("open_cashflow") or 0.0)
    if credit > 0:  # net credit position
        captured = credit - cost_to_close
        pct = captured / credit * 100.0 if credit else 0.0
        return round(pct, 1), round(captured, 2)
    if credit < 0:  # net debit position: cost_to_close is what it's worth now (a credit to close)
        debit = -credit
        current_value = -cost_to_close  # closing a long spread returns a credit
        captured = current_value - debit
        pct = captured / debit * 100.0 if debit else 0.0
        return round(pct, 1), round(captured, 2)
    return None, None


def next_target_crossed(pct, targets, already_alerted):
    """Highest target <= pct that hasn't been alerted yet, or None.
    targets: sorted list of ints e.g. [20,30,50]. already_alerted: set/list of ints."""
    if pct is None:
        return None
    crossed = [t for t in sorted(targets) if pct >= t and t not in set(already_alerted or [])]
    return crossed[-1] if crossed else None


def parse_targets(s):
    """'20,30,50' -> [20,30,50]. Empty/garbage -> [50] (tastytrade default)."""
    out = []
    for part in str(s or "").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return sorted(set(out)) or [50]

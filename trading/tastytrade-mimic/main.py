"""tastytrade Follow-Feed mimic trader — approval-only main loop.

Arming rules (all three required for a live order, checked every iteration):
  1. MODE=live            (env)
  2. --execute            (CLI flag)
  3. per-trade Telegram Approve tap (telegram_gate)
Anything less runs the order as an API dry-run only. KILL_SWITCH file halts all.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import ledger
from broker import BrokerError, TastytradeBroker
from config import Config
from signals import make_source, make_close_source
from telegram_gate import notify, request_approval, send_card, poll_callbacks, finalize_card


def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen": []}


def save_state(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f)


def _multiplier(cfg: Config, sig: dict) -> int:
    # Legs carry ratio-reduced quantities; MAX_CONTRACTS caps the largest leg.
    max_leg = max(int(leg.get("quantity", 1)) for leg in sig["legs"])
    return max(1, cfg.max_contracts // max_leg)


def execute_signal(cfg: Config, broker: TastytradeBroker, sig: dict, multiplier: int, armed: bool) -> str:
    """Place (dry-run unless armed) an ALREADY-APPROVED signal and notify the result."""
    try:
        result = broker.place(sig, multiplier, armed=armed)
    except BrokerError as e:
        notify(cfg, f"⚠️ Order failed for {sig['symbol']}: {e}",
               key="order-failed", cooldown_s=cfg.alert_cooldown_s)
        return "error"
    except Exception as e:  # never fail silently or crash the poll loop on a surprise
        notify(cfg, f"⚠️ Unexpected error handling {sig['symbol']}: {type(e).__name__}: {e}",
               key="unexpected-error", cooldown_s=cfg.alert_cooldown_s)
        return "error"
    if result["status"] == "submitted":
        venue = "LIVE" if cfg.mode == "live" else "PAPER (sandbox)"
        notify(cfg, f"📬 {venue} order submitted for {sig['symbol']} (id {result.get('order_id')})")
    else:
        cost = ""
        if result.get("bp_change") is not None:
            try:
                sign = "-" if result.get("bp_effect") == "Debit" else "+"
                cost = f" Buying power: {sign}${float(result['bp_change']):,.2f}."
                if result.get("fees") not in (None, ""):
                    cost += f" Fees: ${float(result['fees']):,.2f}."
            except (TypeError, ValueError):
                cost = ""
        detail = {"dry-run-only": "🧪 Dry-run OK",
                  "notification-only": "📣 Notification-only",
                  "rejected": "🚫 Order rejected"}.get(result["status"], "📣 Notification-only")
        notify(cfg, f"{detail} for {sig['symbol']} — not armed, no order placed.{cost} "
                    f"Warnings: {result.get('warnings') or 'none'}")
    # Record the copied trade to the ledger + open a paper position (no orders placed).
    if cfg.track_pnl and result["status"] in ("dry-run-only", "notification-only", "submitted"):
        ts = datetime.now(timezone.utc).isoformat()
        positions = ledger.load_positions(cfg.positions_file)
        rec = ledger.record_open(sig, multiplier, result, ts)
        positions[rec["id"]] = rec
        ledger.save_positions(cfg.positions_file, positions)
        ledger.append_jsonl(cfg.ledger_file, dict(rec, event="open"))
    return result["status"]


def process_signal(cfg: Config, broker: TastytradeBroker, sig: dict, armed: bool) -> str:
    """Blocking single-signal flow (kept for tests / --once compatibility)."""
    multiplier = _multiplier(cfg, sig)
    if not request_approval(cfg, sig, multiplier):
        return "skipped"
    return execute_signal(cfg, broker, sig, multiplier, armed)


def run(cfg: Config, execute_flag: bool, once: bool) -> int:
    problems = cfg.validate()
    if problems:
        print("Config problems:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    live_execute = cfg.mode == "live" and execute_flag       # submits to PRODUCTION (real money)
    paper_execute = cfg.mode == "paper" and cfg.paper_execute  # submits to CERT sandbox (fake money)
    armed = live_execute or paper_execute
    print(f"mode={cfg.mode} armed={armed} (paper_exec={paper_execute} live_exec={live_execute}) "
          f"source={cfg.signal_source} api={cfg.api_base}")
    if live_execute:
        notify(cfg, "🔴 tt-mimic is LIVE-ARMED (real money). Every trade still needs your tap.")
    elif paper_execute:
        notify(cfg, "🧪 tt-mimic PAPER-EXECUTE on — approved trades will FILL in the cert sandbox "
                    "(fake money, real fills). Every trade still needs your tap.")

    broker = TastytradeBroker(cfg)
    source = make_source(cfg)
    close_source = make_close_source(cfg) if cfg.track_pnl else None
    state = load_state(cfg.state_file)

    # Non-blocking approval model: cards are sent, then a SINGLE getUpdates poller
    # services taps for ANY pending card. A tap works anytime before expiry; every
    # tap is answered so the button never spins silently; multiple cards can be
    # pending at once. Only this process polls getUpdates -> no callback theft.
    pending = {}   # sig_id -> {"sig", "multiplier", "message_id", "expiry"}
    offset = None
    first_pass = True

    while True:
        now = time.time()
        if cfg.kill_switch_engaged():
            print("KILL_SWITCH engaged — idling, no polling, no orders")
            if once:
                return 0
            time.sleep(cfg.poll_interval_s)
            continue

        # 1) fetch new signals -> send cards (non-blocking) and register as pending
        if first_pass or not once:
            for sig in source.poll():
                if sig["id"] in state["seen"]:
                    continue
                state["seen"] = state["seen"][-500:] + [sig["id"]]
                save_state(cfg.state_file, state)  # mark seen BEFORE acting: never double-fire
                mult = _multiplier(cfg, sig)
                mid = send_card(cfg, sig, mult)
                pending[sig["id"]] = {"sig": sig, "multiplier": mult, "message_id": mid,
                                      "expiry": now + cfg.approval_timeout_s}
                print(f"card sent: {sig['id']} ({sig['trader']} {sig['symbol']})")
        first_pass = False

        # 2) service taps for ANY pending card
        offset, taps = poll_callbacks(cfg, offset)
        for tap in taps:
            p = pending.pop(tap["sig_id"], None)
            if p is None:
                continue  # tap on an already-resolved/expired card — button already answered
            if tap["decision"] == "skip":
                finalize_card(cfg, p["sig"], p["multiplier"], p["message_id"], "❌ Skipped")
                print(f"signal {tap['sig_id']}: skipped by tap")
                continue
            status = execute_signal(cfg, broker, p["sig"], p["multiplier"], armed)
            label = {"submitted": "📬 LIVE order submitted",
                     "dry-run-only": "✅ Approved — dry-run OK",
                     "notification-only": "✅ Approved — notification only",
                     "rejected": "🚫 Rejected by broker",
                     "error": "⚠️ Order error"}.get(status, "✅ Approved")
            finalize_card(cfg, p["sig"], p["multiplier"], p["message_id"], label)
            print(f"signal {tap['sig_id']}: {status}")

        # 2.5) realize P&L: when a followed trader CLOSES a position we copied,
        # match it and book realized P&L into the scorecard (no orders placed).
        if close_source is not None:
            try:
                closes = close_source.poll()
            except Exception:
                closes = []
            positions = ledger.load_positions(cfg.positions_file)
            dirty = bool(ledger.mark_expired(positions, datetime.now(timezone.utc).strftime("%y%m%d")))
            for csig in closes:
                closed = ledger.match_and_close(positions, csig, datetime.now(timezone.utc).isoformat())
                if not closed:
                    continue
                dirty = True
                ledger.append_jsonl(cfg.ledger_file, dict(closed, event="close"))
                tot = ledger.scorecard(positions)["per_trader"].get(closed["trader"], {}).get("realized_pnl", 0.0)
                notify(cfg, f"💵 {closed['trader']}'s {closed['symbol']} closed: "
                            f"{ledger._money(closed['realized_pnl'])} "
                            f"(running {ledger._money(tot)} on {closed['trader']})")
                print(f"closed {closed['id']} ({closed['trader']} {closed['symbol']}): {closed['realized_pnl']}")
            if dirty:
                ledger.save_positions(cfg.positions_file, positions)

        # 3) expire stale pending cards
        for sid in [s for s, pv in pending.items() if now >= pv["expiry"]]:
            p = pending.pop(sid)
            finalize_card(cfg, p["sig"], p["multiplier"], p["message_id"], "⏰ Expired → skipped")
            print(f"signal {sid}: expired")

        if once and not pending:
            return 0
        time.sleep(2 if once else cfg.poll_interval_s)


def main() -> int:
    parser = argparse.ArgumentParser(description="tastytrade follow-feed mimic (approval-only)")
    parser.add_argument("--execute", action="store_true",
                        help="arm live execution (requires MODE=live; per-trade approval still applies)")
    parser.add_argument("--once", action="store_true", help="process pending signals then exit")
    parser.add_argument("--scorecard", action="store_true",
                        help="print the paper P&L scorecard (per-trader realized results) and exit")
    args = parser.parse_args()
    if args.scorecard:
        cfg = Config()
        print(ledger.format_scorecard(ledger.scorecard(ledger.load_positions(cfg.positions_file))))
        return 0
    return run(Config(), execute_flag=args.execute, once=args.once)


if __name__ == "__main__":
    sys.exit(main())

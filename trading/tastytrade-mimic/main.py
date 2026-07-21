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

from broker import BrokerError, TastytradeBroker
from config import Config
from signals import make_source
from telegram_gate import notify, request_approval


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


def process_signal(cfg: Config, broker: TastytradeBroker, sig: dict, armed: bool) -> str:
    # Legs carry ratio-reduced quantities; MAX_CONTRACTS caps the largest leg.
    max_leg = max(int(leg.get("quantity", 1)) for leg in sig["legs"])
    multiplier = max(1, cfg.max_contracts // max_leg)
    approved = request_approval(cfg, sig, multiplier)
    if not approved:
        return "skipped"
    try:
        result = broker.place(sig, multiplier, armed=armed)
    except BrokerError as e:
        notify(cfg, f"⚠️ Order failed for {sig['symbol']}: {e}")
        return "error"
    if result["status"] == "submitted":
        notify(cfg, f"📬 LIVE order submitted for {sig['symbol']} (id {result.get('order_id')})")
    else:
        notify(cfg, f"🧪 Dry-run OK for {sig['symbol']} — not armed, no order placed. "
                    f"Warnings: {result.get('warnings') or 'none'}")
    return result["status"]


def run(cfg: Config, execute_flag: bool, once: bool) -> int:
    problems = cfg.validate()
    if problems:
        print("Config problems:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    armed = cfg.mode == "live" and execute_flag
    print(f"mode={cfg.mode} armed={armed} source={cfg.signal_source} api={cfg.api_base}")
    if armed:
        notify(cfg, "🔴 tt-mimic is ARMED (live + --execute). Every trade still needs your tap.")

    broker = TastytradeBroker(cfg)
    source = make_source(cfg)
    state = load_state(cfg.state_file)

    while True:
        if cfg.kill_switch_engaged():
            print("KILL_SWITCH engaged — idling, no polling, no orders")
            if once:
                return 0
            time.sleep(cfg.poll_interval_s)
            continue
        for sig in source.poll():
            if sig["id"] in state["seen"]:
                continue
            state["seen"] = state["seen"][-500:] + [sig["id"]]
            save_state(cfg.state_file, state)  # mark seen BEFORE acting: never double-fire
            outcome = process_signal(cfg, broker, sig, armed)
            print(f"signal {sig['id']} ({sig['trader']} {sig['symbol']}): {outcome}")
        if once:
            return 0
        time.sleep(cfg.poll_interval_s)


def main() -> int:
    parser = argparse.ArgumentParser(description="tastytrade follow-feed mimic (approval-only)")
    parser.add_argument("--execute", action="store_true",
                        help="arm live execution (requires MODE=live; per-trade approval still applies)")
    parser.add_argument("--once", action="store_true", help="process pending signals then exit")
    args = parser.parse_args()
    return run(Config(), execute_flag=args.execute, once=args.once)


if __name__ == "__main__":
    sys.exit(main())

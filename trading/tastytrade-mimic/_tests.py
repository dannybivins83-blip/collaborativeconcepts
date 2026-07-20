"""Offline tests for tt-mimic — no network, run with: python3 _tests.py"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import TastytradeBroker
from config import Config
from signals import FileSignalSource, parse_follow_feed, validate_signal
import main as main_mod


def sample_signal(**overrides):
    sig = {
        "id": "t1", "trader": "Tom", "symbol": "SPY", "order_type": "Limit",
        "price": 1.05, "price_effect": "Credit",
        "legs": [
            {"instrument_type": "Equity Option", "symbol": "SPY   260821P00550000",
             "action": "Sell to Open", "quantity": 1},
            {"instrument_type": "Equity Option", "symbol": "SPY   260821P00545000",
             "action": "Buy to Open", "quantity": 1},
        ],
    }
    sig.update(overrides)
    return sig


class ConfigTests(unittest.TestCase):
    def test_paper_mode_uses_sandbox(self):
        with mock.patch.dict(os.environ, {"MODE": "paper"}, clear=False):
            self.assertIn("cert", Config().api_base)

    def test_default_mode_is_paper(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            self.assertEqual(cfg.mode, "paper")
            self.assertIn("cert", cfg.api_base)

    def test_live_mode_uses_production(self):
        with mock.patch.dict(os.environ, {"MODE": "live"}, clear=False):
            self.assertEqual(Config().api_base, "https://api.tastytrade.com")

    def test_validate_reports_names_not_values(self):
        with mock.patch.dict(os.environ, {"TT_CLIENT_SECRET": "supersecret"}, clear=True):
            problems = Config().validate()
        self.assertTrue(any("TT_REFRESH_TOKEN" in p for p in problems))
        self.assertFalse(any("supersecret" in p for p in problems))

    def test_kill_switch(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "KILL_SWITCH")
            with mock.patch.dict(os.environ, {"KILL_SWITCH_FILE": path}, clear=False):
                cfg = Config()
                self.assertFalse(cfg.kill_switch_engaged())
                open(path, "w").close()
                self.assertTrue(cfg.kill_switch_engaged())


class SignalTests(unittest.TestCase):
    def test_valid_signal_passes(self):
        self.assertEqual(validate_signal(sample_signal()), [])

    def test_missing_legs_fails(self):
        self.assertTrue(validate_signal(sample_signal(legs=[])))

    def test_file_source_reads_valid_and_skips_garbage(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "signals.json")
            with open(path, "w") as f:
                json.dump([sample_signal(), {"junk": True}, "nope"], f)
            sigs = FileSignalSource(path).poll()
            self.assertEqual(len(sigs), 1)
            self.assertEqual(sigs[0]["id"], "t1")

    def test_file_source_tolerates_missing_and_malformed(self):
        self.assertEqual(FileSignalSource("/nonexistent/x.json").poll(), [])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as f:
                f.write("{not json")
            self.assertEqual(FileSignalSource(path).poll(), [])

    def test_parse_follow_feed_envelope(self):
        raw = {"data": {"items": [sample_signal(), {"noise": 1}]}}
        self.assertEqual(len(parse_follow_feed(raw)), 1)


class BrokerTests(unittest.TestCase):
    def test_build_order_maps_legs_and_price(self):
        order = TastytradeBroker.build_order(sample_signal(), qty=1)
        self.assertEqual(order["order-type"], "Limit")
        self.assertEqual(order["price"], "1.05")
        self.assertEqual(len(order["legs"]), 2)
        self.assertEqual(order["legs"][0]["action"], "Sell to Open")

    def test_disarmed_place_never_submits(self):
        cfg = Config()
        broker = TastytradeBroker(cfg)
        calls = []

        def fake_request(method, path, payload=None):
            calls.append(path)
            if path.endswith("dry-run"):
                return {"data": {"warnings": []}}
            raise AssertionError("real order endpoint must not be hit when disarmed")

        with mock.patch.object(broker, "_request", side_effect=fake_request), \
             mock.patch.object(broker, "account_number", return_value="5WT00000"):
            result = broker.place(sample_signal(), qty=1, armed=False)
        self.assertEqual(result["status"], "dry-run-only")
        self.assertTrue(all("dry-run" in c for c in calls if "orders" in c))


class ArmingTests(unittest.TestCase):
    def _run(self, mode, execute_flag):
        captured = {}

        def fake_process(cfg, broker, sig, armed):
            captured["armed"] = armed
            return "skipped"

        env = {"MODE": mode, "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_FILE": sig_path, "STATE_FILE": os.path.join(d, "s.json"),
                        "KILL_SWITCH_FILE": os.path.join(d, "KILL_SWITCH")})
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(main_mod, "process_signal", side_effect=fake_process), \
                 mock.patch.object(main_mod, "notify"):
                rc = main_mod.run(Config(), execute_flag=execute_flag, once=True)
        return rc, captured

    def test_paper_mode_never_armed_even_with_execute(self):
        rc, captured = self._run("paper", execute_flag=True)
        self.assertEqual(rc, 0)
        self.assertFalse(captured["armed"])

    def test_live_without_execute_not_armed(self):
        rc, captured = self._run("live", execute_flag=False)
        self.assertEqual(rc, 0)
        self.assertFalse(captured["armed"])

    def test_live_with_execute_is_armed(self):
        rc, captured = self._run("live", execute_flag=True)
        self.assertEqual(rc, 0)
        self.assertTrue(captured["armed"])

    def test_kill_switch_blocks_everything(self):
        env = {"MODE": "live", "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            kill = os.path.join(d, "KILL_SWITCH")
            open(kill, "w").close()
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_FILE": sig_path, "STATE_FILE": os.path.join(d, "s.json"),
                        "KILL_SWITCH_FILE": kill})
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(main_mod, "process_signal") as proc, \
                 mock.patch.object(main_mod, "notify"):
                rc = main_mod.run(Config(), execute_flag=True, once=True)
        self.assertEqual(rc, 0)
        proc.assert_not_called()

    def test_signals_deduped_across_runs(self):
        env = {"MODE": "paper", "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_FILE": sig_path, "STATE_FILE": os.path.join(d, "s.json"),
                        "KILL_SWITCH_FILE": os.path.join(d, "KILL_SWITCH")})
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(main_mod, "process_signal", return_value="skipped") as proc, \
                 mock.patch.object(main_mod, "notify"):
                main_mod.run(Config(), execute_flag=False, once=True)
                main_mod.run(Config(), execute_flag=False, once=True)
            self.assertEqual(proc.call_count, 1)


class ApprovalGateTests(unittest.TestCase):
    def test_expiry_returns_skip_never_approve(self):
        import telegram_gate
        cfg = Config()
        object.__setattr__(cfg, "approval_timeout_s", 0)  # expire immediately
        object.__setattr__(cfg, "telegram_bot_token", "x")
        object.__setattr__(cfg, "telegram_chat_id", "1")
        with mock.patch.object(telegram_gate, "_call",
                               return_value={"ok": True, "result": {"message_id": 1}}):
            self.assertFalse(telegram_gate.request_approval(cfg, sample_signal(), qty=1))

    def test_wrong_chat_cannot_approve(self):
        import telegram_gate
        cfg = Config()
        object.__setattr__(cfg, "approval_timeout_s", 1)
        object.__setattr__(cfg, "telegram_bot_token", "x")
        object.__setattr__(cfg, "telegram_chat_id", "1")
        stranger_tap = {"ok": True, "result": [{
            "update_id": 10,
            "callback_query": {"id": "cq1", "data": "approve:t1",
                               "message": {"chat": {"id": 999}}},
        }]}

        def fake_call(token, method, params):
            if method == "sendMessage":
                return {"ok": True, "result": {"message_id": 1}}
            if method == "getUpdates":
                return stranger_tap
            return {"ok": True}

        with mock.patch.object(telegram_gate, "_call", side_effect=fake_call):
            self.assertFalse(telegram_gate.request_approval(cfg, sample_signal(), qty=1))


if __name__ == "__main__":
    unittest.main(verbosity=2)

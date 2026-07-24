"""Offline tests for tt-mimic — no network, run with: python3 _tests.py"""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone

from broker import TastytradeBroker
from config import Config
from signals import FileSignalSource, occ_symbol, parse_follow_feed, validate_signal
import main as main_mod
import ledger

# Real payload captured from the public follow-feed endpoint on 2026-07-21
CAPTURED_FEED = {"public_orders": [{
    "id": 43227967, "expiration": "DAY", "order_type": "net_credit",
    "price": "0.2", "strategy": "Custom", "reason": "Super bear for today!",
    "executed_at": "2026-07-21T14:11:00Z", "filled_at": "2026-07-21T14:11:47Z",
    "probability_of_profit": "80.9986714293475", "underlying_price": "7476.76",
    "placed_at": "2026-07-21T13:31:38Z", "trader_id": 36625, "is_hedge": True,
    "tos_iv_rank": "42.7565392",
    "order_legs": [
        {"symbol": "SPXW 260721P07435000", "action": "selltoopen", "quantity": "1.0",
         "underlying_symbol": "SPX", "strike_price": "7435.0", "call_or_put": "P"},
        {"symbol": "SPXW 260721C07520000", "action": "buytoopen", "quantity": "1.0",
         "underlying_symbol": "SPX", "strike_price": "7520.0", "call_or_put": "C"},
        {"symbol": "SPXW 260721C07510000", "action": "selltoopen", "quantity": "1.0",
         "underlying_symbol": "SPX", "strike_price": "7510.0", "call_or_put": "C"},
        {"symbol": "SPXW 260721P07445000", "action": "buytoopen", "quantity": "1.0",
         "underlying_symbol": "SPX", "strike_price": "7445.0", "call_or_put": "P"},
    ],
    "comments": [],
}]}
FEED_NOW = datetime(2026, 7, 21, 14, 30, tzinfo=timezone.utc)


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

    def test_api_base_env_overridable(self):
        with mock.patch.dict(os.environ, {"MODE": "live", "TT_API_BASE_LIVE": "https://api.example.com"}, clear=True):
            self.assertEqual(Config().api_base, "https://api.example.com")
        with mock.patch.dict(os.environ, {"MODE": "paper", "TT_API_BASE_PAPER": "https://sbx.example.com"}, clear=True):
            self.assertEqual(Config().api_base, "https://sbx.example.com")

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

    def test_parse_captured_feed_payload(self):
        sigs = parse_follow_feed(CAPTURED_FEED, trader_names={"36625": "Tom Preston"},
                                 now=FEED_NOW)
        self.assertEqual(len(sigs), 1)
        sig = sigs[0]
        self.assertEqual(sig["id"], "43227967")
        self.assertEqual(sig["trader"], "Tom Preston")
        self.assertEqual(sig["symbol"], "SPX")
        self.assertEqual(sig["order_type"], "Limit")
        self.assertEqual(sig["price_effect"], "Credit")
        self.assertEqual(sig["price"], 0.2)
        self.assertEqual(len(sig["legs"]), 4)
        self.assertEqual(sig["legs"][0]["symbol"], "SPXW  260721P07435000")  # OCC padding
        self.assertEqual(sig["legs"][0]["action"], "Sell to Open")
        self.assertEqual(sig["legs"][1]["action"], "Buy to Open")
        self.assertTrue(all(leg["quantity"] == 1 for leg in sig["legs"]))
        self.assertEqual(validate_signal(sig), [])  # feeds straight into the pipeline

    def test_parse_skips_unfilled_orders(self):
        feed = {"public_orders": [dict(CAPTURED_FEED["public_orders"][0], filled_at=None)]}
        self.assertEqual(parse_follow_feed(feed, now=FEED_NOW), [])

    def test_parse_skips_stale_orders(self):
        old_now = datetime(2026, 7, 22, 14, 30, tzinfo=timezone.utc)  # next day
        self.assertEqual(parse_follow_feed(CAPTURED_FEED, max_age_min=180, now=old_now), [])

    def test_parse_reduces_ratio_quantities(self):
        order = dict(CAPTURED_FEED["public_orders"][0])
        order["order_legs"] = [
            dict(order["order_legs"][0], quantity="10.0"),
            dict(order["order_legs"][1], quantity="20.0"),
        ]
        sigs = parse_follow_feed({"public_orders": [order]}, now=FEED_NOW)
        self.assertEqual([leg["quantity"] for leg in sigs[0]["legs"]], [1, 2])

    def test_parse_unknown_trader_gets_id_label(self):
        sigs = parse_follow_feed(CAPTURED_FEED, now=FEED_NOW)
        self.assertEqual(sigs[0]["trader"], "Trader 36625")

    def test_occ_symbol_padding(self):
        self.assertEqual(occ_symbol("SPXW 260721P07435000"), "SPXW  260721P07435000")
        self.assertEqual(occ_symbol("SPY 260904P00550000"), "SPY   260904P00550000")
        self.assertIsNone(occ_symbol("garbage"))


class BrokerTests(unittest.TestCase):
    def test_build_order_maps_legs_and_price(self):
        order = TastytradeBroker.build_order(sample_signal(), 1)
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
            result = broker.place(sample_signal(), 1, armed=False)
        self.assertEqual(result["status"], "dry-run-only")
        self.assertTrue(all("dry-run" in c for c in calls if "orders" in c))


class ArmingTests(unittest.TestCase):
    """run() uses the non-blocking approval model: send_card -> poll_callbacks ->
    execute_signal on an Approve tap. These mock that seam and verify arming."""
    def _run(self, mode, execute_flag):
        captured = {}
        def fake_execute(cfg, broker, sig, multiplier, armed):
            captured["armed"] = armed
            return "dry-run-only"
        env = {"MODE": mode, "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TT_PROD_CLIENT_SECRET": "prod_x", "TT_PROD_REFRESH_TOKEN": "prod_y",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_SOURCE": "file", "SIGNAL_FILE": sig_path,
                        "STATE_FILE": os.path.join(d, "s.json"),
                        "KILL_SWITCH_FILE": os.path.join(d, "KILL_SWITCH")})
            with mock.patch.dict(os.environ, env, clear=True),                  mock.patch.object(main_mod, "send_card", return_value=111),                  mock.patch.object(main_mod, "poll_callbacks",
                                   return_value=(1, [{"sig_id": "t1", "decision": "approve"}])),                  mock.patch.object(main_mod, "execute_signal", side_effect=fake_execute),                  mock.patch.object(main_mod, "finalize_card"),                  mock.patch.object(main_mod, "notify"):
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
               "TT_PROD_CLIENT_SECRET": "prod_x", "TT_PROD_REFRESH_TOKEN": "prod_y",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            kill = os.path.join(d, "KILL_SWITCH")
            open(kill, "w").close()
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_SOURCE": "file", "SIGNAL_FILE": sig_path,
                        "STATE_FILE": os.path.join(d, "s.json"), "KILL_SWITCH_FILE": kill})
            with mock.patch.dict(os.environ, env, clear=True),                  mock.patch.object(main_mod, "send_card") as sc,                  mock.patch.object(main_mod, "execute_signal") as ex,                  mock.patch.object(main_mod, "poll_callbacks", return_value=(None, [])),                  mock.patch.object(main_mod, "notify"):
                rc = main_mod.run(Config(), execute_flag=True, once=True)
        self.assertEqual(rc, 0)
        sc.assert_not_called()       # kill switch -> no card sent
        ex.assert_not_called()       # kill switch -> nothing executed

    def test_signals_deduped_across_runs(self):
        env = {"MODE": "paper", "TT_CLIENT_SECRET": "x", "TT_REFRESH_TOKEN": "x",
               "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        with tempfile.TemporaryDirectory() as d:
            sig_path = os.path.join(d, "signals.json")
            with open(sig_path, "w") as f:
                json.dump([sample_signal()], f)
            env.update({"SIGNAL_SOURCE": "file", "SIGNAL_FILE": sig_path,
                        "STATE_FILE": os.path.join(d, "s.json"),
                        "KILL_SWITCH_FILE": os.path.join(d, "KILL_SWITCH")})
            with mock.patch.dict(os.environ, env, clear=True),                  mock.patch.object(main_mod, "send_card", return_value=111) as sc,                  mock.patch.object(main_mod, "poll_callbacks",
                                   return_value=(1, [{"sig_id": "t1", "decision": "approve"}])),                  mock.patch.object(main_mod, "execute_signal", return_value="dry-run-only"),                  mock.patch.object(main_mod, "finalize_card"),                  mock.patch.object(main_mod, "notify"):
                main_mod.run(Config(), execute_flag=False, once=True)
                main_mod.run(Config(), execute_flag=False, once=True)
            self.assertEqual(sc.call_count, 1)   # card sent once across both runs


class ApprovalGateTests(unittest.TestCase):
    def test_expiry_returns_skip_never_approve(self):
        import telegram_gate
        cfg = Config()
        object.__setattr__(cfg, "approval_timeout_s", 0)  # expire immediately
        object.__setattr__(cfg, "telegram_bot_token", "x")
        object.__setattr__(cfg, "telegram_chat_id", "1")
        with mock.patch.object(telegram_gate, "_call",
                               return_value={"ok": True, "result": {"message_id": 1}}):
            self.assertFalse(telegram_gate.request_approval(cfg, sample_signal(), 1))

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
            self.assertFalse(telegram_gate.request_approval(cfg, sample_signal(), 1))


class TokenRequestTests(unittest.TestCase):
    """The OAuth refresh body — client_id is included only when provisioned."""

    def _capture_token_body(self, env):
        captured = {}

        class OKResp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return json.dumps({"access_token": "AT", "expires_in": 900}).encode()

        def fake_urlopen(req, timeout=0):
            captured["body"] = req.data.decode()
            return OKResp()

        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            token = TastytradeBroker(Config())._token()
        self.assertEqual(token, "AT")
        return captured["body"]

    def test_token_includes_client_id_when_set(self):
        body = self._capture_token_body(
            {"TT_CLIENT_SECRET": "s", "TT_REFRESH_TOKEN": "r", "TT_CLIENT_ID": "cid"})
        self.assertIn("client_id=cid", body)
        self.assertIn("grant_type=refresh_token", body)

    def test_token_omits_client_id_when_absent(self):
        body = self._capture_token_body({"TT_CLIENT_SECRET": "s", "TT_REFRESH_TOKEN": "r"})
        self.assertNotIn("client_id", body)


class TelegramTransportTests(unittest.TestCase):
    def test_call_retries_on_429_then_succeeds(self):
        import telegram_gate
        calls = {"n": 0}

        class OKResp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return json.dumps({"ok": True, "result": {}}).encode()

        def fake_urlopen(req, timeout=0):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(
                    "http://x", 429, "Too Many Requests", {"Retry-After": "1"}, None)
            return OKResp()

        with mock.patch.object(telegram_gate, "_sleep") as slept, \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            out = telegram_gate._call("tok", "sendMessage", {"a": 1})
        self.assertEqual(out, {"ok": True, "result": {}})
        self.assertEqual(calls["n"], 2)   # retried once after the 429
        slept.assert_called_once()        # honored the backoff instead of crashing

    def test_call_fails_fast_on_4xx(self):
        import telegram_gate

        def fake_urlopen(req, timeout=0):
            raise urllib.error.HTTPError("http://x", 400, "Bad Request", {}, None)

        with mock.patch.object(telegram_gate, "_sleep") as slept, \
             mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(urllib.error.HTTPError):
                telegram_gate._call("tok", "sendMessage", {"a": 1})
        slept.assert_not_called()         # non-429 4xx is not retried

    def test_approval_returns_false_when_send_fails(self):
        import telegram_gate
        cfg = Config()
        object.__setattr__(cfg, "telegram_bot_token", "x")
        object.__setattr__(cfg, "telegram_chat_id", "1")

        def boom(token, method, params):
            raise OSError("telegram unreachable")

        with mock.patch.object(telegram_gate, "_call", side_effect=boom):
            # a dead gate must mean SKIP, never approve, and never crash the loop
            self.assertFalse(telegram_gate.request_approval(cfg, sample_signal(), 1))


class TokenErrorTests(unittest.TestCase):
    """Auth/network failures must surface as BrokerError, never silent crashes."""

    def _broker(self, env):
        with mock.patch.dict(os.environ, env, clear=True):
            return TastytradeBroker(Config())

    def test_token_http_error_becomes_broker_error(self):
        import io
        from broker import BrokerError
        broker = self._broker({"TT_CLIENT_SECRET": "s", "TT_REFRESH_TOKEN": "r"})

        def fake_urlopen(req, timeout=0):
            raise urllib.error.HTTPError(
                "http://x/oauth/token", 401, "Unauthorized", {},
                io.BytesIO(b'{"error":"invalid_client"}'))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(BrokerError) as ctx:
                broker._token()
        self.assertIn("401", str(ctx.exception))

    def test_token_network_error_becomes_broker_error(self):
        from broker import BrokerError
        broker = self._broker({"TT_CLIENT_SECRET": "s", "TT_REFRESH_TOKEN": "r"})

        def fake_urlopen(req, timeout=0):
            raise urllib.error.URLError("connection refused")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(BrokerError):
                broker._token()

    def test_token_400_gives_regenerate_hint(self):
        import io
        from broker import BrokerError
        broker = self._broker({"TT_CLIENT_SECRET": "s", "TT_REFRESH_TOKEN": "r"})

        def fake_urlopen(req, timeout=0):
            raise urllib.error.HTTPError(
                "http://x/oauth/token", 400, "Bad Request", {},
                io.BytesIO(b'{"error":"invalid_grant","error_description":"Grant revoked"}'))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(BrokerError) as ctx:
                broker._token()
        self.assertIn("regenerate", str(ctx.exception).lower())  # actionable hint


class ProcessSignalErrorTests(unittest.TestCase):
    """After approval, any failure must notify the owner and not crash the loop."""

    def _run_with_place(self, place_exc):
        cfg = Config()
        broker = TastytradeBroker(cfg)
        msgs = []
        with mock.patch.object(broker, "place", side_effect=place_exc), \
             mock.patch.object(main_mod, "request_approval", return_value=True), \
             mock.patch.object(main_mod, "notify", side_effect=lambda c, t, **kw: msgs.append(t)):
            outcome = main_mod.process_signal(cfg, broker, sample_signal(), armed=False)
        return outcome, msgs

    def test_broker_error_notifies_order_failed(self):
        from broker import BrokerError
        outcome, msgs = self._run_with_place(BrokerError("HTTP 401: invalid_client"))
        self.assertEqual(outcome, "error")
        self.assertTrue(any("Order failed" in m and "401" in m for m in msgs))

    def test_unexpected_error_still_notifies_and_returns_error(self):
        # a raw KeyError (the old silent-crash path) must now notify, not propagate
        outcome, msgs = self._run_with_place(KeyError("account-number"))
        self.assertEqual(outcome, "error")
        self.assertTrue(any("SPY" in m for m in msgs))


class NotifyDedupeTests(unittest.TestCase):
    def setUp(self):
        import telegram_gate
        telegram_gate._recent_alerts.clear()

    def _cfg(self):
        cfg = Config()
        object.__setattr__(cfg, "telegram_bot_token", "x")
        object.__setattr__(cfg, "telegram_chat_id", "1")
        return cfg

    def test_keyed_alert_deduped_within_cooldown(self):
        import telegram_gate
        cfg = self._cfg()
        with mock.patch.object(telegram_gate, "_call") as call:
            telegram_gate.notify(cfg, "cred dead", key="order-failed", cooldown_s=3600)
            telegram_gate.notify(cfg, "cred still dead", key="order-failed", cooldown_s=3600)
        self.assertEqual(call.call_count, 1)  # repeat suppressed within cooldown

    def test_unkeyed_alert_always_sends(self):
        import telegram_gate
        cfg = self._cfg()
        with mock.patch.object(telegram_gate, "_call") as call:
            telegram_gate.notify(cfg, "dry-run ok")
            telegram_gate.notify(cfg, "dry-run ok")
        self.assertEqual(call.call_count, 2)  # confirmations never deduped

    def test_distinct_keys_both_send(self):
        import telegram_gate
        cfg = self._cfg()
        with mock.patch.object(telegram_gate, "_call") as call:
            telegram_gate.notify(cfg, "a", key="order-failed", cooldown_s=3600)
            telegram_gate.notify(cfg, "b", key="unexpected-error", cooldown_s=3600)
        self.assertEqual(call.call_count, 2)




# --- reconciliation safety: armed vs disarmed on a dead broker (overlord 2026-07-22) ---
import unittest as _ut
from broker import TastytradeBroker as _TB, BrokerError as _BE

class BrokerDegradationTest(_ut.TestCase):
    def _broker(self):
        class _Cfg:
            tt_client_secret="x"; tt_refresh_token="x"
            api_base="https://api.cert.tastyworks.com"; max_contracts=1
        b=_TB(_Cfg())
        def _boom(*a,**k): raise _BE("OAuth token refresh -> HTTP 400: Grant revoked")
        b.account_number=_boom            # simulate dead grant
        b._request=_boom
        return b
    def _sig(self):
        return {"symbol":"SPY","trader":"Tom","price":0.5,"price_effect":"Credit","legs":[{"instrument_type":"Equity Option","symbol":"SPY   260821P00700000","quantity":1,"action":"Sell to Open"}]}
    def test_disarmed_unreachable_degrades(self):
        r=self._broker().place(self._sig(),1,armed=False)
        self.assertEqual(r["status"],"notification-only")   # graceful, no crash
    def test_armed_unreachable_raises(self):
        with self.assertRaises(_BE):                         # loud fail, places nothing
            self._broker().place(self._sig(),1,armed=True)


class BrokerRejectionTest(_ut.TestCase):
    """A 4xx from the dry-run engine is an order REJECTION, not an outage."""
    def _broker(self, code):
        class _Cfg:
            tt_client_secret="x"; tt_refresh_token="x"
            api_base="https://api.cert.tastyworks.com"; max_contracts=1
        b=_TB(_Cfg())
        b.account_number=lambda: "6AC21859"                  # auth OK
        def _boom(*a,**k): raise _BE("POST /orders/dry-run -> HTTP %d: bad symbol" % code, code=code)
        b._request=_boom
        return b
    def _sig(self):
        return {"symbol":"SPY","trader":"Tom","price":0.5,"price_effect":"Credit",
                "legs":[{"instrument_type":"Equity Option","symbol":"SPY   260821P00700000",
                         "quantity":1,"action":"Sell to Open"}]}
    def test_422_rejection_surfaces_reason(self):
        r=self._broker(422).place(self._sig(),1,armed=False)
        self.assertEqual(r["status"],"rejected")
        self.assertIn("order rejected", r["warnings"][0])
    def test_5xx_degrades_to_notification_only(self):
        self.assertEqual(self._broker(503).place(self._sig(),1,armed=False)["status"],"notification-only")
    def test_auth_401_stays_notification_only(self):
        self.assertEqual(self._broker(401).place(self._sig(),1,armed=False)["status"],"notification-only")
    def test_broker_error_carries_code(self):
        self.assertEqual(_BE("x",code=422).code,422)
        self.assertIsNone(_BE("y").code)


# --- card economics: total investment + best-case ROI (overlord 2026-07-22) ---
import unittest as _ut2, telegram_gate as _tg
class SpreadEconomicsTest(_ut2.TestCase):
    def _sig(self, price, eff, k1, k2):
        return {"symbol":"SPY","price":price,"price_effect":eff,"legs":[
            {"symbol":"SPY   260821P%08d"%(k1*1000),"action":"Sell to Open","quantity":1},
            {"symbol":"SPY   260821P%08d"%(k2*1000),"action":"Buy to Open","quantity":1}]}
    def test_credit_spread_roi(self):
        inv,prof,roi=_tg._spread_economics(self._sig(0.60,"Credit",714,711),1)
        self.assertEqual(round(inv),240); self.assertEqual(round(prof),60); self.assertEqual(round(roi),25)
    def test_debit_spread_scales(self):
        inv,prof,roi=_tg._spread_economics(self._sig(1.20,"Debit",500,505),2)
        self.assertEqual(round(inv),240); self.assertEqual(round(prof),760)
    def test_single_leg_returns_none(self):
        s={"symbol":"SPY","price":1.0,"price_effect":"Credit","legs":[{"symbol":"SPY   260821P00700000","action":"Sell to Open","quantity":1}]}
        self.assertIsNone(_tg._spread_economics(s,1))


class LedgerTest(unittest.TestCase):
    def _open_sig(self):
        return {"id": "o1", "trader": "Tom", "symbol": "SPY", "price": 1.05, "price_effect": "Credit",
                "legs": [{"symbol": "SPY   260821P00550000"}, {"symbol": "SPY   260821P00545000"}]}

    def _close(self, trader="Tom", price=0.40, eff="Debit"):
        return {"trader": trader, "symbol": "SPY", "price": price, "price_effect": eff,
                "legs": [{"symbol": "SPY   260821P00550000"}, {"symbol": "SPY   260821P00545000"}]}

    def test_cashflow_signs(self):
        self.assertEqual(ledger.cashflow(1.05, "Credit", 1), 105.0)   # credit in, +
        self.assertEqual(ledger.cashflow(0.40, "Debit", 2), -80.0)    # debit out, -

    def test_leg_key_ignores_spaces_and_order(self):
        a = ledger.leg_key([{"symbol": "SPY   260821P00545000"}, {"symbol": "SPY   260821P00550000"}])
        b = ledger.leg_key([{"symbol": "SPY260821P00550000"}, {"symbol": "SPY260821P00545000"}])
        self.assertEqual(a, b)

    def test_open_then_trader_close_realizes_pnl(self):
        pos = {}
        rec = ledger.record_open(self._open_sig(), 1, {"status": "dry-run-only"}, "t0")
        pos[rec["id"]] = rec
        closed = ledger.match_and_close(pos, self._close(price=0.40), "t1")
        self.assertIsNotNone(closed)
        self.assertEqual(closed["realized_pnl"], 65.0)   # +105 credit, -40 to buy back
        self.assertEqual(pos["o1"]["status"], "closed")

    def test_close_wrong_trader_no_match(self):
        pos = {}
        rec = ledger.record_open(self._open_sig(), 1, {}, "t0")
        pos[rec["id"]] = rec
        self.assertIsNone(ledger.match_and_close(pos, self._close(trader="Jim"), "t1"))
        self.assertEqual(pos["o1"]["status"], "open")

    def test_scorecard_rollup_and_winrate(self):
        pos = {}
        rec = ledger.record_open(self._open_sig(), 1, {}, "t0")
        pos[rec["id"]] = rec
        ledger.match_and_close(pos, self._close(price=0.40), "t1")   # +65 win
        sc = ledger.scorecard(pos)
        self.assertEqual(sc["overall"]["realized_pnl"], 65.0)
        self.assertEqual(sc["overall"]["closed"], 1)
        self.assertEqual(sc["overall"]["wins"], 1)
        self.assertEqual(sc["per_trader"]["Tom"]["realized_pnl"], 65.0)

    def test_losing_close_counts_as_loss(self):
        pos = {}
        rec = ledger.record_open(self._open_sig(), 1, {}, "t0")
        pos[rec["id"]] = rec
        ledger.match_and_close(pos, self._close(price=2.00), "t1")   # +105 - 200 = -95
        self.assertEqual(pos["o1"]["realized_pnl"], -95.0)
        self.assertEqual(ledger.scorecard(pos)["overall"]["losses"], 1)

    def test_mark_expired_excluded_from_realized(self):
        pos = {}
        rec = ledger.record_open(self._open_sig(), 1, {}, "t0")   # expiry 260821
        pos[rec["id"]] = rec
        self.assertTrue(ledger.mark_expired(pos, "260901"))        # past expiry
        self.assertEqual(pos["o1"]["status"], "expired")
        sc = ledger.scorecard(pos)
        self.assertEqual(sc["overall"]["expired"], 1)
        self.assertEqual(sc["overall"]["realized_pnl"], 0.0)

    def test_ledger_and_positions_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            pp = os.path.join(d, "positions.json")
            ledger.save_positions(pp, {"o1": {"trader": "Tom", "status": "open"}})
            self.assertEqual(ledger.load_positions(pp)["o1"]["trader"], "Tom")
            lj = os.path.join(d, "trades.jsonl")
            ledger.append_jsonl(lj, {"event": "open", "id": "o1"})
            ledger.append_jsonl(lj, {"event": "close", "id": "o1"})
            with open(lj) as f:
                self.assertEqual(len(f.read().strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# --- paper-execute safety: paper fills go to cert, real money needs MODE=live (overlord 2026-07-22) ---
import unittest as _ut3, os as _os3
from config import Config as _Cfg3
class PaperExecuteSafetyTest(_ut3.TestCase):
    def _cfg(self, **env):
        old = dict(_os3.environ)
        try:
            for k in ("MODE","PAPER_EXECUTE"): _os3.environ.pop(k, None)
            _os3.environ.update({k: v for k, v in env.items()})
            return _Cfg3()
        finally:
            _os3.environ.clear(); _os3.environ.update(old)
    def test_paper_execute_uses_cert_never_prod(self):
        c = self._cfg(MODE="paper", PAPER_EXECUTE="1")
        self.assertTrue(c.paper_execute)
        self.assertIn("cert", c.api_base)                 # sandbox host
        self.assertNotIn("api.tastytrade.com", c.api_base)  # NEVER production
    def test_live_is_the_only_path_to_prod(self):
        c = self._cfg(MODE="live")
        self.assertEqual(c.api_base, "https://api.tastytrade.com")
    def test_default_is_dry_run_only(self):
        c = self._cfg(MODE="paper")
        self.assertFalse(c.paper_execute)                 # off unless explicitly set
        self.assertIn("cert", c.api_base)


# --- card duration line (overlord 2026-07-22) ---
import unittest as _ut4, telegram_gate as _tg4
class DurationTest(_ut4.TestCase):
    def test_expiration_parsed_from_occ(self):
        exp, dte = _tg4._occ_expiration("SPY   260821P00714000")
        self.assertEqual(exp, "Aug 21, 2026")     # date is stable; dte varies by run-day
        self.assertIsInstance(dte, int)
    def test_bad_symbol_returns_none(self):
        self.assertEqual(_tg4._occ_expiration("garbage"), (None, None))


# --- REAL-MONEY WALL: cert vs prod credential separation (overlord 2026-07-23) ---
import unittest as _ut5, os as _os5
from config import Config as _Cfg5
class RealMoneyWallTest(_ut5.TestCase):
    CERT = {"TT_CLIENT_SECRET":"cert_sec","TT_REFRESH_TOKEN":"cert_ref","TT_CLIENT_ID":"cert_id","TT_ACCOUNT":"CERT1",
            "TELEGRAM_BOT_TOKEN":"b","TELEGRAM_CHAT_ID":"c"}
    PROD = {"TT_PROD_CLIENT_SECRET":"prod_sec","TT_PROD_REFRESH_TOKEN":"prod_ref","TT_PROD_CLIENT_ID":"prod_id","TT_PROD_ACCOUNT":"PROD1"}
    def _cfg(self, **extra):
        old=dict(_os5.environ)
        try:
            for k in list(_os5.environ):
                if k.startswith(("TT_","MODE","PAPER_EXECUTE","MAX_CONTRACTS","LIVE_MAX","TELEGRAM_")): _os5.environ.pop(k,None)
            _os5.environ.update(self.CERT); _os5.environ.update(self.PROD); _os5.environ.update(extra)
            return _Cfg5()
        finally:
            _os5.environ.clear(); _os5.environ.update(old)
    def test_paper_uses_cert_never_prod(self):
        c=self._cfg(MODE="paper")
        self.assertEqual(c.tt_client_secret,"cert_sec")
        self.assertEqual(c.tt_refresh_token,"cert_ref")
        self.assertEqual(c.tt_account,"CERT1")
        self.assertIn("cert",c.api_base)
        self.assertNotIn("prod_sec",(c.tt_client_secret,c.tt_refresh_token))  # prod never surfaces in paper
    def test_live_uses_prod_never_cert(self):
        c=self._cfg(MODE="live")
        self.assertEqual(c.tt_client_secret,"prod_sec")
        self.assertEqual(c.tt_refresh_token,"prod_ref")
        self.assertEqual(c.tt_account,"PROD1")
        self.assertEqual(c.api_base,"https://api.tastytrade.com")
    def test_live_hard_caps_contracts_at_one(self):
        c=self._cfg(MODE="live",MAX_CONTRACTS="10")
        self.assertEqual(c.max_contracts,1)          # live ignores a big MAX_CONTRACTS
        p=self._cfg(MODE="paper",MAX_CONTRACTS="10")
        self.assertEqual(p.max_contracts,10)          # paper is unrestricted
    def test_live_refuses_when_prod_slot_empty(self):
        old=dict(_os5.environ)
        try:
            for k in list(_os5.environ):
                if k.startswith(("TT_","MODE","TELEGRAM_")): _os5.environ.pop(k,None)
            _os5.environ.update(self.CERT); _os5.environ["MODE"]="live"   # no prod creds
            probs=_Cfg5().validate()
            self.assertTrue(any("PROD" in p or "sandbox" in p for p in probs))
        finally:
            _os5.environ.clear(); _os5.environ.update(old)
    def test_live_refuses_prod_equals_cert(self):
        c=self._cfg(MODE="live",TT_PROD_CLIENT_SECRET="cert_sec",TT_PROD_REFRESH_TOKEN="cert_ref")
        self.assertTrue(any("identical" in p for p in c.validate()))


# --- multi-leg (iron condor) economics on the card (overlord 2026-07-23) ---
import unittest as _ut6, telegram_gate as _tg6
class MultiLegEconTest(_ut6.TestCase):
    def test_iron_condor_prices(self):
        sig={"symbol":"SPX","price":9.35,"price_effect":"Debit","legs":[
            {"symbol":"SPXW  260918C07700000","action":"Buy to Open","quantity":1},
            {"symbol":"SPXW  260918C07680000","action":"Sell to Open","quantity":1},
            {"symbol":"SPXW  260918P07000000","action":"Sell to Open","quantity":1},
            {"symbol":"SPXW  260918P06980000","action":"Buy to Open","quantity":1}]}
        inv,prof,roi=_tg6._spread_economics(sig,1)
        self.assertEqual(round(inv),935)              # debit paid = max loss
        self.assertEqual(round(prof),1065)            # 20-wide wing - 9.35 debit
    def test_two_leg_still_works(self):
        sig={"symbol":"SPY","price":0.60,"price_effect":"Credit","legs":[
            {"symbol":"SPY   260821P00714000","action":"Sell to Open","quantity":1},
            {"symbol":"SPY   260821P00711000","action":"Buy to Open","quantity":1}]}
        inv,prof,roi=_tg6._spread_economics(sig,1)
        self.assertEqual(round(inv),240); self.assertEqual(round(prof),60)


# --- profit-target exit manager (overlord 2026-07-23) ---
import unittest as _ut6, exit_manager as _em
class ExitManagerTest(_ut6.TestCase):
    def _pos(self, cashflow):  # credit spread: open_cashflow +260 = $2.60 credit x1
        return {"open_cashflow": cashflow, "symbol": "SPY", "trader": "Tom", "id": "x", "legs": ["a", "b"]}
    def _marks(self, short_mark, long_mark):
        return [{"mark": short_mark, "qty": 1, "dir": "Short", "multiplier": 100},
                {"mark": long_mark, "qty": 1, "dir": "Long", "multiplier": 100}]
    def test_credit_spread_50pct(self):
        # opened for $2.60 credit; buy back for $1.30 net -> captured 50%
        pct, pnl = _em.captured_pct(self._pos(260.0), self._marks(1.60, 0.30))  # cost_to_close = 130
        self.assertEqual(pct, 50.0); self.assertEqual(pnl, 130.0)
    def test_missing_mark_is_none(self):
        pct, pnl = _em.captured_pct(self._pos(260.0), self._marks(None, 0.30))
        self.assertIsNone(pct)
    def test_target_crossing_dedupes(self):
        self.assertEqual(_em.next_target_crossed(52.0, [20,30,50], []), 50)
        self.assertEqual(_em.next_target_crossed(52.0, [20,30,50], [50]), 30)  # highest not-yet-alerted
        self.assertIsNone(_em.next_target_crossed(52.0, [20,30,50], [20,30,50]))
    def test_parse_targets(self):
        self.assertEqual(_em.parse_targets("20,30,50"), [20,30,50])
        self.assertEqual(_em.parse_targets(""), [50])


# --- per-leg close buttons (overlord 2026-07-23) ---
import unittest as _ut7, telegram_gate as _tg7
class PerLegCloseTest(_ut7.TestCase):
    def test_leg_label(self):
        self.assertEqual(_tg7._leg_label({"symbol":"SPY   260821P00714000","dir":"Short"}), "714P S")
        self.assertEqual(_tg7._leg_label({"symbol":"QQQ   260918C00500000","dir":"Long"}), "500C L")
    def test_keyboard_has_all_hold_and_per_leg(self):
        legs=[{"symbol":"SPY   260821P00714000","dir":"Short"},{"symbol":"SPY   260821P00711000","dir":"Long"}]
        kb=_tg7._close_keyboard("pid", legs)["inline_keyboard"]
        self.assertEqual(kb[0][0]["callback_data"],"closeyes:pid")   # Close ALL
        self.assertEqual(kb[0][1]["callback_data"],"closeno:pid")    # Hold
        self.assertEqual(kb[1][0]["callback_data"],"closeleg:pid:0") # leg 1
        self.assertEqual(kb[2][0]["callback_data"],"closeleg:pid:1") # leg 2


# --- fill confirmation: unfilled orders never book P&L (overlord 2026-07-24) ---
import unittest as _ut8
import ledger as _lg8
class FillReconcileTest(_ut8.TestCase):
    class _Brk:
        def __init__(self, m): self.m = m
        def order_status(self, oid): return self.m.get(oid)
    def test_filled_becomes_open_unfilled_excluded(self):
        pos = {"a": {"status":"pending","order_id":"1","trader":"T","open_cashflow":100.0},
               "b": {"status":"pending","order_id":"2","trader":"T","open_cashflow":-474.0}}
        _lg8.reconcile_fills(pos, self._Brk({"1":"Filled","2":"Expired"}))
        self.assertEqual(pos["a"]["status"],"open")       # filled -> real position
        self.assertEqual(pos["b"]["status"],"unfilled")   # expired -> not a position
    def test_unfilled_cannot_close_or_book_pnl(self):
        # an unfilled position must NOT match a trader close (no phantom P&L)
        pos={"b":{"status":"unfilled","trader":"T434925","legs":["MU260724P00750000"],"open_cashflow":-474.0}}
        closed=_lg8.match_and_close(pos, {"trader":"T434925","legs":[{"symbol":"MU260724P00750000"}],
                                          "price":24.1,"price_effect":"Credit"}, "now")
        self.assertIsNone(closed)                          # unfilled -> never books the +1936 phantom

# Deploy tt-mimic to the Oracle VM

Runbook for standing up the tastytrade follow-feed mimic trader under the
existing `pm2` + watchdog + KILL_SWITCH stack at `/home/opc/auto-trader`
(owned by the `coinbase-trader` agent). Deploys **disarmed / paper** — see the
hard rails in [`README.md`](./README.md) before you ever go live.

Prereq: complete the one-time "Setup (Danny)" steps in the README first
(unlock tastytrade, create the OAuth app + refresh token + sandbox account,
create the Telegram bot, get your chat id).

## 1. Pull the module onto the VM

```bash
ssh opc@YOUR_VM_IP
cd /home/opc/auto-trader

# Clone the branch carrying this module and copy only the module folder.
# After this branch merges to main, use --branch main instead.
git clone --depth 1 --branch claude/tastytrade-mimic-setup-jwcmaa \
  https://github.com/dannybivins83-blip/collaborativeconcepts.git tt-src
cp -r tt-src/trading/tastytrade-mimic ./tastytrade-mimic && rm -rf tt-src
cd tastytrade-mimic

python3 _tests.py        # expect: Ran 24 tests ... OK
```

No `pip install` needed — the module is standard-library only.

## 2. Fill in secrets (env.sh)

`env.sh` holds real secrets, is gitignored, and never gets committed. Copy the
template, fill it in with a text editor, then lock it down:

```bash
cp env.sh.example env.sh
nano env.sh              # replace every PASTE_HERE, keep MODE=paper
chmod 600 env.sh
```

> A secret pasted into a chat, commit, bus message, or screenshot is **burned** —
> regenerate it before use. Only ever confirm a secret by NAME, never its value.

## 3. Start under pm2

`start.sh` sources the colocated `env.sh` and execs `main.py` from its own
directory (disarmed by default — no `--execute`).

```bash
pm2 start ./start.sh --name tt-mimic
pm2 save
pm2 logs tt-mimic --lines 5   # should print: mode=paper armed=False source=follow-feed
```

Seeing `armed=False` in the log confirms the safety posture: the loop polls the
public follow feed and asks for a Telegram approval per trade, but every order
runs as an API dry-run only until you deliberately arm it.

## 4. Operating

- **Halt everything:** `touch /home/opc/auto-trader/tastytrade-mimic/KILL_SWITCH`
  (the watcher idles; remove the file to resume).
- **Restart / logs:** `pm2 restart tt-mimic` · `pm2 logs tt-mimic`.
- **Going live (only after watching a full paper cycle):** set `MODE=live` in
  `env.sh` and launch with the `--execute` flag —
  `pm2 start ./start.sh --name tt-mimic -- --execute`. Even then, **every trade
  still requires your per-trade Telegram tap**; an unanswered request expires to
  SKIP.

## TARGET ENVIRONMENT — verified on the VM 2026-07-21 (do not regress)
- The Oracle VM runs **Python 3.9.25**. There is no newer interpreter installed.
- **Do NOT use PEP-604 unions** (`dict | None`). They are a syntax error on 3.9 and WILL fail the
  deploy even though the test suite passes on a modern Python. Use `Optional[dict]` from `typing`.
  This bit us once: 5 occurrences across broker.py/signals.py had to be converted on the VM.
- `pip3` is NOT on PATH. Use `python3 -m pip`.
- Verified after the fix: `python3 _tests.py` → **Ran 24 tests, OK, exit 0** on the VM itself.
- Default posture re-verified: `main.py` computes `armed = cfg.mode == "live" and execute_flag`,
  and MODE defaults to `paper`. Arming requires BOTH. Unchanged by the compatibility fix.
- `env.sh` lives beside the module, mode 600, gitignored. TT_CLIENT_ID / TT_CLIENT_SECRET /
  TT_REFRESH_TOKEN are already populated from the main .env. Only TELEGRAM_CHAT_ID remains blank.

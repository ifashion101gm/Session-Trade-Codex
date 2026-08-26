"""Candle-driven runner for SESSION_SIMPLE_V1 (config strategy_id ASIAN_SESSION_V1).

Owns TIME / SCHEDULING / NEW-BAR DETECTION / PROCESS LIFECYCLE / HEARTBEAT only.
Strategy decisions (trend/range, sweep, bias, entry, SL, TP, risk, quota, order
construction, order_check/order_send semantics) remain entirely inside
``scripts/execute_session_signal.py`` and the engine it calls -- this runner
invokes that script as a subprocess once per newly closed M15 bar inside the
execution window and does nothing else with the result besides logging it.

Default mode is CHECK-ONLY: the underlying script is invoked WITHOUT
``--confirm``, so it always dry-runs (analyze + optionally a real broker-side
order_check, never order_send). ``execute_session_signal.py``'s own
authorization chain (``--confirm`` AND ``ALLOW_ORDER_SUBMISSION=true`` AND
``ALLOW_ONE_DEMO_ORDER=true``) is designed for an explicit, one-off, manual
CLI invocation. Converting that into unattended automatic sending is a
deliberate, separate decision -- this runner never makes it silently. Pass
``--enable-auto-send`` (and the same two env vars) to opt in explicitly.

Usage
-----
    python scripts/session_simple_runner.py --symbol EURUSD                 # Phase A, check-only
    python scripts/session_simple_runner.py --symbol EURUSD --once          # single cycle, then exit
    ALLOW_ORDER_SUBMISSION=true ALLOW_ONE_DEMO_ORDER=true \\
        python scripts/session_simple_runner.py --symbol EURUSD --enable-auto-send   # Phase B
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.config import load_config  # noqa: E402
from session_strategy.engine import execution_bounds  # noqa: E402

STATE_PATH = ROOT / "data" / "session_simple_runner_state.json"
LOCK_PATH = ROOT / "data" / "session_simple_runner.lock"
EXECUTE_SCRIPT = ROOT / "scripts" / "execute_session_signal.py"
HEARTBEAT_SECONDS = 30
POLL_SECONDS = 5


def floor_m15(now: datetime, step_seconds: int) -> datetime:
    """Start of the currently forming M15 bar == close time of the most
    recently fully closed bar. Pure UTC arithmetic -- fixed-boundary M15
    bars need no broker round-trip to detect a rollover."""
    epoch = now.timestamp()
    floored = epoch - (epoch % step_seconds)
    return datetime.fromtimestamp(floored, tz=timezone.utc)


def acquire_lock():
    """Single-instance lock. On Windows, an OS-held file lock (msvcrt) is
    released automatically on process exit/crash -- no stale-PID bookkeeping
    needed. Returns an open file handle that must be kept alive for the
    runner's lifetime, or None if another instance already holds it."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK_PATH, "r+b" if LOCK_PATH.exists() else "w+b")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.seek(0)
        fh.write(f"pid={os.getpid()} started_utc={datetime.now(timezone.utc).isoformat()}\n".encode())
        fh.flush()
    except OSError:
        fh.close()
        return None
    return fh


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    tmp.replace(STATE_PATH)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def run_check(symbol: str, config, enable_auto_send: bool) -> tuple[int, dict | None]:
    """Invoke the authoritative script as a subprocess. Runner never imports
    or reimplements strategy logic -- it only owns when to call this."""
    cmd = [sys.executable, str(EXECUTE_SCRIPT), "--symbol", symbol, "--check"]
    env = os.environ.copy()
    if enable_auto_send:
        cmd.append("--confirm")
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120)
    output_tail = "\n".join((proc.stdout or "").splitlines()[-1:])
    payload = None
    try:
        payload = json.loads(output_tail) if output_tail.strip().startswith("{") else None
    except ValueError:
        payload = None
    if proc.returncode not in (0, 1, 2, 3):
        log(f"UNEXPECTED_EXIT_CODE={proc.returncode} stderr_tail={proc.stderr[-500:]!r}")
    return proc.returncode, payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    ap.add_argument("--once", action="store_true", help="Run a single evaluation cycle then exit (for tests/CI).")
    ap.add_argument("--enable-auto-send", action="store_true",
                     help="Phase B: pass --confirm through to execute_session_signal.py. "
                          "Still requires ALLOW_ORDER_SUBMISSION=true and ALLOW_ONE_DEMO_ORDER=true "
                          "at the underlying script -- this flag alone does not bypass those.")
    args = ap.parse_args()

    config = load_config(args.config)
    if config.trading_mode != "demo":
        log(f"REFUSING: trading_mode={config.trading_mode!r} is not demo")
        return 1

    lock = acquire_lock()
    if lock is None:
        log("SINGLE_RUNNER_LOCK: another instance already holds the lock; exiting")
        return 1
    log(f"SessionSimpleV1 runner starting. symbol={args.symbol} auto_send={args.enable_auto_send}")

    state = load_state()
    key = args.symbol
    entry = state.get(key, {})
    last_processed = entry.get("last_processed_m15_close_utc")
    last_heartbeat = 0.0

    try:
        while True:
            now = datetime.now(timezone.utc)
            trading_date = now.date()
            exec_start, exec_end = execution_bounds(trading_date, config)
            window_open = exec_start <= now < exec_end
            current_bar_close = floor_m15(now, config.timeframe_seconds).isoformat()

            if time.time() - last_heartbeat >= HEARTBEAT_SECONDS:
                log(
                    "HEARTBEAT state=WAITING account=DEMO symbol=%s utc=%s window=%s "
                    "last_processed_m15=%s auto_send=%s live=BLOCKED"
                    % (args.symbol, now.strftime("%H:%M:%S"),
                       "OPEN" if window_open else "CLOSED",
                       last_processed or "NONE",
                       "ENABLED" if args.enable_auto_send else "DISABLED")
                )
                last_heartbeat = time.time()

            if window_open and current_bar_close != last_processed:
                log(f"NEW_CLOSED_M15 close_utc={current_bar_close} -- evaluating {args.symbol}")
                try:
                    rc, payload = run_check(args.symbol, config, args.enable_auto_send)
                    action = (payload or {}).get("execution", f"EXIT_CODE_{rc}")
                    log(f"BAR_PROCESSED=YES STRATEGY_EVALUATED=YES action={action}")
                except subprocess.TimeoutExpired:
                    log("CRITICAL: execute_session_signal.py timed out; not marking bar processed")
                    time.sleep(POLL_SECONDS)
                    continue
                except Exception as exc:  # noqa: BLE001 -- fail closed, keep runner alive in check-only state
                    log(f"CRITICAL_EXCEPTION during evaluation: {exc!r}")
                    time.sleep(POLL_SECONDS)
                    continue

                last_processed = current_bar_close
                state[key] = {
                    "strategy_id": config.strategy_id,
                    "symbol": args.symbol,
                    "trading_date": trading_date.isoformat(),
                    "last_processed_m15_close_utc": last_processed,
                    "last_successful_check_utc": now.isoformat(),
                    "last_execution_id": (payload or {}).get("signal_id"),
                    "runner_instance_id": os.getpid(),
                    "updated_at": now.isoformat(),
                }
                save_state(state)

            if args.once:
                return 0
            time.sleep(POLL_SECONDS)
    finally:
        lock.close()
        log("SessionSimpleV1 runner stopped.")


if __name__ == "__main__":
    raise SystemExit(main())

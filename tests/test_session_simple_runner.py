import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import session_simple_runner as runner  # noqa: E402


def test_floor_m15_rounds_down_to_bar_boundary():
    now = datetime(2026, 8, 26, 10, 7, 30, tzinfo=timezone.utc)
    assert runner.floor_m15(now, 900) == datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)


def test_floor_m15_exact_boundary_is_stable():
    now = datetime(2026, 8, 26, 10, 15, 0, tzinfo=timezone.utc)
    assert runner.floor_m15(now, 900) == datetime(2026, 8, 26, 10, 15, 0, tzinfo=timezone.utc)


def test_state_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "state.json")
    runner.save_state({"EURUSD": {"last_processed_m15_close_utc": "x"}})
    assert runner.load_state() == {"EURUSD": {"last_processed_m15_close_utc": "x"}}


def test_load_state_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "missing.json")
    assert runner.load_state() == {}


def test_load_state_corrupt_file_fails_closed_to_empty(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(runner, "STATE_PATH", path)
    assert runner.load_state() == {}


def test_single_instance_lock_blocks_second_holder(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    first = runner.acquire_lock()
    try:
        assert first is not None
        second = runner.acquire_lock()
        assert second is None
    finally:
        first.close()


def test_lock_released_after_close_allows_new_holder(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    first = runner.acquire_lock()
    first.close()
    second = runner.acquire_lock()
    assert second is not None
    second.close()


class _FakeConfig:
    trading_mode = "demo"
    timeframe_seconds = 900
    strategy_id = "ASIAN_SESSION_V1"
    session_start_utc = "00:00:00"
    session_end_utc = "07:00:00"
    execution_start_utc = "07:00:00"
    execution_end_utc = "16:00:00"


def test_pre_window_does_not_invoke_check(monkeypatch, tmp_path, capsys):
    """Requirement: before 07:00 UTC, runner stays alive but attempts no evaluation."""
    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    monkeypatch.setattr(runner, "load_config", lambda path: _FakeConfig())

    called = {"n": 0}

    def fake_run_check(*a, **k):
        called["n"] += 1
        return 0, {"execution": "DRY_RUN"}

    monkeypatch.setattr(runner, "run_check", fake_run_check)
    monkeypatch.setattr(sys, "argv", ["session_simple_runner.py", "--symbol", "EURUSD", "--once"])

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 26, 6, 30, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(runner, "datetime", _FixedDatetime)
    rc = runner.main()
    assert rc == 0
    assert called["n"] == 0


def test_in_window_new_bar_invokes_check_once_and_persists_state(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(runner, "STATE_PATH", state_path)
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    monkeypatch.setattr(runner, "load_config", lambda path: _FakeConfig())

    called = {"n": 0}

    def fake_run_check(*a, **k):
        called["n"] += 1
        return 0, {"execution": "DRY_RUN", "signal_id": "abc123"}

    monkeypatch.setattr(runner, "run_check", fake_run_check)
    monkeypatch.setattr(sys, "argv", ["session_simple_runner.py", "--symbol", "EURUSD", "--once"])

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 26, 10, 7, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(runner, "datetime", _FixedDatetime)
    rc = runner.main()
    assert rc == 0
    assert called["n"] == 1

    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["EURUSD"]["last_processed_m15_close_utc"] == "2026-08-26T10:00:00+00:00"
    assert saved["EURUSD"]["last_execution_id"] == "abc123"


def test_same_bar_seen_twice_not_reprocessed(monkeypatch, tmp_path):
    """Simulates a restart: durable state already has this bar recorded, so a
    fresh --once cycle at the same timestamp must not call run_check again."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "EURUSD": {"last_processed_m15_close_utc": "2026-08-26T10:00:00+00:00"}
    }), encoding="utf-8")
    monkeypatch.setattr(runner, "STATE_PATH", state_path)
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    monkeypatch.setattr(runner, "load_config", lambda path: _FakeConfig())

    called = {"n": 0}
    monkeypatch.setattr(runner, "run_check", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or (0, {}))
    monkeypatch.setattr(sys, "argv", ["session_simple_runner.py", "--symbol", "EURUSD", "--once"])

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 26, 10, 7, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(runner, "datetime", _FixedDatetime)
    rc = runner.main()
    assert rc == 0
    assert called["n"] == 0


def test_post_window_no_new_entry_evaluation(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")
    monkeypatch.setattr(runner, "load_config", lambda path: _FakeConfig())

    called = {"n": 0}
    monkeypatch.setattr(runner, "run_check", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or (0, {}))
    monkeypatch.setattr(sys, "argv", ["session_simple_runner.py", "--symbol", "EURUSD", "--once"])

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 26, 16, 5, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(runner, "datetime", _FixedDatetime)
    rc = runner.main()
    assert rc == 0
    assert called["n"] == 0


def test_non_demo_trading_mode_refuses(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "runner.lock")

    class _RealConfig(_FakeConfig):
        trading_mode = "real"

    monkeypatch.setattr(runner, "load_config", lambda path: _RealConfig())
    monkeypatch.setattr(sys, "argv", ["session_simple_runner.py", "--symbol", "EURUSD", "--once"])
    rc = runner.main()
    assert rc == 1

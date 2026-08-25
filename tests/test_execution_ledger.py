"""Unit tests for the local durable execution ledger (Phase B, 2026-08-25).

Covers the crash-safety property the ledger exists for: a signal_id that
reached SEND_REQUESTED or later is committed and must block a re-send, even
before order_send's response is known.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.execution.ledger import ExecutionLedger  # noqa: E402


def _ledger(tmp_path) -> ExecutionLedger:
    return ExecutionLedger(tmp_path / "test_execution_ledger.sqlite3")


def test_unknown_signal_is_not_committed(tmp_path):
    ledger = _ledger(tmp_path)
    committed, reason = ledger.is_committed("nope")
    assert committed is False
    assert reason == ""


def test_prepared_alone_is_not_committed(tmp_path):
    """PREPARED means we started working on it, not that we asked the broker
    to send it -- a dry-run or a crash before order_send leaves a PREPARED
    row that must NOT block a real attempt."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sig1", "attempt1", "EURUSD", "LONG", {"symbol": "EURUSD"})
    committed, _ = ledger.is_committed("sig1")
    assert committed is False


def test_send_requested_blocks_before_any_response_is_known(tmp_path):
    """This is the crash-safety property the ledger exists for: the write
    happens BEFORE order_send() is called, so even if the process dies right
    after that write and before the broker responds, is_committed() is
    already True on restart."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sig2", "attempt1", "EURUSD", "SHORT", {"symbol": "EURUSD"})
    ledger.mark_send_requested("sig2")
    committed, reason = ledger.is_committed("sig2")
    assert committed is True
    assert "SEND_REQUESTED" in reason


def test_send_response_done_marks_send_accepted(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig3", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sig3")
    ledger.mark_send_response("sig3", retcode=10009, comment="Done", order_ticket=555)
    row = ledger.get("sig3")
    assert row["status"] == "SEND_ACCEPTED"
    assert row["order_ticket"] == 555


def test_send_response_non_done_marks_send_rejected(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig4", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sig4")
    ledger.mark_send_response("sig4", retcode=10013, comment="Invalid request", order_ticket=None)
    row = ledger.get("sig4")
    assert row["status"] == "SEND_REJECTED"
    # A rejected send must NOT be treated as committed -- it never reached the
    # broker successfully, so a corrected retry should be allowed.
    committed, _ = ledger.is_committed("sig4")
    assert committed is False


def test_position_confirmed_is_committed(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig5", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sig5")
    ledger.mark_send_response("sig5", retcode=10009, comment="Done", order_ticket=1)
    ledger.mark_position_confirmed("sig5", deal_ticket=2, position_ticket=3,
                                   filled_volume=0.01, fill_price=1.1)
    row = ledger.get("sig5")
    assert row["status"] == "POSITION_CONFIRMED"
    assert row["position_ticket"] == 3
    committed, _ = ledger.is_committed("sig5")
    assert committed is True


def test_reconciliation_failed_is_recorded_with_note(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig6", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sig6")
    ledger.mark_reconciliation_failed("sig6", "no matching position found")
    row = ledger.get("sig6")
    assert row["status"] == "RECONCILIATION_FAILED"
    assert "no matching position" in row["note"]


MAGIC = 123456
OTHER_MAGIC = 999999


def test_has_committed_execution_today_false_when_nothing_sent(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig8", "attempt1", "EURUSD", "LONG", {"magic": MAGIC})  # PREPARED only, never sent
    assert ledger.has_committed_execution_today("EURUSD", "2026-08-25", MAGIC) is False


def test_has_committed_execution_today_true_once_send_requested(tmp_path):
    """The regression this exists to prevent: a dry run/--check call must NOT
    burn the quota, but an actual send attempt must."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sig9", "attempt1", "EURUSD", "SHORT", {"magic": MAGIC})
    ledger.mark_send_requested("sig9")
    assert ledger.has_committed_execution_today("EURUSD", "2026-08-25", MAGIC) is True


def test_has_committed_execution_today_ignores_other_symbols_and_dates(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig10", "attempt1", "GBPUSD", "LONG", {"magic": MAGIC})
    ledger.mark_send_requested("sig10")
    assert ledger.has_committed_execution_today("EURUSD", "2026-08-25", MAGIC) is False
    # Same symbol, but querying a different date should also be False, since
    # created_utc is matched by a date-prefix LIKE against the row's real
    # timestamp -- confirms the query is actually date-scoped, not global.
    assert ledger.has_committed_execution_today("GBPUSD", "1999-01-01", MAGIC) is False


def test_has_committed_execution_today_ignores_other_magic_numbers(tmp_path):
    """Regression test for the real bug found live 2026-08-25: a TEST_EXECUTION
    harness commit (magic 999999) on EURUSD must NOT be counted as a real
    ASIAN_SESSION_V1 (magic 123456) commit on the same symbol/date -- they
    are unrelated strategies sharing a broker symbol."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sig11", "attempt1", "EURUSD", "LONG", {"magic": OTHER_MAGIC})
    ledger.mark_send_requested("sig11")
    assert ledger.has_committed_execution_today("EURUSD", "2026-08-25", MAGIC) is False
    assert ledger.has_committed_execution_today("EURUSD", "2026-08-25", OTHER_MAGIC) is True


def test_signal_id_is_the_primary_key_reprepare_does_not_duplicate(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sig7", "attempt1", "EURUSD", "LONG", {"a": 1})
    ledger.prepare("sig7", "attempt2", "EURUSD", "LONG", {"a": 2})
    row = ledger.get("sig7")
    assert row["attempt_id"] == "attempt2"
    count = ledger.db.execute(
        "SELECT COUNT(*) as n FROM executions WHERE signal_id=?", ("sig7",)
    ).fetchone()["n"]
    assert count == 1

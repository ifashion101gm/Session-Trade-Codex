"""Unit tests for broker_has_prior_execution / execution_already_committed /
reconcile_position (Phase B/C, 2026-08-25). All against a mocked gateway --
no live MT5 needed, and this specifically covers the "retcode looks like
success but the position isn't actually there" case the plan called out.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.execution.ledger import ExecutionLedger  # noqa: E402
from session_strategy.execution.reconciliation import (  # noqa: E402
    broker_has_prior_execution, execution_already_committed, reconcile_position,
)

MAGIC = 123456


def _ledger(tmp_path) -> ExecutionLedger:
    return ExecutionLedger(tmp_path / "test_reconciliation_ledger.sqlite3")


def _gateway(positions=None, deals=None, orders=None):
    gw = MagicMock()
    gw.positions.return_value = positions or []
    gw.deals.return_value = deals or []
    gw.orders.return_value = orders or []
    return gw


# --------------------------------------------------------------- broker_has_prior_execution

def test_broker_has_prior_execution_false_when_clean():
    gw = _gateway()
    found, _ = broker_has_prior_execution(gw, "EURUSD", MAGIC)
    assert found is False


def test_broker_has_prior_execution_true_for_open_position():
    gw = _gateway(positions=[{"symbol": "EURUSD", "magic": MAGIC, "ticket": 1}])
    found, reason = broker_has_prior_execution(gw, "EURUSD", MAGIC)
    assert found is True and "1" in reason


def test_broker_has_prior_execution_true_for_todays_deal():
    gw = _gateway(deals=[{"symbol": "EURUSD", "magic": MAGIC, "ticket": 9}])
    found, reason = broker_has_prior_execution(gw, "EURUSD", MAGIC)
    assert found is True and "9" in reason


# --------------------------------------------------------------- execution_already_committed

def test_already_committed_true_from_local_ledger_even_with_clean_broker(tmp_path):
    """This is the whole point of the local ledger: broker state can lag or
    be briefly unavailable, but the local write happened synchronously
    before order_send -- it must win even when the broker looks clean."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sigA", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigA")
    gw = _gateway()  # broker shows nothing yet
    committed, reason = execution_already_committed(ledger, gw, "sigA", "EURUSD", MAGIC)
    assert committed is True
    assert "SEND_REQUESTED" in reason


def test_already_committed_true_from_broker_even_with_no_local_record(tmp_path):
    """The reverse case: e.g. a fresh checkout with no local ledger at all,
    but the broker already shows a position -- must still block."""
    ledger = _ledger(tmp_path)
    gw = _gateway(positions=[{"symbol": "EURUSD", "magic": MAGIC, "ticket": 2}])
    committed, reason = execution_already_committed(ledger, gw, "sigB", "EURUSD", MAGIC)
    assert committed is True
    assert "2" in reason


def test_not_committed_when_both_clean(tmp_path):
    ledger = _ledger(tmp_path)
    gw = _gateway()
    committed, _ = execution_already_committed(ledger, gw, "sigC", "EURUSD", MAGIC)
    assert committed is False


# --------------------------------------------------------------- reconcile_position

def test_reconcile_position_rejected_send_does_not_query_positions(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sigD", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigD")
    gw = _gateway()
    send_result = {"retcode": 10013, "comment": "Invalid request", "order": None}

    outcome = reconcile_position(gw, ledger, "sigD", send_result)

    assert outcome["stage"] == "ORDER_SEND_RESPONSE_RECEIVED"
    assert outcome["outcome"] == "SEND_REJECTED"
    gw.positions.assert_not_called()


def test_reconcile_position_confirmed_when_matching_position_found(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.prepare("sigE", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigE")
    gw = _gateway(positions=[{"ticket": 777, "symbol": "EURUSD", "volume": 0.01, "price_open": 1.1}])
    send_result = {"retcode": 10009, "comment": "Done", "order": 777, "deal": 888, "price": 1.1}

    outcome = reconcile_position(gw, ledger, "sigE", send_result)

    assert outcome["stage"] == "BROKER_POSITION_CONFIRMED"
    assert outcome["outcome"] == "CONFIRMED"
    row = ledger.get("sigE")
    assert row["status"] == "POSITION_CONFIRMED"
    assert row["position_ticket"] == 777


def test_reconcile_position_fails_when_retcode_done_but_no_position_or_deal_found(tmp_path):
    """The exact case the plan called out: a DONE-looking retcode is NOT
    enough on its own -- if the position genuinely can't be found on
    re-query, this must be a hard failure, not a silent success."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sigF", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigF")
    gw = _gateway(positions=[], deals=[])  # broker shows NOTHING despite "DONE"
    send_result = {"retcode": 10009, "comment": "Done", "order": 999, "deal": 1000, "price": 1.1}

    outcome = reconcile_position(gw, ledger, "sigF", send_result)

    assert outcome["stage"] == "BROKER_STATE_QUERIED"
    assert outcome["outcome"] == "BROKER_RECONCILIATION_FAILED"
    row = ledger.get("sigF")
    assert row["status"] == "RECONCILIATION_FAILED"


def test_reconcile_position_confirms_pending_limit_order_not_yet_filled(tmp_path):
    """Regression test for the real bug found live 2026-08-25: a LIMIT order
    (the entry_type both the real strategy and the test harness use) does not
    create a position or deal until it fills -- it creates a PENDING order.
    Before this fix, reconcile_position() mis-reported this as
    BROKER_RECONCILIATION_FAILED despite the order genuinely existing."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sigH", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigH")
    gw = _gateway(
        positions=[], deals=[],
        orders=[{"ticket": 555, "symbol": "EURUSD", "price_open": 1.16195, "sl": 1.15995, "tp": 1.16495}],
    )
    send_result = {"retcode": 10009, "comment": "Done", "order": 555, "deal": 0, "price": 1.16195}

    outcome = reconcile_position(gw, ledger, "sigH", send_result)

    assert outcome["stage"] == "BROKER_STATE_QUERIED"
    assert outcome["outcome"] == "PENDING_ORDER_CONFIRMED"
    row = ledger.get("sigH")
    assert row["status"] == "PENDING_ORDER_CONFIRMED"
    assert row["order_ticket"] == 555
    assert row["sl"] == 1.15995
    assert row["tp"] == 1.16495
    # A pending order is a committed, successful terminal state -- must count
    # toward duplicate protection just like POSITION_CONFIRMED does.
    committed, _ = ledger.is_committed("sigH")
    assert committed is True


def test_reconcile_position_falls_back_to_deal_history_if_position_already_closed(tmp_path):
    """A tiny test order can hit its own stop/target almost immediately --
    the position may already be closed by the time we re-query. Deal history
    showing the matching deal is still a valid confirmation."""
    ledger = _ledger(tmp_path)
    ledger.prepare("sigG", "attempt1", "EURUSD", "LONG", {})
    ledger.mark_send_requested("sigG")
    gw = _gateway(positions=[], deals=[{"ticket": 1000, "symbol": "EURUSD", "volume": 0.01, "price": 1.1}])
    send_result = {"retcode": 10009, "comment": "Done", "order": 999, "deal": 1000, "price": 1.1}

    outcome = reconcile_position(gw, ledger, "sigG", send_result)

    assert outcome["stage"] == "BROKER_POSITION_CONFIRMED"
    assert outcome["outcome"] == "CONFIRMED_VIA_DEAL_HISTORY"

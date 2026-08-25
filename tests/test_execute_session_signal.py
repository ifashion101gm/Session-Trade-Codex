"""Steps 1-7 of the execution-hardening sequence (2026-08-25):

1. Test an artificially accepted StrategyResult
2. Verify exact TradeIntent mapping
3. Verify deterministic signal_id
4. Duplicate-send protection -- now covered by tests/test_reconciliation.py
   (broker_has_prior_execution/execution_already_committed), which this file
   used to duplicate under the old already_sent() name before the rename.
5-7. Verify the --check (order_check dry-run) path builds the right request
     and surfaces the broker's retcode/comment, via a mocked gateway (no live
     MT5 connection -- the execution window was closed by the time this was
     written, so this is the only way to exercise 5-7 today; see STATUS.md).

No MT5 connection required -- pure unit tests against a synthetic, in-memory
AnalysisResult and (for steps 5-7) a MagicMock gateway, exercising the same
build_intent()/signal_id()/dry_broker_check() functions the live script uses.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from session_strategy.config import load_config  # noqa: E402
from session_strategy.mt5_gateway import MT5ExecutionGateway  # noqa: E402
from session_strategy.models import AccountSnapshot, AnalysisResult, Gate  # noqa: E402
from execute_session_signal import (  # noqa: E402
    build_intent, signal_id, dry_broker_check, ASIAN_SESSION_V1_MAGIC,
)


def _accepted_result(**overrides) -> AnalysisResult:
    account = AccountSnapshot(
        login_masked="*****746", account_type="demo", balance=1000.0, equity=1000.0,
        server="VantageMarkets-Demo", trade_allowed=True, expert_allowed=True, ping_ms=250.0,
    )
    base = dict(
        analysis_id="test0000",
        timestamp_utc=datetime(2026, 8, 25, 14, 31, tzinfo=timezone.utc),
        trading_date="2026-08-25",
        symbol="EURUSD",
        account=account,
        bid=1.16700, ask=1.16714, spread=0.00014,
        asian_start=datetime(2026, 8, 25, 0, 0, tzinfo=timezone.utc),
        asian_end=datetime(2026, 8, 25, 7, 0, tzinfo=timezone.utc),
        asian_high=1.16704, asian_low=1.16506, asian_range=0.00198,
        session_type="BEARISH_TREND",
        setup="TREND_CONTINUATION",
        direction="SHORT",
        signal_time=datetime(2026, 8, 25, 7, 15, tzinfo=timezone.utc),
        signal_candle={"open": 1.16650, "high": 1.16660, "low": 1.16600, "close": 1.16605},
        entry=1.16605,
        stop_loss=1.16654,
        tp1_4r=1.16409,
        tp2_5r=1.16360,
        risk_fraction=0.005,
        reason_codes=["TREND_SESSION", "MIDPOINT_RETRACEMENT"],
        gates=[Gate("G1_ENVIRONMENT", True, "ok"), Gate("G16_EXECUTION_WINDOW", True, "ok")],
    )
    base.update(overrides)
    return AnalysisResult(**base)


def test_accepted_result_is_accepted():
    result = _accepted_result()
    assert result.accepted is True
    assert result.status == "SIGNAL_ACCEPTED"


def test_unaccepted_result_is_not_accepted():
    result = _accepted_result(entry=None)
    assert result.accepted is False
    result2 = _accepted_result(gates=[Gate("G10_SETUP_DETECTED", False, "no setup")])
    assert result2.accepted is False


def test_build_intent_maps_every_field_exactly():
    result = _accepted_result()
    intent = build_intent(result)

    assert intent.strategy_id == "ASIAN_SESSION_V1"
    assert intent.strategy_version == "1.0"
    assert intent.symbol == "EURUSD"
    assert intent.reference_session == "ASIAN"
    assert intent.reference_start == result.asian_start
    assert intent.reference_end == result.asian_end
    assert intent.reference_high == 1.16704
    assert intent.reference_low == 1.16506
    assert intent.reference_range == 0.00198
    assert intent.regime == "TREND"
    assert intent.setup == "TREND_CONTINUATION"
    assert intent.direction == "SHORT"
    assert intent.signal_time == result.signal_time
    assert intent.signal_price == 1.16605  # from signal_candle["close"]
    assert intent.entry_type == "LIMIT"
    assert intent.entry_price == 1.16605
    assert intent.stop_price == 1.16654
    assert intent.target_price == 1.16360  # tp2_5r, the 5R ceiling, NOT tp1_4r
    assert intent.risk_fraction == 0.005
    assert intent.reason_code == "TREND_SESSION,MIDPOINT_RETRACEMENT"
    assert intent.entry_contract_signed is True


def test_build_intent_range_regime():
    result = _accepted_result(session_type="RANGE", setup="SWEEP", direction="LONG")
    intent = build_intent(result)
    assert intent.regime == "RANGE"


def test_build_intent_falls_back_to_entry_when_no_signal_candle():
    result = _accepted_result(signal_candle=None)
    intent = build_intent(result)
    assert intent.signal_price == result.entry


def test_signal_id_is_deterministic():
    result = _accepted_result()
    a = signal_id(result)
    b = signal_id(_accepted_result())  # identical inputs, freshly built
    assert a == b
    assert isinstance(a, str) and len(a) > 0


def test_signal_id_changes_with_session_identity():
    base = signal_id(_accepted_result())
    different_symbol = signal_id(_accepted_result(symbol="GBPUSD"))
    different_date = signal_id(_accepted_result(trading_date="2026-08-26"))
    different_setup = signal_id(_accepted_result(setup="SWEEP"))
    different_direction = signal_id(_accepted_result(direction="LONG"))
    assert len({base, different_symbol, different_date, different_setup, different_direction}) == 5


def test_signal_id_stable_across_unrelated_field_changes():
    """Fields that don't identify *which* signal this is (bid/ask, spread, analysis_id
    itself) must not change the id -- otherwise every re-run of analyze on the same
    session would look like a new signal and duplicate-send protection would be
    useless."""
    a = signal_id(_accepted_result())
    b = signal_id(_accepted_result(analysis_id="different-random-uuid", bid=1.9, ask=2.0))
    assert a == b


# ---------------------------------------------------------------------------
# Steps 5-7 -- dry_broker_check() against a mocked gateway
# ---------------------------------------------------------------------------

def _mock_gateway(positions=None, deals=None) -> MT5ExecutionGateway:
    gw = MagicMock(spec=MT5ExecutionGateway)
    gw.positions.return_value = positions or []
    gw.deals.return_value = deals or []
    gw.account.return_value = MagicMock(equity=1000.0)
    gw.loss_for_one_lot.return_value = 10.0
    gw.symbol_spec.return_value = MagicMock(volume_min=0.01, volume_max=100.0, volume_step=0.01)
    gw.order_check.return_value = {"retcode": 0, "comment": "Done"}
    return gw


def test_dry_broker_check_calls_real_order_check_and_surfaces_retcode():
    gw = _mock_gateway()
    config = load_config(str(ROOT / "config" / "strategy.yaml"))
    intent = build_intent(_accepted_result())

    outcome = dry_broker_check(config, gw, intent)

    assert outcome["stage"] == "ORDER_CHECK"
    assert outcome["retcode"] == 0
    assert outcome["comment"] == "Done"
    assert outcome["request"]["symbol"] == "EURUSD"
    gw.order_check.assert_called_once()


def test_dry_broker_check_request_uses_correct_type_key_and_direction():
    """Regression test for the RequestBuilder bug found and fixed 2026-08-25:
    the request must use MT5's real "type" key (not "order_type"), and must
    reflect intent.direction -- previously every order silently built as a
    market BUY regardless of direction or entry_type."""
    gw = _mock_gateway()
    config = load_config(str(ROOT / "config" / "strategy.yaml"))
    short_intent = build_intent(_accepted_result(direction="SHORT"))  # LIMIT entry_type from build_intent

    outcome = dry_broker_check(config, gw, short_intent)

    request = outcome["request"]
    assert "order_type" not in request
    assert "type" in request
    import MetaTrader5 as mt5
    assert request["type"] == mt5.ORDER_TYPE_SELL_LIMIT
    assert request["action"] == mt5.TRADE_ACTION_PENDING


def test_dry_broker_check_stops_at_risk_supervisor_without_calling_order_check():
    """If risk sizing fails (e.g. bad equity), order_check must never be called --
    a broker round-trip for a request we already know is invalid is pointless."""
    gw = _mock_gateway()
    gw.account.return_value = MagicMock(equity=0.0)  # triggers INVALID_ACCOUNT_EQUITY
    config = load_config(str(ROOT / "config" / "strategy.yaml"))
    intent = build_intent(_accepted_result())

    outcome = dry_broker_check(config, gw, intent)

    assert outcome["stage"] == "RISK_SUPERVISOR"
    gw.order_check.assert_not_called()

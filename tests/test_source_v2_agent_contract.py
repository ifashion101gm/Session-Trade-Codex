from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]


def contract():
    return yaml.safe_load((ROOT / "config" / "source_v2_agent.yaml").read_text())


def test_contract_is_analysis_only_and_cannot_mutate_mt5():
    data = contract()
    assert data["mode"] == "analysis_only"
    permissions = data["execution_permissions"]
    assert not any(permissions[x] for x in ("submit_orders", "modify_orders", "close_positions"))


def test_explicit_actionable_closes_are_six_not_seven():
    data = contract()["session"]
    assert data["deterministic_count"] == 6
    assert len(data["actionable_completed_m15_closes"]) == 6


def test_uncertain_bias_fails_all_setup_branches():
    assert contract()["bias"]["uncertain"] == "NO_TRADE_ALL_SETUPS"


def test_risk_and_spread_contract():
    risk = contract()["risk"]
    assert risk["risk_percent_equity"] == 1.0
    assert risk["stop_distance"] == "0.25 * asian_range"
    assert risk["maximum_spread_fraction_of_stop"] == 0.15


def test_hard_expiry_precedes_conflicting_workflow_times():
    data = contract()
    assert data["session"]["signal_expiry_local"] == "09:30"
    assert data["workflow"]["contradictory_supplied_workflow"]["status"] == "EXCLUDED_FROM_CANONICAL_BACKTEST"

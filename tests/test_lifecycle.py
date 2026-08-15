import json
import tempfile
import unittest
from pathlib import Path

from session_strategy.config import load_config
from session_strategy.lifecycle import assess_analysis, assess_profitability
from session_strategy.render import DISCLAIMER


def analysis_payload(strategy, **overrides):
    data = {
        "analysis_id": "abc123", "status": "NO_TRADE", "accepted": False,
        "entry": None, "config_hash": strategy.hash,
        "config_snapshot": strategy.raw, "schema_version": 2,
        "strategy_id": "ASIAN_SESSION_V1", "contract_version": "1.0",
        "account": {"account_type": "demo"},
        "reason_codes": ["RANGE_SESSION", "NO_QUALIFYING_SETUP"],
        "gates": [{"name": "G1_ENVIRONMENT", "passed": True, "detail": "demo"},
                  {"name": "G4_SESSION_DATA", "passed": False, "detail": "gap"}],
    }
    data.update(overrides)
    return data


def ticket_text(data):
    gates = "\n".join(g["name"] for g in data["gates"])
    plan = ""
    if data["status"] == "SIGNAL_ACCEPTED":
        plan = (f"\n- Entry: {data.get('entry')}\n- Stop loss: {data.get('stop_loss')}"
                f"\n- TP1 (75% off): {data.get('tp1_4r')} (4R)"
                f"\n- TP2 (runner): {data.get('tp2_5r')} (5R)"
                f"\n- Volume: {data.get('volume')} lots")
    return f"{data['analysis_id']}\n{data['status']}\n{gates}{plan}\n{DISCLAIMER}"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.strategy = load_config()

    def _assess(self, data, ticket=None):
        with tempfile.TemporaryDirectory() as tmp:
            a, t = Path(tmp) / "analysis.json", Path(tmp) / "ticket.md"
            a.write_text(json.dumps(data), encoding="utf-8")
            t.write_text(ticket if ticket is not None else ticket_text(data), encoding="utf-8")
            return assess_analysis(a, t)

    def test_conformant_no_trade_artifact_passes(self):
        self.assertTrue(self._assess(analysis_payload(self.strategy)).passed)

    def test_ticket_missing_gates_or_disclaimer_fails(self):
        data = analysis_payload(self.strategy)
        self.assertFalse(self._assess(data, ticket="abc123\nNO_TRADE").passed)

    def test_wrong_strategy_id_or_version_fails(self):
        self.assertFalse(self._assess(analysis_payload(self.strategy, strategy_id="SSPF_V2_2")).passed)
        self.assertFalse(self._assess(analysis_payload(self.strategy, contract_version="2.2")).passed)

    def test_status_must_follow_the_gates_and_the_plan(self):
        # All gates pass and an entry exists -> must be SIGNAL_ACCEPTED.
        accepted = analysis_payload(
            self.strategy, status="SIGNAL_ACCEPTED", accepted=True, entry=1.1645,
            stop_loss=1.1635, tp1_4r=1.1685, tp2_5r=1.1695, volume=0.05,
            gates=[{"name": "G1_ENVIRONMENT", "passed": True, "detail": "demo"}])
        self.assertTrue(self._assess(accepted).passed)
        mislabelled = dict(accepted, status="NO_TRADE")
        self.assertFalse(self._assess(mislabelled).passed)

    def test_accepted_ticket_must_repeat_exact_plan_values(self):
        accepted = analysis_payload(
            self.strategy, status="SIGNAL_ACCEPTED", accepted=True, entry=1.1645,
            stop_loss=1.1635, tp1_4r=1.1685, tp2_5r=1.1695, volume=0.05,
            gates=[{"name": "G1_ENVIRONMENT", "passed": True, "detail": "demo"}])
        altered_ticket = ticket_text(accepted).replace("- Stop loss: 1.1635", "- Stop loss: 1.1600")
        result = self._assess(accepted, altered_ticket)
        self.assertFalse(result.passed)
        self.assertTrue(any("stop_loss" in failure for failure in result.failures))

    def test_reason_codes_are_required(self):
        self.assertFalse(self._assess(analysis_payload(self.strategy, reason_codes=[])).passed)

    def test_configuration_snapshot_is_required_and_hash_checked(self):
        self.assertFalse(self._assess(analysis_payload(self.strategy, config_snapshot={})).passed)
        altered = json.loads(json.dumps(self.strategy.raw))
        altered["risk"]["risk_percent_per_trade"] = 9
        result = self._assess(analysis_payload(self.strategy, config_snapshot=altered))
        self.assertFalse(result.passed)
        self.assertIn("embedded configuration snapshot does not match config hash", result.failures)

    def test_schema_version_is_enforced(self):
        self.assertFalse(self._assess(analysis_payload(self.strategy, schema_version=1)).passed)

    def test_only_compliant_out_of_sample_records_count(self):
        good = [{"trade_id": str(i), "strategy_id": "ASIAN_SESSION_V1", "contract_version": "1.0",
                 "setup": "SWEEP", "r_multiple": 1.0 if i % 2 == 0 else -0.5,
                 "rule_compliant": True, "sample": "out_of_sample", "synthetic": False}
                for i in range(50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trades.json"
            path.write_text(json.dumps(good), encoding="utf-8")
            self.assertTrue(assess_profitability(path).passed)
            for row in good:
                row["synthetic"] = True
            path.write_text(json.dumps(good), encoding="utf-8")
            result = assess_profitability(path)
            self.assertFalse(result.passed)
            self.assertEqual(result.metrics["eligible_oos"], 0)

    def test_records_from_the_superseded_contract_are_rejected(self):
        stale = [{"trade_id": str(i), "strategy_id": "SSPF_V2_2", "contract_version": "2.2",
                  "r_multiple": 1.0, "rule_compliant": True, "sample": "forward_demo",
                  "synthetic": False} for i in range(50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trades.json"
            path.write_text(json.dumps(stale), encoding="utf-8")
            result = assess_profitability(path)
            self.assertFalse(result.passed)
            self.assertEqual(result.metrics["eligible_oos"], 0)


if __name__ == "__main__":
    unittest.main()

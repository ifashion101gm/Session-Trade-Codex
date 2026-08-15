import unittest
import yaml

from session_strategy.production_candidate_validator import validate


def cfg():
    with open("config/no_trade_research.yaml", encoding="utf-8") as source:
        return yaml.safe_load(source)


def payload():
    return {"symbol": "EURUSD", "current_time": "2026-08-12T08:30:00Z",
            "asian_session": {"high": 1.105, "low": 1.100},
            "ohlcv_data": {"atr_14d": .01, "spread": .0002, "pip_size": .0001,
                           "m15": [{"open": 1.101, "high": 1.103, "low": 1.1005, "close": 1.102},
                                   {"open": 1.101, "high": 1.102, "low": 1.099, "close": 1.1008}]}}


class ProductionCandidateValidatorTests(unittest.TestCase):
    def test_high_quality_m15_sweep_passes_read_only(self):
        result = validate(payload(), cfg())
        self.assertEqual(result["status"], "SIGNAL_ACCEPTED")
        self.assertGreaterEqual(result["metrics"]["rejection_wick_ratio"], .4)
        self.assertFalse(result["execution_authorized"])

    def test_low_quality_sweep_is_rejected(self):
        data = payload()
        data["ohlcv_data"]["m15"][-1] = {
            "open": 1.0993, "high": 1.101, "low": 1.099, "close": 1.1001}
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"], "GATE_G6_FAIL_LOW_WICK_QUALITY_RATIO")

    def test_uncertain_is_not_overridden(self):
        data = payload()
        data["ohlcv_data"]["m15"][-1] = {
            "open": 1.104, "high": 1.1052, "low": 1.103, "close": 1.1045}
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"], "GATE_G3_FAIL_CLASSIFICATION_UNCERTAIN")

    def test_pair_dynamic_ceiling_is_one_point_one_atr(self):
        data = payload(); data["asian_session"]["high"] = 1.112
        self.assertEqual(validate(data, cfg())["rejection_reason"],
                         "GATE_G5_FAIL_OVER_EXPANSION")

    def test_gbpusd_requires_efficiency_of_at_least_point_seven_five(self):
        data = payload(); data["symbol"] = "GBPUSD"
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"],
                         "GATE_ASSET_FAIL_GBPUSD_EFFICIENCY_BELOW_0_75")


if __name__ == "__main__":
    unittest.main()

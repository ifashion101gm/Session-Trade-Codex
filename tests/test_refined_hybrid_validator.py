import unittest

import yaml

from session_strategy.refined_hybrid_validator import validate


def cfg():
    with open("config/no_trade_research.yaml", encoding="utf-8") as source:
        return yaml.safe_load(source)


def payload():
    return {
        "symbol": "EURUSD", "current_time": "2026-08-12T08:30:00Z",
        "asian_session": {"high": 1.1050, "low": 1.1000},
        "ohlcv_data": {
            "atr_14d": 0.0100, "spread": 0.0002, "pip_size": 0.0001,
            "m15": [
                {"open": 1.1010, "high": 1.1030, "low": 1.1005, "close": 1.1020},
                {"open": 1.1020, "high": 1.1030, "low": 1.0990, "close": 1.1010},
            ],
            "m5": [],
            "h4": [
                {"high": 1.10, "low": 1.08}, {"high": 1.11, "low": 1.09},
                {"high": 1.12, "low": 1.10},
            ],
        },
    }


class RefinedHybridValidatorTests(unittest.TestCase):
    def test_sweep_is_selected_and_execution_remains_disabled(self):
        result = validate(payload(), cfg())
        self.assertEqual(result["status"], "SIGNAL_ACCEPTED")
        self.assertEqual(result["metrics"]["selected_canonical_setup"], "SWEEP")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["trade_parameters"]["max_hold_timestamp"], "20:00 UTC")

    def test_pair_specific_atr_ceiling_is_enforced(self):
        data = payload(); data["asian_session"]["high"] = 1.1140
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"], "GATE_G5_FAIL_OVER_EXPANSION")

    def test_h4_bias_can_override_uncertain_m15(self):
        data = payload()
        data["ohlcv_data"]["m15"][-1] = {
            "open": 1.1030, "high": 1.1052, "low": 1.1020, "close": 1.1045}
        result = validate(data, cfg())
        self.assertTrue(result["metrics"]["h4_bias_override_applied"])
        self.assertEqual(result["metrics"]["effective_classification"], "BULLISH_TREND")

    def test_neutral_h4_does_not_rescue_uncertain_m15(self):
        data = payload()
        data["ohlcv_data"]["m15"][-1] = {
            "open": 1.1030, "high": 1.1052, "low": 1.1020, "close": 1.1045}
        data["ohlcv_data"]["h4"] = []
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"], "GATE_CLASSIFICATION_UNCERTAIN")

    def test_dynamic_buffer_uses_larger_atr_component(self):
        result = validate(payload(), cfg())
        # max(1.5*0.0002, 0.05*0.01) = 0.0005; long sweep extreme 1.0990.
        self.assertAlmostEqual(result["trade_parameters"]["stop_loss"], 1.0985)

    def test_shallow_trend_retrace_must_touch_named_level(self):
        data = payload()
        data["ohlcv_data"]["m15"] = [
            {"open": 1.1000, "high": 1.1010, "low": 1.0999, "close": 1.1005},
            {"open": 1.1060, "high": 1.1070, "low": 1.1060, "close": 1.1068},
        ]
        result = validate(data, cfg())
        self.assertEqual(result["rejection_reason"], "GATE_PATTERN_FAIL_NO_CANONICAL_SETUP")

    def test_sweep_wins_priority_over_overlapping_range_rejection(self):
        result = validate(payload(), cfg())
        self.assertIn("SWEEP", result["metrics"]["qualifying_candidates"])
        self.assertEqual(result["metrics"]["selected_canonical_setup"], "SWEEP")


if __name__ == "__main__":
    unittest.main()

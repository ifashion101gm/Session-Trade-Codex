import unittest

import yaml

from session_strategy.research_validator import validate


def config():
    with open("config/no_trade_research.yaml", encoding="utf-8") as source:
        return yaml.safe_load(source)


def payload():
    return {
        "symbol": "EURUSD",
        "current_time": "2026-08-12T08:30:00Z",
        "asian_session": {"high": 1.1050, "low": 1.1000,
                          "start": "2026-08-12T00:00:00Z", "end": "2026-08-12T08:00:00Z"},
        "ohlcv_data": {"atr_14d": 0.0100, "pip_size": 0.0001, "setup": "SWEEP",
                       "direction": "LONG", "spread_buffer": 0.0002,
                       "signal_candle": {"open": 1.1001, "high": 1.1010,
                                         "low": 1.0990, "close": 1.1005}},
        "dom_data": {"resting_limit_volume_at_sweep": 300,
                     "average_20_level_depth": 100, "cvd_reversal": True},
    }


class ResearchValidatorTests(unittest.TestCase):
    def test_valid_sweep_returns_read_only_proposal(self):
        result = validate(payload(), config())
        self.assertEqual(result["status"], "SIGNAL_ACCEPTED")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["trade_parameters"]["risk_reward_ratio"], "1:5")
        self.assertAlmostEqual(result["trade_parameters"]["stop_loss"], 1.0988)

    def test_compressed_range_fails_before_dom(self):
        data = payload(); data["asian_session"]["high"] = 1.1010
        result = validate(data, config())
        self.assertEqual(result["rejection_reason"], "GATE_G4_FAIL_COMPRESSION_VOLATILITY")

    def test_overexpanded_range_is_rejected(self):
        data = payload(); data["asian_session"]["high"] = 1.1120
        result = validate(data, config())
        self.assertEqual(result["rejection_reason"], "GATE_G5_FAIL_OVER_EXPANSION")

    def test_missing_or_weak_dom_fails_closed(self):
        data = payload(); data["dom_data"] = {}
        self.assertEqual(validate(data, config())["rejection_reason"],
                         "GATE_G6_FAIL_DOM_DATA_MISSING")
        data = payload(); data["dom_data"]["resting_limit_volume_at_sweep"] = 200
        self.assertEqual(validate(data, config())["rejection_reason"],
                         "GATE_G6_FAIL_DOM_LIQUIDITY_INSUFFICIENT")

    def test_outside_window_is_rejected(self):
        data = payload(); data["current_time"] = "2026-08-12T11:00:00Z"
        self.assertEqual(validate(data, config())["rejection_reason"],
                         "GATE_G1_FAIL_OUTSIDE_EXECUTION_WINDOW")


if __name__ == "__main__":
    unittest.main()

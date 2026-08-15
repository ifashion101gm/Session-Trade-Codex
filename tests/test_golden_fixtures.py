"""Golden regression cases loaded from versioned candle-feed fixtures."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from session_strategy.config import load_config
from session_strategy.engine import analyze
from session_strategy.models import AccountSnapshot, Candle, SymbolSpec
from session_strategy.render import write_artifacts


FIXTURES = Path(__file__).with_name("fixtures")
TRADING_DATE = date(2026, 8, 11)
WHEN = datetime(2026, 8, 11, 8, 45, tzinfo=timezone.utc)
SPEC = SymbolSpec("EURUSD", 5, .00001, .00001, .01, 100, .01, 0)


def load_case(name: str):
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    session_payload = payload
    if "asian_session_fixture" in payload:
        session_payload = json.loads(
            (FIXTURES / payload["asian_session_fixture"]).read_text(encoding="utf-8"))

    def bars(key):
        return [Candle(datetime.fromisoformat(row["time"].replace("Z", "+00:00")),
                       row["open"], row["high"], row["low"], row["close"],
                       row.get("tick_volume", 0)) for row in payload[key]]

    session = [Candle(datetime.fromisoformat(row["time"].replace("Z", "+00:00")),
                      row["open"], row["high"], row["low"], row["close"],
                      row.get("tick_volume", 0)) for row in session_payload["asian_session"]]
    return payload, session, bars("execution_window")


class GoldenFixtureTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def analyze_case(self, name):
        payload, session, execution = load_case(name)
        result = analyze(
            config=self.config, symbol="EURUSD", trading_date=TRADING_DATE, now=WHEN,
            account=AccountSnapshot("****985", "demo", 1000, 1000, "VTMarkets-Demo",
                                    True, True, 10),
            spec=SPEC,
            tick=payload.get("tick", {"bid": 1.16499, "ask": 1.16501,
                                      "time": WHEN.timestamp(), "broker_offset_hours": 0}),
            session_candles=session, execution_candles=execution,
            one_lot_loss=lambda *_: 100.0, daily_used_cash=0, drawdown_percent=0,
            journal_healthy=True, trades_taken_this_session=0,
        )
        return payload["expected"], result

    def test_versioned_golden_cases(self):
        names = (
            "bullish_sweep_pass.json",
            "bearish_sweep_structural_stop_fail.json",
            "range_rejection_pass.json",
            "trend_continuation_invalidated.json",
            "range_expansion_no_close_back.json",
            "contradictory_dual_boundary_sweep.json",
            "stale_quote_spread_expansion.json",
        )
        for name in names:
            with self.subTest(fixture=name):
                expected, result = self.analyze_case(name)
                self.assertEqual(result.session_type, expected["session_type"])
                self.assertEqual(result.setup, expected["setup"])
                self.assertEqual(result.status, expected["status"])
                if "direction" in expected:
                    self.assertEqual(result.direction, expected["direction"])
                if "reason_code" in expected:
                    self.assertIn(expected["reason_code"], result.reason_codes)
                if "warning_contains" in expected:
                    self.assertTrue(any(expected["warning_contains"] in warning
                                        for warning in result.warnings))

    def test_analysis_json_embeds_reconstructable_config_snapshot(self):
        _, result = self.analyze_case("bullish_sweep_pass.json")
        with TemporaryDirectory() as temporary, patch("session_strategy.render.chart"):
            paths = write_artifacts(result, [], Path(temporary))
            artifact = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
        self.assertEqual(artifact["config_hash"], self.config.hash)
        self.assertEqual(artifact["config_snapshot"], self.config.raw)
        self.assertEqual(artifact["config_snapshot"]["sweep_buffer_fraction"], 0.02)


if __name__ == "__main__":
    unittest.main()

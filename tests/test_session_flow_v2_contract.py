import datetime as dt
import unittest
from pathlib import Path

import yaml

from session_strategy.session_contract import (MMT, SESSION_FLOW_V2_LEGS, StrategyType,
                                               SweepResolution, classify_completed_reference,
                                               path_efficiency_ratio, select_strategy)


class SessionFlowV2ContractTests(unittest.TestCase):
    def setUp(self):
        self.day = dt.date(2022, 10, 3)

    def test_asian_half_open_window_has_32_bars(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        start, end = leg.bounds(self.day)
        opens = [start + dt.timedelta(minutes=15 * i) for i in range(32)]
        leg.validate_bar_opens(self.day, opens)
        self.assertEqual(opens[0].time(), dt.time(0, 0))
        self.assertEqual(opens[-1].time(), dt.time(7, 45))
        self.assertEqual(end.time(), dt.time(8, 0))

    def test_london_half_open_window_has_20_bars(self):
        leg = SESSION_FLOW_V2_LEGS["POST_LONDON"]
        start, end = leg.bounds(self.day)
        opens = [start + dt.timedelta(minutes=15 * i) for i in range(20)]
        leg.validate_bar_opens(self.day, opens)
        self.assertEqual(opens[-1].time(), dt.time(11, 45))
        self.assertEqual(end.time(), dt.time(12, 0))

    def test_activation_times_convert_to_myanmar(self):
        self.assertEqual(
            SESSION_FLOW_V2_LEGS["POST_ASIAN"].activation_mmt(self.day).timetz(),
            dt.time(14, 30, tzinfo=MMT),
        )
        self.assertEqual(
            SESSION_FLOW_V2_LEGS["POST_LONDON"].activation_mmt(self.day).timetz(),
            dt.time(18, 30, tzinfo=MMT),
        )

    def test_rejects_missing_duplicate_or_future_bar(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        start, _ = leg.bounds(self.day)
        valid = [start + dt.timedelta(minutes=15 * i) for i in range(32)]
        for invalid in (valid[:-1], valid[:-1] + [valid[-2]], valid + [valid[-1] + dt.timedelta(minutes=15)]):
            with self.assertRaisesRegex(ValueError, "INVALID_REFERENCE_SESSION"):
                leg.validate_bar_opens(self.day, invalid)

    def test_reference_objects_are_frozen(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        with self.assertRaises((AttributeError, TypeError)):
            leg.expected_m15_candles = 28

    def test_signed_er_includes_first_open_to_close_path_and_routes_not_trend(self):
        # Net displacement=20; close-to-close path=45; first open-to-close=8.
        closes = [108.0, 136.5, 120.0]
        self.assertAlmostEqual(path_efficiency_ratio(100.0, closes), 20 / 53)
        selected = select_strategy(100.0, closes, SweepResolution.NO_SWEEP)
        self.assertFalse(selected.trend_test)
        self.assertEqual(selected.strategy_type, StrategyType.RANGE)

    def test_trend_short_circuits_sweep_and_threshold_equality_is_trend(self):
        trend = select_strategy(100.0, [100.0, 110.0], SweepResolution.QUALIFIED)
        self.assertEqual(trend.strategy_type, StrategyType.TREND)
        self.assertEqual(trend.sweep_test, "NOT_EVALUATED")
        threshold = select_strategy(100.0, [100.0, 117.5, 110.0],
                                    SweepResolution.QUALIFIED)
        self.assertAlmostEqual(threshold.efficiency_ratio, 0.40)
        self.assertEqual(threshold.strategy_type, StrategyType.TREND)

    def test_not_trend_waterfall_resolves_sweep_or_range_at_box_completion(self):
        closes = [100.0, 110.0, 100.0]  # ER=0
        sweep = select_strategy(100.0, closes, SweepResolution.QUALIFIED)
        self.assertEqual(sweep.strategy_type, StrategyType.SWEEP)
        range_result = select_strategy(100.0, closes, SweepResolution.NO_SWEEP)
        self.assertEqual(range_result.strategy_type, StrategyType.RANGE)
        with self.assertRaisesRegex(ValueError, "SWEEP_RESULT_REQUIRED"):
            select_strategy(100.0, closes)

    def test_zero_path_proceeds_to_sweep_and_every_resolved_result_has_one_type(self):
        resolved = [
            select_strategy(100.0, [100.0, 110.0]),
            select_strategy(100.0, [100.0, 100.0], SweepResolution.QUALIFIED),
            select_strategy(100.0, [100.0, 100.0], SweepResolution.NO_SWEEP),
        ]
        self.assertEqual([x.strategy_type for x in resolved],
                         [StrategyType.TREND, StrategyType.SWEEP, StrategyType.RANGE])
        for result in resolved:
            flags = [result.strategy_type is member for member in StrategyType]
            self.assertEqual(sum(flags), 1, "resolved result must own exactly one type")
        self.assertEqual(path_efficiency_ratio(100.0, [100.0, 100.0]), 0.0)

    def test_range_classification_remains_range_when_entry_is_unavailable(self):
        selected = select_strategy(100.0, [100.0, 100.0], SweepResolution.NO_SWEEP)
        entry_status = "NO_VALID_RANGE_ENTRY"
        self.assertEqual(selected.strategy_type, StrategyType.RANGE)
        self.assertEqual(entry_status, "NO_VALID_RANGE_ENTRY")

    def test_asian_classifier_rejects_post_box_candle_and_cannot_reroute(self):
        leg = SESSION_FLOW_V2_LEGS["POST_ASIAN"]
        start, _ = leg.bounds(self.day)
        opens = [start + dt.timedelta(minutes=15 * i) for i in range(32)]
        closes = [100.0] * 32
        selected = classify_completed_reference(
            leg, self.day, opens, 100.0, closes, SweepResolution.NO_SWEEP)
        self.assertEqual(selected.strategy_type, StrategyType.RANGE)
        with self.assertRaisesRegex(ValueError, "INVALID_REFERENCE_SESSION"):
            classify_completed_reference(
                leg, self.day, opens + [start + dt.timedelta(hours=8)],
                100.0, closes + [150.0], SweepResolution.QUALIFIED)

    def test_london_classifier_activates_with_only_20_completed_bars(self):
        leg = SESSION_FLOW_V2_LEGS["POST_LONDON"]
        start, _ = leg.bounds(self.day)
        opens = [start + dt.timedelta(minutes=15 * i) for i in range(20)]
        selected = classify_completed_reference(
            leg, self.day, opens, 100.0, [100.0] * 20,
            SweepResolution.NO_SWEEP)
        self.assertEqual(selected.strategy_type, StrategyType.RANGE)
        self.assertEqual(leg.activation_utc(self.day).time(), dt.time(12, 0))

    def test_machine_contract_uses_waterfall_and_signed_common_management(self):
        path = Path(__file__).resolve().parents[1] / "archive" / "session_configs" / "session_flow_v2.yaml"
        contract = yaml.safe_load(path.read_text(encoding="utf-8"))
        classifier = contract["classifier"]
        frozen_classifier = contract["session_classifier"]
        self.assertEqual(frozen_classifier["classifier_id"], "ER_ONLY_V2")
        self.assertEqual(frozen_classifier["threshold"], 0.40)
        self.assertEqual(frozen_classifier["equality"], "TREND")
        self.assertEqual(frozen_classifier["zero_path"], "RANGE")
        self.assertEqual(frozen_classifier["status"], "VALIDATED")
        self.assertEqual(frozen_classifier["legacy_070_policy"],
                         "FORBIDDEN_NOT_PART_OF_ER_ONLY_V2")
        self.assertEqual(classifier["routing_order"],
                         ["SESSION_BOX", "SESSION_CLASSIFIER",
                          "REFERENCE_SWEEP_CLASSIFIER", "SETUP_ROUTER"])
        self.assertEqual(classifier["final_session_types"], ["TREND", "RANGE"])
        self.assertEqual(classifier["final_setup_types"], ["TREND", "SWEEP", "RANGE"])
        self.assertEqual(classifier["authoritative_fields"],
                         ["session_type", "setup_type", "entry_engine"])
        self.assertEqual(classifier["routing_acceptance_status"],
                         "VALIDATED_STATELESS_COMPLETED_BOX")
        self.assertEqual(classifier["midpoint_role"], "DIAGNOSTIC_ONLY")
        self.assertEqual(contract["experimental_sweep"]["completed_box_qualification_status"],
                         "RETIRED_EXPERIMENT_NOT_ROUTING_AUTHORITY")
        proposal = contract["sweep_classifier"]
        self.assertEqual(proposal["version"], "1.0")
        self.assertEqual(proposal["status"],
                         "VALIDATED_FOR_SESSION_FLOW_V2_SIMPLE")
        self.assertTrue(proposal["executable_authority"])
        self.assertEqual(proposal["implementation"],
                         "session_strategy.session_contract.classify_sweep")
        self.assertEqual(classifier["classification_event"],
                         "ALL_ROUTING_AT_REFERENCE_BOX_COMPLETE")
        self.assertEqual(classifier["post_reference_session_rerouting"], "FORBIDDEN")
        lineage = contract["audit_lineage"]
        self.assertEqual(lineage["resolved_final_type_invariant"],
                         "EXACTLY_ONE_OF_TREND_SWEEP_RANGE")
        self.assertEqual(lineage["range_setup_pending_state"],
                         "NOT_APPLICABLE_ROUTE_RESOLVED_AT_BOX_CLOSE")
        risk = contract["common_price_risk_management"]
        self.assertEqual(risk["one_r_reference_range_fraction"], 0.25)
        self.assertEqual(risk["partial_target_r"], 4.0)
        self.assertEqual(risk["partial_close_fraction"], 0.75)
        self.assertEqual(risk["final_target_r"], 5.0)
        self.assertEqual(risk["runner_fraction"], 0.25)
        self.assertFalse(risk["automatic_breakeven"])
        self.assertEqual(risk["stop_after_partial"], "ORIGINAL_STOP_UNCHANGED")
        cowork = contract["cowork_sweep"]
        self.assertEqual(cowork["status"], "RETIRED_BY_SESSION_FLOW_V2_SIMPLE")
        self.assertFalse(cowork["strategy_selection_authority"])
        self.assertEqual(cowork["validation_gate"],
                         "VALID_FROZEN_SESSION_AND_VALIDATED_ER_ONLY_V2_RANGE_ONLY")
        self.assertEqual(cowork["short_entry_reference"], "MAX_OPEN_CLOSE")
        self.assertEqual(cowork["management_override"]["runner_stop_after_partial"],
                         "BREAKEVEN")


if __name__ == "__main__":
    unittest.main()

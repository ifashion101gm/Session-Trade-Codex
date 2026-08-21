from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os

import yaml


@dataclass(frozen=True)
class SymbolConfig:
    """Logical symbol. `broker_symbol` is the exact MT5 string, which varies by
    account and server group. `display_pip_size` is for reports only — sizing and
    price normalisation use live MT5 metadata."""
    broker_symbol: str
    display_pip_size: float
    minimum_range: float
    maximum_range: float
    maximum_spread: float


@dataclass(frozen=True)
class SetupRule:
    enabled: bool
    session_types: tuple[str, ...]
    confirmation: str
    entry_price: str
    require_structural_stop_clearance: bool = False
    disallow_after_confirmed_sweep: bool = False


@dataclass(frozen=True)
class StrategyConfig:
    mode: str
    strategy_id: str
    contract_version: str
    system: dict[str, Any]
    session_contract: dict[str, Any]
    symbol_mapping: dict[str, str]
    timeframe: str
    timeframe_seconds: int
    use_closed_candles_only: bool
    interval_semantics: str
    candle_timestamp_semantics: str
    session_start_utc: str
    session_end_utc: str
    session_candles: int
    execution_start_utc: str
    execution_end_utc: str
    post_session_candles: int
    midpoint_zone_low_fraction: float
    midpoint_zone_high_fraction: float
    sweep_buffer_fraction: float
    stop_buffer_fraction: float
    touch_tolerance_fraction: float
    rejection_quality_fraction: float
    governance: dict[str, Any]
    execution_permissions: dict[str, bool]
    account_guard: dict[str, Any]
    live_data: dict[str, Any]
    data_quality: dict[str, Any]
    classification: dict[str, Any]
    setups: dict[str, Any]
    fixed_stop_policy: dict[str, Any]
    management: dict[str, Any]
    cost_model: dict[str, Any]
    news_filter: dict[str, Any]
    risk: dict[str, Any]
    symbols: dict[str, SymbolConfig]
    setup_rules: dict[str, SetupRule] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    # ---- convenience accessors: one place per concept ----------------------
    @property
    def hash(self) -> str:
        encoded = json.dumps(self.raw, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()[:16]

    @property
    def signoff_hash(self) -> str:
        """Fingerprint configuration while excluding the approval record itself."""
        raw = json.loads(json.dumps(self.raw))
        raw.get("governance", {}).pop("parameter_signoff", None)
        encoded = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()[:16]

    @property
    def efficiency_ratio_threshold(self) -> float:
        return float(self.classification["efficiency_ratio_threshold"])

    @property
    def close_location_trend(self) -> float:
        return float(self.classification["close_location_trend"])

    @property
    def stop_range_fraction(self) -> float:
        return float(self.fixed_stop_policy["stop_range_fraction"])

    @property
    def widening_allowed(self) -> bool:
        return bool(self.fixed_stop_policy["widening_allowed"])

    @property
    def partial_target_r(self) -> float:
        return float(self.management["partial_target_r"])

    @property
    def final_target_r(self) -> float:
        return float(self.management["final_target_r"])

    @property
    def partial_close_percent(self) -> float:
        return float(self.management["partial_close_percent"])

    @property
    def risk_percent_per_trade(self) -> float:
        return float(self.risk["risk_percent_per_trade"])

    @property
    def daily_risk_limit_percent(self) -> float:
        return float(self.risk["daily_risk_limit_percent"])

    @property
    def maximum_drawdown_percent(self) -> float:
        return float(self.risk["maximum_drawdown_percent"])

    @property
    def maximum_trades_per_symbol_session(self) -> int:
        return int(self.risk["maximum_trades_per_symbol_session"])

    @property
    def maximum_tick_age_seconds(self) -> int:
        return int(self.live_data["maximum_tick_age_seconds"])

    @property
    def setup_priority(self) -> list[str]:
        return list(self.setups["priority"])

    @property
    def expected_session_candles(self) -> int:
        return _window_seconds(self.session_start_utc, self.session_end_utc) // self.timeframe_seconds

    @property
    def expected_post_session_candles(self) -> int:
        return _window_seconds(self.execution_start_utc, self.execution_end_utc) // self.timeframe_seconds

    def allowed_logins(self, include_environment: bool = True) -> list[int]:
        """Config allowlist, extended by SSPF_ALLOWED_LOGINS so a real login
        never needs to enter version control."""
        logins = [int(x) for x in self.account_guard.get("allowed_logins", [])]
        if not include_environment:
            return logins
        env = os.environ.get("SSPF_ALLOWED_LOGINS", "")
        if not env and os.name == "nt":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    env = str(winreg.QueryValueEx(key, "SSPF_ALLOWED_LOGINS")[0])
            except (FileNotFoundError, OSError):
                pass
        logins += [int(x.strip()) for x in env.split(",") if x.strip().isdigit()]
        return logins

    def broker_symbol(self, logical: str) -> str:
        return self.symbols[logical].broker_symbol

    def resolve_symbol(self, requested: str) -> str:
        """Return the normalized strategy symbol for an exact supported input.

        Broker-suffixed names are accepted as inputs, but live MT5 calls always
        use the corresponding configured ``broker_symbol`` rather than an
        unsuffixed fallback.
        """
        if requested in self.symbols:
            return requested
        logical = self.symbol_mapping.get(requested)
        if logical in self.symbols and self.broker_symbol(logical) == requested:
            return logical
        raise KeyError(requested)

    def cost_per_lot_round_turn(self) -> float:
        return float(self.cost_model.get("commission_per_lot_round_turn") or 0.0)

    def slippage_points(self) -> float:
        return float(self.cost_model.get("slippage_points") or 0.0)


def _window_seconds(start: str, end: str) -> int:
    sh, sm = (int(x) for x in start.split(":"))
    eh, em = (int(x) for x in end.split(":"))
    seconds = (eh * 3600 + em * 60) - (sh * 3600 + sm * 60)
    return seconds + 86400 if seconds <= 0 else seconds


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "strategy.yaml"


_SETUP_KEYS = ("sweep", "range_rejection", "trend_continuation")


def load_config(path: str | Path | None = None) -> StrategyConfig:
    source = Path(path) if path else default_config_path()
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if raw.get("mode") != "analysis_only":
        raise ValueError("Only analysis_only mode is supported")

    known = set(StrategyConfig.__dataclass_fields__) - {"symbols", "raw", "setup_rules"}
    unknown = sorted(set(raw) - known - {"symbols"})
    if unknown:
        raise ValueError(f"Unknown configuration key(s): {', '.join(unknown)}")
    missing = sorted(known - set(raw))
    if missing:
        raise ValueError(f"Missing configuration key(s): {', '.join(missing)}")

    symbols = {name: SymbolConfig(**values) for name, values in raw["symbols"].items()}
    setup_rules = {}
    for key in _SETUP_KEYS:
        block = dict(raw["setups"][key])
        block["session_types"] = tuple(block["session_types"])
        setup_rules[key.upper()] = SetupRule(**block)

    config = StrategyConfig(**{**raw, "symbols": symbols, "setup_rules": setup_rules, "raw": raw})
    _validate(config)
    return config


def _validate(config: StrategyConfig) -> None:
    """Fail loudly on a configuration that cannot express the specification."""
    problems: list[str] = []

    system = config.system
    contract = config.session_contract
    if system.get("engine_version") != "v1.0" or system.get("active_strategy") != "ASIAN_SESSION_V1":
        problems.append("system must select ASIAN_SESSION_V1 engine version v1.0")
    if system.get("supersede_legacy") is not True:
        problems.append("system.supersede_legacy must be true")
    if config.strategy_id != "ASIAN_SESSION_V1" or config.contract_version != "1.0":
        problems.append("strategy_id/contract_version must be ASIAN_SESSION_V1/1.0")
    # CORRECTED 2026-08-19 (C-33): these literals still asserted the superseded
    # 22:00-07:00 / 36-candle window after config/strategy.yaml was corrected on
    # 2026-08-15 to 00:00-07:00 / 28. The validator therefore rejected its own SSOT
    # before any engine logic ran. Authority for 00:00-07:00 / 28:
    # config/strategy.yaml L85-90, SESSION_FLOW_V1_SPEC.md, STRATEGY_SPEC.md S10.
    # sweep_window_hours stays 9 — it describes the 07:00-16:00 execution window,
    # which is unchanged. No strategy behaviour depends on session_contract; it is
    # asserted here and never read elsewhere.
    expected_contract = {
        "asian_start_utc": "00:00",
        "asian_end_utc": "07:00",
        "required_m15_candles": 28,
        "sweep_window_hours": 9,
    }
    for key, value in expected_contract.items():
        if contract.get(key) != value:
            problems.append(f"session_contract.{key} must be {value!r} for ASIAN_SESSION_V1")
    if (config.session_start_utc, config.session_end_utc, config.session_candles,
            config.execution_start_utc, config.execution_end_utc, config.post_session_candles) != (
                "00:00", "07:00", 28, "07:00", "16:00", 36):
        problems.append("runtime session window must be 00:00-07:00 plus 07:00-16:00 UTC (28 + 36 M15 candles)")

    if config.timeframe_seconds <= 0:
        problems.append("timeframe_seconds must be positive")
    elif config.session_candles != config.expected_session_candles:
        problems.append(
            f"session_candles={config.session_candles} does not match the "
            f"{config.session_start_utc}-{config.session_end_utc} window at {config.timeframe} "
            f"(expected {config.expected_session_candles})")
    if config.timeframe_seconds > 0 and config.post_session_candles != config.expected_post_session_candles:
        problems.append(
            f"post_session_candles={config.post_session_candles} does not match the "
            f"{config.execution_start_utc}-{config.execution_end_utc} window at {config.timeframe} "
            f"(expected {config.expected_post_session_candles})")
    if config.interval_semantics != "left_closed_right_open":
        problems.append("interval_semantics must be left_closed_right_open")
    if not config.use_closed_candles_only:
        problems.append("use_closed_candles_only must be true")

    if not 0 < config.stop_range_fraction < 1:
        problems.append("fixed_stop_policy.stop_range_fraction must be between 0 and 1")
    if config.widening_allowed:
        problems.append("fixed_stop_policy.widening_allowed must be false — the stop is fixed")
    if config.fixed_stop_policy.get("on_clearance_failure") != "REJECT_TRADE":
        problems.append("fixed_stop_policy.on_clearance_failure must be REJECT_TRADE")
    if not config.fixed_stop_policy.get("structural_clearance_required"):
        problems.append("fixed_stop_policy.structural_clearance_required must be true")
    if config.final_target_r <= config.partial_target_r:
        problems.append("management.final_target_r must exceed management.partial_target_r")
    if not 0 < config.partial_close_percent < 100:
        problems.append("management.partial_close_percent must be between 0 and 100")
    if config.management.get("trailing_stop_enabled"):
        problems.append("management.trailing_stop_enabled must be false for ASIAN_SESSION_V1")

    news = config.news_filter
    if news.get("enabled") and news.get("unavailable_policy") != "NO_TRADE":
        problems.append("news_filter.unavailable_policy must be NO_TRADE when enabled")
    if float(news.get("minutes_before", -1)) < 0 or float(news.get("minutes_after", -1)) < 0:
        problems.append("news_filter windows must be non-negative")

    if not 0 <= config.efficiency_ratio_threshold <= 1:
        problems.append("classification.efficiency_ratio_threshold must be between 0 and 1")
    if not 0.5 <= config.close_location_trend <= 1:
        problems.append("classification.close_location_trend must be between 0.5 and 1")
    if config.classification.get("trade_uncertain_sessions"):
        problems.append("classification.trade_uncertain_sessions must be false")
    if config.midpoint_zone_low_fraction >= config.midpoint_zone_high_fraction:
        problems.append("midpoint zone bounds are inverted")

    if config.governance.get("optimization_allowed") is not False:
        problems.append("governance.optimization_allowed must be false for the Stage 2 baseline")

    for permission in ("submit_orders", "modify_orders", "close_positions"):
        if config.execution_permissions.get(permission):
            problems.append(f"execution_permissions.{permission} must be false in analysis_only mode")

    if config.risk_percent_per_trade <= 0 or config.risk_percent_per_trade > config.daily_risk_limit_percent:
        problems.append("risk.risk_percent_per_trade must be positive and within the daily limit")
    if config.risk.get("risk_basis") != "LOWER_OF_BALANCE_EQUITY":
        problems.append("risk.risk_basis must be LOWER_OF_BALANCE_EQUITY")
    if config.risk["percentage_scale"] != "PERCENT_NOT_DECIMAL":
        problems.append("risk.percentage_scale must be PERCENT_NOT_DECIMAL")

    if config.cost_model.get("reject_if_cost_model_incomplete"):
        if config.cost_model.get("commission_per_lot_round_turn") is None or \
           config.cost_model.get("slippage_points") is None:
            problems.append("cost_model is incomplete but reject_if_cost_model_incomplete is true")

    missing_setups = [s for s in config.setup_priority if s not in config.setup_rules]
    if missing_setups:
        problems.append(f"setups.priority names undefined setup(s): {', '.join(missing_setups)}")

    for name, symbol in config.symbols.items():
        if symbol.minimum_range >= symbol.maximum_range:
            problems.append(f"{name}: minimum_range must be below maximum_range")
        if symbol.maximum_spread <= 0 or symbol.display_pip_size <= 0:
            problems.append(f"{name}: display_pip_size and maximum_spread must be positive")
        if not symbol.broker_symbol:
            problems.append(f"{name}: broker_symbol must be set")

    for broker, logical in config.symbol_mapping.items():
        if logical not in config.symbols:
            problems.append(f"symbol_mapping.{broker} references unknown symbol {logical}")
        elif config.broker_symbol(logical) != broker:
            problems.append(f"symbol_mapping.{broker} must match {logical}.broker_symbol exactly")

    if problems:
        raise ValueError("Invalid strategy configuration:\n  - " + "\n  - ".join(problems))

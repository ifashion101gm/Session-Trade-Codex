"""ASIAN_SESSION_V1 decision engine.

Deterministic, close-confirmed and event-driven. `analyze()` is a pure function:
every input is injected, no clock is read, no I/O is performed. Identical inputs
always produce identical output apart from the random analysis id.

Setup priority per symbol per session: SWEEP > RANGE_REJECTION > TREND_CONTINUATION.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from math import floor
from uuid import uuid4

from .config import StrategyConfig
from .models import (AccountSnapshot, AnalysisResult, AsianLevels, Candle, Gate, Reason,
                     SymbolSpec)


# --------------------------------------------------------------------------- time

def session_bounds(trading_date: date, config: StrategyConfig) -> tuple[datetime, datetime]:
    """Half-open [start, end) UTC bounds. The session ends on `trading_date`."""
    start_clock = time.fromisoformat(config.session_start_utc)
    end_clock = time.fromisoformat(config.session_end_utc)
    end = datetime.combine(trading_date, end_clock, timezone.utc)
    start_date = trading_date - timedelta(days=1) if start_clock >= end_clock else trading_date
    return datetime.combine(start_date, start_clock, timezone.utc), end


def execution_bounds(trading_date: date, config: StrategyConfig) -> tuple[datetime, datetime]:
    start = datetime.combine(trading_date, time.fromisoformat(config.execution_start_utc), timezone.utc)
    end = datetime.combine(trading_date, time.fromisoformat(config.execution_end_utc), timezone.utc)
    return start, (end + timedelta(days=1) if end <= start else end)


def calibrate_broker_tick(now: datetime, raw_tick_time: float,
                          declared_offset_hours: int | None = None) -> tuple[bool, int, float]:
    """Normalize broker-shifted epoch timestamps using a verified whole-hour UTC offset."""
    offset_hours = 0 if declared_offset_hours is None else declared_offset_hours
    if not -14 <= offset_hours <= 14:
        return False, offset_hours, float("inf")
    return True, offset_hours, now.timestamp() - (raw_tick_time - offset_hours * 3600)


# --------------------------------------------------------------------- validation

def filter_window(candles: list[Candle], start: datetime, end: datetime) -> list[Candle]:
    """Half-open [start, end) by bar-open time.

    MT5 `copy_rates_range` may include the closing timestamp, so the window is
    re-applied after retrieval rather than trusted from the API call.
    """
    return [c for c in candles if start <= c.time < end]


def validate_candles(candles: list[Candle], window_start: datetime, count: int,
                     config: StrategyConfig | None = None,
                     minimum_count: int | None = None,
                     now: datetime | None = None) -> tuple[bool, str]:
    """Contiguous, closed, correctly ordered candles inside the window."""
    step = timedelta(seconds=config.timeframe_seconds) if config else timedelta(minutes=15)
    quality = config.data_quality if config else {}
    required = count if minimum_count is None else minimum_count
    if len(candles) < required or len(candles) > count:
        return False, f"expected {required}-{count} candles, received {len(candles)}"
    if not candles:
        return True, "0 completed candles"

    times = [c.time for c in candles]
    if quality.get("require_unique_timestamps", True) and len(set(times)) != len(times):
        return False, "duplicate candle timestamps"
    if quality.get("reject_non_monotonic_timestamps", True) and times != sorted(times):
        return False, "non-monotonic candle timestamps"
    if quality.get("reject_future_timestamps", True) and now is not None:
        if any(t + step > now for t in times):
            return False, "candle window includes an unclosed or future bar"

    expected = [window_start + step * i for i in range(count)]
    if times[0] not in expected:
        return False, "first candle is outside the configured window"
    first = expected.index(times[0])
    if times != expected[first:first + len(candles)]:
        return False, "candles contain a gap, duplicate, or out-of-window timestamp"
    if any(not (c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high) for c in candles):
        return False, "invalid OHLC ordering"
    if quality.get("reject_zero_ohlc", True) and any(
            c.high <= 0 or c.low <= 0 or c.open <= 0 or c.close <= 0 for c in candles):
        return False, "non-positive OHLC value"
    return True, f"{len(candles)} contiguous closed candles"


# ------------------------------------------------------------------------- levels

def lock_asian_levels(candles: list[Candle], config: StrategyConfig) -> AsianLevels:
    """Immutable at the session close. Nothing after the lock may modify these."""
    high = max(c.high for c in candles)
    low = min(c.low for c in candles)
    rng = high - low
    opened, closed = candles[0].open, candles[-1].close
    efficiency = abs(closed - opened) / rng if rng else 0.0
    location = (closed - low) / rng if rng else 0.0
    return AsianLevels(
        high=high, low=low, range=rng, midpoint=low + 0.5 * rng,
        open=opened, close=closed,
        risk_unit=config.stop_range_fraction * rng,
        lower_quartile=low + 0.25 * rng,
        upper_quartile=high - 0.25 * rng,
        midpoint_zone_low=low + config.midpoint_zone_low_fraction * rng,
        midpoint_zone_high=low + config.midpoint_zone_high_fraction * rng,
        efficiency_ratio=efficiency, close_location=location,
    )


def classify_session(levels: AsianLevels, config: StrategyConfig) -> str:
    """RANGE / BULLISH_TREND / BEARISH_TREND / UNCERTAIN."""
    if levels.efficiency_ratio <= config.efficiency_ratio_threshold + 1e-12:
        return "RANGE"
    bullish_floor = config.close_location_trend
    bearish_ceiling = 1.0 - config.close_location_trend
    if levels.close_location >= bullish_floor and levels.close > levels.open:
        return "BULLISH_TREND"
    if levels.close_location <= bearish_ceiling and levels.close < levels.open:
        return "BEARISH_TREND"
    return "UNCERTAIN"


# ------------------------------------------------------------------------ setups

def detect_sweep(candle: Candle, levels: AsianLevels, config: StrategyConfig) -> dict | None:
    """Liquidity taken beyond a boundary, then a close back inside."""
    sweep_buffer = config.sweep_buffer_fraction * levels.range
    quality = config.rejection_quality_fraction
    swept_low = (candle.open >= levels.low and candle.low < levels.low - sweep_buffer
                 and candle.close > levels.low)
    swept_high = (candle.open <= levels.high and candle.high > levels.high + sweep_buffer
                  and candle.close < levels.high)
    # A single candle taking both boundaries is directionally contradictory.
    if swept_low and swept_high:
        return None
    if swept_low:
        if candle.range and candle.close < candle.low + quality * candle.range:
            return None
        return {"setup": "SWEEP", "direction": "LONG", "extreme": candle.low,
                "codes": [Reason.SELL_SIDE_SWEEP, Reason.CLOSE_BACK_INSIDE]}
    if swept_high:
        if candle.range and candle.close > candle.high - quality * candle.range:
            return None
        return {"setup": "SWEEP", "direction": "SHORT", "extreme": candle.high,
                "codes": [Reason.BUY_SIDE_SWEEP, Reason.CLOSE_BACK_INSIDE]}
    return None


def detect_range_rejection(candle: Candle, levels: AsianLevels,
                           config: StrategyConfig) -> dict | None:
    """A boundary touch that is rejected. A convincing breakout close invalidates it."""
    tolerance = config.touch_tolerance_fraction * levels.range
    if candle.close < levels.low or candle.close > levels.high:
        return None
    if (candle.open >= levels.low and candle.low <= levels.low + tolerance
            and candle.close > levels.low and candle.bullish):
        return {"setup": "RANGE_REJECTION", "direction": "LONG", "extreme": candle.low,
                "codes": [Reason.BOUNDARY_REJECTION]}
    if (candle.open <= levels.high and candle.high >= levels.high - tolerance
            and candle.close < levels.high and candle.bearish):
        return {"setup": "RANGE_REJECTION", "direction": "SHORT", "extreme": candle.high,
                "codes": [Reason.BOUNDARY_REJECTION]}
    return None


def detect_trend_continuation(candle: Candle, session_type: str, levels: AsianLevels,
                              config: StrategyConfig) -> dict | None:
    """Confirmed 45–55% retracement that does not violate the opposite quartile."""
    touched = candle.low <= levels.midpoint_zone_high and candle.high >= levels.midpoint_zone_low
    if not touched:
        return None
    if (session_type == "BULLISH_TREND" and candle.bullish
            and candle.low >= levels.lower_quartile):
        return {"setup": "TREND_CONTINUATION", "direction": "LONG", "extreme": candle.low,
                "codes": [Reason.MIDPOINT_RETRACEMENT]}
    if (session_type == "BEARISH_TREND" and candle.bearish
            and candle.high <= levels.upper_quartile):
        return {"setup": "TREND_CONTINUATION", "direction": "SHORT", "extreme": candle.high,
                "codes": [Reason.MIDPOINT_RETRACEMENT]}
    return None


def trend_invalidated(candle: Candle, session_type: str, levels: AsianLevels) -> bool:
    """Trading through the opposite quartile cancels a pending trend setup."""
    if session_type == "BULLISH_TREND":
        return candle.low < levels.lower_quartile
    if session_type == "BEARISH_TREND":
        return candle.high > levels.upper_quartile
    return False


# ------------------------------------------------------------------------ helpers

def _aligned(value: float, tick: float) -> float:
    return round(value / tick) * tick


def _volume_floor(raw: float, step: float) -> float:
    return floor(raw / step + 1e-9) * step


# ----------------------------------------------------------------------- analyze

def analyze(
    *, config: StrategyConfig, symbol: str, trading_date: date, now: datetime,
    account: AccountSnapshot, spec: SymbolSpec, tick: dict[str, float],
    session_candles: list[Candle], execution_candles: list[Candle],
    one_lot_loss: callable, daily_used_cash: float, drawdown_percent: float,
    journal_healthy: bool, trades_taken_this_session: int = 0,
    account_identity_verified: bool = False,
    news_events: list[dict] | None = None, news_calendar_available: bool = True,
) -> AnalysisResult:
    now = now.astimezone(timezone.utc)
    asian_start, asian_end = session_bounds(trading_date, config)
    exec_start, exec_end = execution_bounds(trading_date, config)

    result = AnalysisResult(
        analysis_id=uuid4().hex[:12], timestamp_utc=now, trading_date=trading_date.isoformat(),
        symbol=symbol, account=account, bid=tick["bid"], ask=tick["ask"],
        spread=tick["ask"] - tick["bid"], strategy_id=config.strategy_id,
        contract_version=config.contract_version, config_hash=config.hash,
        config_snapshot=config.raw,
        asian_start=asian_start, asian_end=asian_end, expiry_utc=exec_end,
        partial_close_percent=config.partial_close_percent,
        risk_fraction=config.risk_percent_per_trade / 100,
    )
    result.session_candle_times = [c.time.isoformat().replace("+00:00", "Z") for c in session_candles]
    result.execution_candle_times = [c.time.isoformat().replace("+00:00", "Z") for c in execution_candles]

    # G1 environment ---------------------------------------------------------
    guard = config.account_guard
    demo_ok = account.account_type == "demo" or not guard.get("require_demo_account", True)
    server_ok = account.server == guard["required_server"]
    allowed = config.allowed_logins(include_environment=False)
    if account_identity_verified:
        login_ok, how = True, "exact allowlist (gateway verified)"
    elif allowed:
        masked = {("*" * max(0, len(str(x)) - 3)) + str(x)[-3:] for x in allowed}
        login_ok, how = account.login_masked in masked, "configured allowlist"
    elif guard.get("reject_suffix_only_matching"):
        login_ok, how = False, "no allowlist and suffix matching is rejected"
    else:
        login_ok = account.login_masked.endswith(str(guard["fallback_account_suffix"]))
        how = "suffix fallback (weak — set SSPF_ALLOWED_LOGINS)"
    environment_ok = demo_ok and server_ok and login_ok
    result.gates.append(Gate("G1_ENVIRONMENT", environment_ok,
                             f"account={account.account_type}, server={account.server}, "
                             f"login={account.login_masked} via {how}"))
    if environment_ok and not allowed and not account_identity_verified:
        result.warnings.append(
            "Account identity verified by three-digit suffix only. Different accounts can share a "
            "suffix; set SSPF_ALLOWED_LOGINS for an exact match.")
    if not environment_ok:
        result.add_reason(Reason.ENVIRONMENT_NOT_AUTHORIZED)
        if not login_ok and (allowed or account_identity_verified):
            result.add_reason(Reason.ACCOUNT_NOT_ALLOWLISTED)

    # G2 universe ------------------------------------------------------------
    supported = symbol in config.symbols
    result.gates.append(Gate("G2_UNIVERSE", supported, f"symbol={symbol}"))
    if not supported:
        result.add_reason(Reason.SYMBOL_NOT_SUPPORTED)
        return result

    # G3 broker clock --------------------------------------------------------
    clock_ok, offset, tick_age = calibrate_broker_tick(
        now, float(tick.get("time", 0)),
        int(tick["broker_offset_hours"]) if "broker_offset_hours" in tick else None)
    result.broker_utc_offset_hours = offset if clock_ok else None
    fresh = clock_ok and -5 <= tick_age <= config.maximum_tick_age_seconds
    result.gates.append(Gate("G3_BROKER_CLOCK", fresh,
                             f"verified UTC{offset:+d}:00, normalized tick age={tick_age:.0f}s"
                             if clock_ok else "broker timestamp outside valid UTC offsets"))
    if not fresh:
        result.add_reason(Reason.BROKER_CLOCK_UNVERIFIED)

    # G4 session data --------------------------------------------------------
    session_ok, session_detail = validate_candles(
        session_candles, asian_start, config.session_candles, config, now=now)
    exec_ok, exec_detail = validate_candles(
        execution_candles, exec_start, config.post_session_candles, config,
        minimum_count=0, now=now)
    data_ok = session_ok and exec_ok and result.spread > 0
    detail = session_detail if session_ok else session_detail
    if not exec_ok:
        detail = f"execution window: {exec_detail}"
    elif result.spread <= 0:
        detail = "non-positive spread"
    result.gates.append(Gate("G4_SESSION_DATA", data_ok, detail))
    if not data_ok:
        result.add_reason(Reason.INVALID_ASIAN_DATA)
        return result
    if not fresh:
        return result

    # levels are locked here and never recomputed -----------------------------
    levels = lock_asian_levels(session_candles, config)
    limits = config.symbols[symbol]
    result.asian_high, result.asian_low, result.asian_range = levels.high, levels.low, levels.range
    result.midpoint, result.asian_open, result.asian_close = levels.midpoint, levels.open, levels.close
    result.risk_unit = levels.risk_unit
    result.lower_quartile, result.upper_quartile = levels.lower_quartile, levels.upper_quartile
    result.efficiency_ratio, result.close_location = levels.efficiency_ratio, levels.close_location

    # G5 range bounds --------------------------------------------------------
    range_ok = levels.range > 0 and limits.minimum_range <= levels.range <= limits.maximum_range
    result.gates.append(Gate("G5_RANGE_BOUNDS", range_ok,
                             f"range={levels.range:.10g}, allowed=[{limits.minimum_range:.10g}, {limits.maximum_range:.10g}]"))
    if not range_ok:
        result.add_reason(Reason.INVALID_ASIAN_RANGE)
        return result

    # G6 spread --------------------------------------------------------------
    spread_ok = result.spread <= limits.maximum_spread
    result.gates.append(Gate("G6_SPREAD", spread_ok,
                             f"spread={result.spread:.10g}, maximum={limits.maximum_spread:.10g}"))
    if not spread_ok:
        result.add_reason(Reason.EXCESSIVE_SPREAD)

    # G7 classification ------------------------------------------------------
    result.session_type = classify_session(levels, config)
    if result.session_type == "BULLISH_TREND":
        result.directional_bias = "BULLISH"
    elif result.session_type == "BEARISH_TREND":
        result.directional_bias = "BEARISH"
    else:
        # The pure engine receives only the locked reference and execution bars.
        # For Range evidence, use the close's half-range location as the explicit
        # deterministic fallback; the historical engine can additionally report
        # its wider pre-London swing-structure bias.
        result.directional_bias = "BULLISH" if levels.close_location >= 0.5 else "BEARISH"
    classified = result.session_type != "UNCERTAIN"
    result.gates.append(Gate("G7_SESSION_CLASSIFIED", classified,
                             f"type={result.session_type}, ER={levels.efficiency_ratio:.4f}, "
                             f"close_location={levels.close_location:.4f}"))
    if not classified:
        result.add_reason(Reason.UNCERTAIN_SESSION_TYPE)
        return result
    result.add_reason(Reason.RANGE_SESSION if result.session_type == "RANGE" else Reason.TREND_SESSION)

    # G8 one trade per symbol per session ------------------------------------
    quota_ok = trades_taken_this_session < config.maximum_trades_per_symbol_session
    result.gates.append(Gate("G8_SESSION_QUOTA", quota_ok,
                             f"taken={trades_taken_this_session}, allowed={config.maximum_trades_per_symbol_session}"))
    if not quota_ok:
        result.add_reason(Reason.TRADE_ALREADY_TAKEN)
        result.add_reason(Reason.MAX_SESSION_TRADES_EXCEEDED)
        return result

    # G9 news calendar -------------------------------------------------------
    news = config.news_filter
    news_ok, news_detail = True, "filter disabled"
    if news.get("enabled"):
        if not news_calendar_available:
            news_ok, news_detail = False, "local high-impact calendar unavailable"
            result.add_reason(Reason.NEWS_CALENDAR_UNAVAILABLE)
        else:
            before = timedelta(minutes=float(news["minutes_before"]))
            after = timedelta(minutes=float(news["minutes_after"]))
            currencies = set(news.get("symbol_currencies", {}).get(symbol, []))
            conflicts = []
            for event in news_events or []:
                if str(event.get("impact", "")).upper() != "HIGH":
                    continue
                if currencies and str(event.get("currency", "")).upper() not in currencies:
                    continue
                event_time = event.get("time_utc")
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                if event_time is not None and event_time - before <= now <= event_time + after:
                    conflicts.append(event)
            if conflicts:
                news_ok = False
                news_detail = f"{len(conflicts)} relevant high-impact event(s) within blocked window"
                result.add_reason(Reason.HIGH_IMPACT_NEWS_WINDOW)
            else:
                news_detail = "no relevant high-impact event in blocked window"
    result.gates.append(Gate("G9_NEWS_FILTER", news_ok, news_detail))
    if not news_ok:
        return result

    # setup detection, in configured priority order, over closed execution candles
    detectors = {
        "SWEEP": lambda c: detect_sweep(c, levels, config),
        "RANGE_REJECTION": lambda c: detect_range_rejection(c, levels, config),
        "TREND_CONTINUATION": lambda c: detect_trend_continuation(c, result.session_type, levels, config),
    }
    signal, signal_candle = None, None
    for candle in execution_candles:
        if trend_invalidated(candle, result.session_type, levels):
            result.warnings.append(
                f"Trend setup cancelled: {candle.time.isoformat()} violated the opposite quartile")
            break
        for name in config.setup_priority:
            rule = config.setup_rules.get(name)
            if rule is None or not rule.enabled or result.session_type not in rule.session_types:
                continue
            found = detectors[name](candle)
            if found:
                signal, signal_candle = found, candle
                break
        if signal:
            break

    setup_found = signal is not None
    result.gates.append(Gate("G10_SETUP_DETECTED", setup_found,
                             f"setup={signal['setup']} {signal['direction']}" if setup_found
                             else f"no qualifying setup in {len(execution_candles)} closed execution candle(s)"))
    if not setup_found:
        result.add_reason(Reason.EXECUTION_WINDOW_EXPIRED if len(execution_candles) >= config.post_session_candles
                          else Reason.NO_QUALIFYING_SETUP)
        return result

    for code in signal["codes"]:
        result.add_reason(code)
    result.setup, result.direction = signal["setup"], signal["direction"]
    result.signal_time = signal_candle.time
    result.signal_candle = {"time": signal_candle.time.isoformat().replace("+00:00", "Z"),
                            "open": signal_candle.open, "high": signal_candle.high,
                            "low": signal_candle.low, "close": signal_candle.close}

    long_side = result.direction == "LONG"
    if result.setup == "SWEEP":
        # Enter at the near edge of the sweep candle's real body.
        entry = min(signal_candle.open, signal_candle.close) if long_side else max(signal_candle.open, signal_candle.close)
    elif result.setup == "RANGE_REJECTION":
        entry = levels.low if long_side else levels.high
    else:  # TREND_CONTINUATION
        entry = levels.midpoint
    result.entry = _aligned(entry, spec.tick_size)
    raw_stop = result.entry - levels.risk_unit if long_side else result.entry + levels.risk_unit
    result.stop_loss = _aligned(raw_stop, spec.tick_size)
    result.initial_risk = abs(result.entry - result.stop_loss)
    sign = 1 if long_side else -1
    if result.setup in {"SWEEP", "RANGE_REJECTION"}:
        result.partial_target = _aligned(levels.high if long_side else levels.low, spec.tick_size)
        result.partial_target_label = "opposite session boundary"
        result.runner_management = "MOVE_STOP_TO_BREAKEVEN"
    else:
        result.partial_target = _aligned(result.entry + sign * config.partial_target_r * result.initial_risk, spec.tick_size)
        result.partial_target_label = f"{config.partial_target_r:g}R"
        result.runner_management = "MOVE_STOP_TO_BREAKEVEN; RUNNER_TARGET_5R"
    # Retained as a compatibility alias for existing journal/artifact consumers.
    result.tp1_4r = result.partial_target
    result.tp2_5r = _aligned(result.entry + sign * config.final_target_r * result.initial_risk, spec.tick_size)

    # G11 structural stop (sweeps only) --------------------------------------
    if result.setup == "SWEEP":
        buffer = config.stop_buffer_fraction * levels.range
        required = signal["extreme"] - buffer if long_side else signal["extreme"] + buffer
        structural_ok = (result.stop_loss < required if long_side else result.stop_loss > required)
        detail = (f"stop={result.stop_loss:.10g}, must be beyond {required:.10g} "
                  f"(sweep extreme {signal['extreme']:.10g}, buffer {buffer:.10g})")
        if not structural_ok:
            detail = f"{Reason.FIXED_STOP_NOT_BEYOND_SWEEP}: " + detail
            result.warnings.append(
                "The fixed 25%-of-range stop does not clear the sweep extreme. Widening it would "
                "break the fixed risk rule, so the signal is rejected.")
    else:
        structural_ok, detail = True, "not applicable to this setup"
    result.gates.append(Gate("G11_STRUCTURAL_STOP", structural_ok, detail))
    if not structural_ok:
        result.add_reason(Reason.FIXED_STOP_NOT_BEYOND_SWEEP)
        return result
    if result.setup == "SWEEP":
        result.add_reason(Reason.STRUCTURAL_STOP_VALID)

    # G12 broker stop distance ------------------------------------------------
    stops_ok = result.initial_risk + spec.tick_size / 2 >= spec.stops_level_price
    result.gates.append(Gate("G12_STOPS_LEVEL", stops_ok,
                             f"distance={result.initial_risk:.10g}, broker minimum={spec.stops_level_price:.10g}"))
    if not stops_ok:
        result.add_reason(Reason.BROKER_STOP_DISTANCE)

    # G13 volume --------------------------------------------------------------
    risk_basis = min(account.balance, account.equity)
    result.risk_basis_cash = risk_basis
    daily_limit = risk_basis * config.daily_risk_limit_percent / 100
    intended = min(risk_basis * config.risk_percent_per_trade / 100,
                   max(0.0, daily_limit - daily_used_cash))
    result.intended_risk_cash = intended
    loss_one = one_lot_loss(symbol, "BUY" if long_side else "SELL", result.entry, result.stop_loss)
    volume_ok = loss_one is not None and loss_one > 0 and intended > 0
    if volume_ok:
        result.volume = round(_volume_floor(intended / loss_one, spec.volume_step), 8)
        volume_ok = spec.volume_min <= result.volume <= spec.volume_max
        if volume_ok:
            result.actual_risk_cash = loss_one * result.volume
            result.actual_risk_percent = result.actual_risk_cash / risk_basis * 100
    result.gates.append(Gate("G13_VOLUME_BOUNDS", volume_ok,
                             f"volume={result.volume}, allowed=[{spec.volume_min}, {spec.volume_max}]"
                             if volume_ok else "profit calculation or normalized volume invalid"))
    if not volume_ok:
        result.add_reason(Reason.VOLUME_OUT_OF_BOUNDS)

    # The runner must be a tradeable size, or the two-stage exit is not executable.
    if volume_ok and result.volume:
        remainder = _volume_floor(result.volume * (1 - config.partial_close_percent / 100),
                                  spec.volume_step)
        result.partial_volume = round(result.volume - remainder, 8)
        result.runner_volume = round(remainder, 8)
        if remainder < spec.volume_min:
            result.runner_below_minimum = True
            result.add_reason(Reason.RUNNER_BELOW_MINIMUM_VOLUME)
            result.warnings.append(
                f"The {100 - config.partial_close_percent:.0f}% runner ({remainder:g} lots) is below the "
                f"broker minimum ({spec.volume_min:g}). Policy "
                f"{config.management['remainder_below_minimum_volume_policy']}: close the full position "
                f"at TP1 instead of scaling out.")

    # Transaction costs — a 5R target is not 5R after spread, commission and slippage.
    if result.initial_risk and result.volume:
        slip = config.slippage_points() * spec.point
        cost_price = result.spread + 2 * slip
        result.estimated_cost_r = cost_price / result.initial_risk
        commission = config.cost_per_lot_round_turn() * result.volume
        if result.actual_risk_cash:
            result.estimated_cost_r += commission / result.actual_risk_cash
        result.gross_tp2_r = config.final_target_r
        result.net_tp2_r = config.final_target_r - result.estimated_cost_r
        partial_r = abs(result.partial_target - result.entry) / result.initial_risk
        result.net_tp1_r = partial_r - result.estimated_cost_r
        if not config.cost_model.get("cost_model_signed_off"):
            result.warnings.append(
                "Cost model is not signed off: commission and slippage default to zero, so net R is "
                "spread-only and optimistic. Stage 2 requires signed-off values.")

    # G14 daily risk ----------------------------------------------------------
    proposed = result.actual_risk_cash if result.actual_risk_cash is not None else intended
    daily_ok = journal_healthy and daily_used_cash + proposed <= daily_limit + 1e-9
    result.gates.append(Gate("G14_DAILY_RISK", daily_ok,
                             f"used+proposed={daily_used_cash + proposed:.2f}, limit={daily_limit:.2f}"
                             if journal_healthy else "journal sync unhealthy"))
    if not daily_ok:
        result.add_reason(Reason.DAILY_RISK_EXCEEDED)

    # G15 drawdown ------------------------------------------------------------
    drawdown_ok = journal_healthy and drawdown_percent < config.maximum_drawdown_percent
    result.gates.append(Gate("G15_DRAWDOWN", drawdown_ok,
                             f"drawdown={drawdown_percent:.2f}%, maximum={config.maximum_drawdown_percent:.2f}%"
                             if journal_healthy else "journal sync unhealthy"))
    if not drawdown_ok:
        result.add_reason(Reason.DRAWDOWN_EXCEEDED)

    # G16 execution window ----------------------------------------------------
    window_ok = exec_start <= now < exec_end
    result.gates.append(Gate("G16_EXECUTION_WINDOW", window_ok,
                             f"now={now.isoformat()}, window=[{exec_start.isoformat()}, {exec_end.isoformat()})"))
    if not window_ok:
        result.add_reason(Reason.OUTSIDE_EXECUTION_WINDOW)
    return result

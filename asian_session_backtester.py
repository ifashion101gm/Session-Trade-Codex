"""Deterministic session-strategy benchmark (read-only; no MT5 trade calls).

Authoritative strategy contract: ``STRATEGY_TRUTH_SOURCE.md``.

Input is an approved GMT+2/+3 MT5 terminal or a UTC CSV with columns:
time,open,high,low,close,spread. ``spread`` is in broker points.
Decisions use closed M15 bars; ambiguous same-bar stop/target collisions are STOP_FIRST.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

PIP = 0.0001
POINT = 0.00001
START, END = date(2022, 10, 1), date(2022, 10, 22)
MAX_TRADES_PER_SESSION = 3
MINIMUM_ASIAN_RANGE_PIPS = 10.0
POST_LOSS_COOLDOWN_BARS = 4
MAX_SESSION_LOSS_R = -2.0
MOMENTUM_BODY_MULTIPLIER = 1.5
MINIMUM_SWEEP_WICK_RATIO = 0.35
MINIMUM_BOUNDARY_PIERCE_PIPS = 1.0
RANGE_EFFICIENCY_RATIO_MAX = 0.35
TREND_CLOSE_LOCATION_MIN = 0.65
TREND_ZONE_LOW_FRACTION = 0.45
TREND_ZONE_HIGH_FRACTION = 0.55
WIDE_RANGE_THRESHOLD_PIPS = 40.0
WIDE_RANGE_STOP_BUFFER_PIPS = 3.0
# Hour offsets are relative to the trading date's midnight. The Asian box
# therefore starts at 22:00 on the prior calendar day and ends at 07:00.
SESSION_CYCLES = {"asian": (-2, 7), "london": (7, 12)}


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    spread_points: int | None


def trading_days(start: date = START, end: date = END) -> list[date]:
    return [start + timedelta(days=i) for i in range((end-start).days+1)
            if (start + timedelta(days=i)).weekday() < 5]


def load_csv(path: Path) -> list[Bar]:
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            stamp = datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("CSV timestamps must include UTC offsets")
            rows.append(Bar(stamp.astimezone(timezone.utc), *(float(row[x]) for x in
                        ("open", "high", "low", "close")),
                        int(row["spread"]) if row.get("spread") not in (None, "") else None))
    return sorted(rows, key=lambda x: x.time)


def load_mt5(server_offset: int, symbol: str = "EURUSD",
             start_day: date = START, end_day: date = END) -> tuple[list[Bar], str]:
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        source = " / ".join(str(x) for x in (getattr(account, "company", ""),
                                               getattr(account, "server", "")) if x)
        approved = ("eightcap", "vt markets", "vtmarkets", "vantage")
        if not any(name in source.lower() for name in approved):
            raise RuntimeError(
                f"SOURCE_MISMATCH: approved sources are Eightcap/VT Markets/Vantage, connected to {source!r}")
        if server_offset not in (2, 3):
            raise RuntimeError("SERVER_OFFSET_INVALID: New York-close MT5 history requires GMT+2 or GMT+3")
        shift = timedelta(hours=server_offset)
        begin = datetime.combine(start_day-timedelta(days=2), time.min, timezone.utc) + shift
        finish = datetime.combine(end_day+timedelta(days=2), time.min, timezone.utc) + shift
        data = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, begin, finish)
        if data is None:
            raise RuntimeError(f"{symbol} M15 unavailable: {mt5.last_error()}")
        bars = [Bar(datetime.fromtimestamp(int(x["time"]), timezone.utc)-shift,
                    float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"]),
                    int(x["spread"])) for x in data]
        return bars, source
    finally:
        mt5.shutdown()


def classify(session: list[Bar], high: float, low: float, bias: str = "NEUTRAL") -> str:
    """Classify from net open-to-close displacement divided by session range."""
    width = high-low
    if width <= 0 or not session:
        return "INVALID"
    opened, closed = session[0].open, session[-1].close
    efficiency = abs(closed-opened)/width
    close_location = (closed-low)/width
    if efficiency <= RANGE_EFFICIENCY_RATIO_MAX + 1e-12:
        return "RANGE"
    if (close_location >= TREND_CLOSE_LOCATION_MIN and closed > opened):
        return "BULLISH_TREND"
    if (close_location <= 1.0-TREND_CLOSE_LOCATION_MIN and closed < opened):
        return "BEARISH_TREND"
    return "UNCERTAIN"


def directional_bias(session: list[Bar]) -> str:
    return "BULLISH" if session[-1].close >= session[0].open else "BEARISH"


def daily_bias(bars: list[Bar], cutoff: datetime) -> str:
    """Return a mandatory bullish/bearish bias using only closed M15 bars."""
    structure = m15_structure_bias(bars, cutoff)
    if structure in {"BULLISH", "BEARISH"}:
        return structure
    recent = [bar for bar in bars if bar.time+timedelta(minutes=15) <= cutoff][-32:]
    if not recent:
        return "NEUTRAL"
    midpoint = sum(bar.close for bar in recent) / len(recent)
    return "BULLISH" if recent[-1].close >= midpoint else "BEARISH"


def daily_bias_cutoff(day_start: datetime) -> datetime:
    """Freeze the source-workflow daily bias before London execution begins.

    The flowchart determines one bias for the trading day.  New York therefore
    inherits the 07:00 UTC decision instead of recalculating it from the London
    move and potentially reversing direction mid-day.
    """
    return day_start + timedelta(hours=SESSION_CYCLES["asian"][1])


def m15_structure_bias(bars: list[Bar], cutoff: datetime) -> str:
    """Optional M15 bias from confirmed swings in the last 48 closed bars."""
    recent = [bar for bar in bars if bar.time + timedelta(minutes=15) <= cutoff][-48:]
    if len(recent) < 5:
        return "NEUTRAL"
    swing_highs = [recent[i].high for i in range(1, len(recent)-1)
                   if recent[i].high > recent[i-1].high and recent[i].high > recent[i+1].high]
    swing_lows = [recent[i].low for i in range(1, len(recent)-1)
                  if recent[i].low < recent[i-1].low and recent[i].low < recent[i+1].low]
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "NEUTRAL"
    recent_highs, recent_lows = swing_highs[-4:], swing_lows[-4:]
    high_score = sum(1 if right > left else -1 if right < left else 0
                     for left, right in zip(recent_highs, recent_highs[1:]))
    low_score = sum(1 if right > left else -1 if right < left else 0
                    for left, right in zip(recent_lows, recent_lows[1:]))
    if ((high_score == 3 and low_score >= 1) or
            (low_score == 3 and high_score >= 1)):
        return "BULLISH"
    if ((high_score == -3 and low_score <= -1) or
            (low_score == -3 and high_score <= -1)):
        return "BEARISH"
    if swing_highs[-2] < swing_highs[-1] and swing_lows[-2] < swing_lows[-1]:
        return "BULLISH"
    if swing_highs[-2] > swing_highs[-1] and swing_lows[-2] > swing_lows[-1]:
        return "BEARISH"
    return "NEUTRAL"


def signal_for(kind: str, bars: list[Bar], high: float, low: float,
               asian_close: float, entry_mode: str = "body",
               wide_range_handling: bool = False, bias: str = "NEUTRAL",
               allow_range_setup: bool = True):
    width = high-low
    mid = (high+low)/2
    midpoint_zone_low = low + TREND_ZONE_LOW_FRACTION*width
    midpoint_zone_high = low + TREND_ZONE_HIGH_FRACTION*width
    lower_quartile = low + .25*width
    upper_quartile = high - .25*width
    sweep_observed = False
    for i, bar in enumerate(bars):
        # Require a material liquidity breach in every execution mode. A zero
        # body-mode threshold promoted sub-pip quote noise to Sweep and could
        # incorrectly displace the causal Range branch.
        pierce = MINIMUM_BOUNDARY_PIERCE_PIPS * PIP
        candle_range = bar.high-bar.low
        upper_wick_ratio = ((bar.high-max(bar.open, bar.close))/candle_range
                            if candle_range else 0.0)
        lower_wick_ratio = ((min(bar.open, bar.close)-bar.low)/candle_range
                            if candle_range else 0.0)
        # A boundary breach is a sweep only after the M15 candle reclaims the
        # box and leaves a directional wick. A close outside is continuation /
        # breakout, even on wide ranges. This prevents a large expansion body
        # with only a token wick from being mislabeled as liquidity rejection.
        raw_low_reclaim = (bar.open >= low and bar.low <= low-pierce and
                           bar.close > low)
        raw_high_reclaim = (bar.open <= high and bar.high >= high+pierce and
                            bar.close < high)
        # The source rule is breach + close back inside.  The 35% wick test is
        # confirmation, not an absolute veto: an aligned reversal body also
        # confirms the reclaim.  Once any reclaim occurs, Sweep retains branch
        # precedence and the engine must not downgrade a later bar to Range.
        low_sweep = (raw_low_reclaim and
                     (lower_wick_ratio > MINIMUM_SWEEP_WICK_RATIO or
                      bar.close > bar.open))
        high_sweep = (raw_high_reclaim and
                      (upper_wick_ratio > MINIMUM_SWEEP_WICK_RATIO or
                       bar.close < bar.open))
        sweep_observed = sweep_observed or raw_low_reclaim or raw_high_reclaim
        close_sweep_low = bar.low < asian_close and bar.open >= asian_close and bar.close > asian_close
        close_sweep_high = bar.high > asian_close and bar.open <= asian_close and bar.close < asian_close
        if kind == "RANGE":
            if low_sweep != high_sweep:
                direction = "LONG" if low_sweep else "SHORT"
                # Sweep direction comes from the boundary that was reclaimed,
                # not from daily bias. Bias remains context and still controls
                # Range/Trend direction, but it is not a Sweep-entry veto.
                entry = (min(bar.open, bar.close) if direction == "LONG" else
                         max(bar.open, bar.close))
                return i, "SWEEP", direction, entry
            # A reclaimed boundary with an insufficient rejection wick is an
            # unconfirmed sweep candidate, not a Range entry on the same bar.
            # Wait for a later closed candle to provide valid confirmation.
            if sweep_observed:
                continue
            # No confirmed sweep: a Range entry requires rejection at the
            # favorable boundary, not a continuation close through the box.
            if not allow_range_setup:
                continue
            touches_low, touches_high = bar.low <= low, bar.high >= high
            if touches_low != touches_high and bias in {"BULLISH", "BEARISH"}:
                bullish_rejection = (bias == "BULLISH" and touches_low and
                                     bar.close > low and bar.close > bar.open)
                bearish_rejection = (bias == "BEARISH" and touches_high and
                                     bar.close < high and bar.close < bar.open)
                if bullish_rejection or bearish_rejection:
                    entry = low if bullish_rejection else high
                    direction = "LONG" if bullish_rejection else "SHORT"
                    return i, "RANGE", direction, entry
        elif kind == "BULLISH_TREND":
            if bar.low < lower_quartile:
                return None
            touched_zone = (bar.low <= midpoint_zone_high and
                            bar.high >= midpoint_zone_low)
            if touched_zone and bar.close > bar.open:
                return i, "TREND", "LONG", mid
        elif kind == "BEARISH_TREND":
            if bar.high > upper_quartile:
                return None
            touched_zone = (bar.low <= midpoint_zone_high and
                            bar.high >= midpoint_zone_low)
            if touched_zone and bar.close < bar.open:
                return i, "TREND", "SHORT", mid
    return None


def developing_session_sweep(bars: list[Bar], minimum_prior_bars: int = 4):
    """Return the last causal sweep formed inside a developing session.

    Each candidate is judged only against highs/lows completed before its own
    candle.  This supports a London sweep that is already known when the London
    box freezes at 12:00, without using any New York or future London bars.
    """
    candidate = None
    pierce = MINIMUM_BOUNDARY_PIERCE_PIPS * PIP
    for index in range(minimum_prior_bars, len(bars)):
        bar = bars[index]
        prior = bars[:index]
        prior_high = max(item.high for item in prior)
        prior_low = min(item.low for item in prior)
        candle_range = bar.high-bar.low
        if candle_range <= 0:
            continue
        upper_wick_ratio = (bar.high-max(bar.open, bar.close))/candle_range
        lower_wick_ratio = (min(bar.open, bar.close)-bar.low)/candle_range
        low_reclaim = (bar.open >= prior_low and bar.low <= prior_low-pierce and
                       bar.close > prior_low and
                       (lower_wick_ratio > MINIMUM_SWEEP_WICK_RATIO or
                        bar.close > bar.open))
        high_reclaim = (bar.open <= prior_high and bar.high >= prior_high+pierce and
                        bar.close < prior_high and
                        (upper_wick_ratio > MINIMUM_SWEEP_WICK_RATIO or
                         bar.close < bar.open))
        if low_reclaim != high_reclaim:
            direction = "LONG" if low_reclaim else "SHORT"
            entry = (min(bar.open, bar.close) if direction == "LONG" else
                     max(bar.open, bar.close))
            candidate = index, "SWEEP", direction, entry
    return candidate


def modeled_spread_pips(stamp: datetime) -> float:
    """Deterministic fallback curve for archived bars with no spread history.

    07:00 and 12:00 transition bars use 1.0 pip. During 08:00-16:59 UTC,
    spread is 0.4 at 10:00 and widens linearly to 0.7 at the active-window
    edges. Other hours use the 1.2-pip off-hours assumption.
    """
    hour = stamp.hour + stamp.minute / 60
    if stamp.hour in (7, 12) and stamp.minute == 0:
        return 1.0
    if 7 < hour < 17:
        distance = min(abs(hour - 10), 3.0) / 3.0
        return 0.4 + 0.3 * distance
    return 1.2


def opposing_expansion(signal_bar: Bar, direction: str,
                        prior_bars: list[Bar]) -> tuple[bool, float, float, float, float]:
    """Wick-qualified sweep gate with body diagnostics from prior closed bars.

    A short requires an upper wick above 35% of its real body; a long
    requires the mirrored lower wick. This lets a genuine rejection wick pass
    even when the candle body is an expansion relative to prior bars.
    """
    bodies = [abs(bar.close - bar.open) for bar in prior_bars]
    average_body = sum(bodies) / len(bodies) if bodies else 0.0
    signal_body = abs(signal_bar.close - signal_bar.open)
    opposing = ((direction == "LONG" and signal_bar.close < signal_bar.open) or
                (direction == "SHORT" and signal_bar.close > signal_bar.open))
    upper_wick = signal_bar.high - max(signal_bar.open, signal_bar.close)
    lower_wick = min(signal_bar.open, signal_bar.close) - signal_bar.low
    upper_wick_ratio = upper_wick / signal_body if signal_body > 0 else float("inf")
    lower_wick_ratio = lower_wick / signal_body if signal_body > 0 else float("inf")
    required_wick = lower_wick_ratio if direction == "LONG" else upper_wick_ratio
    rejected = (opposing and signal_body > MOMENTUM_BODY_MULTIPLIER * average_body
                and required_wick <= MINIMUM_SWEEP_WICK_RATIO)
    return rejected, signal_body, average_body, upper_wick_ratio, lower_wick_ratio


def simulate(trade: dict, bars: list[Bar], slippage_pips: float,
             confirmed_limit_fill: Bar | None = None) -> dict:
    long_side = trade["direction"] == "LONG"
    entry, stop, partial, target = (trade[x] for x in ("entry", "stop", "partial", "target"))
    risk, filled, partial_hit = abs(entry-stop), confirmed_limit_fill is not None, False
    spread_r = None
    slippage_r = slippage_pips * PIP / risk
    if confirmed_limit_fill is not None:
        recorded = (confirmed_limit_fill.spread_points or 0) * POINT
        fallback = modeled_spread_pips(confirmed_limit_fill.time)
        spread = recorded if recorded > 0 else fallback * PIP
        spread_source = "HISTORICAL_BAR" if recorded > 0 else "DYNAMIC_INTRADAY_MODEL"
        if spread > .20*risk:
            return {"outcome":"REJECTED_SPREAD_GATE", "r":None,
                    "spread_pips":spread/PIP, "spread_source":spread_source,
                    "exit_bar_index":0,
                    "exit_time":confirmed_limit_fill.time.isoformat().replace("+00:00", "Z")}
        spread_r = spread/risk
        trade["spread_pips"], trade["spread_source"] = spread/PIP, spread_source
        trade["entry_time"] = confirmed_limit_fill.time.isoformat().replace("+00:00", "Z")
        trade["entry_bar_index"] = -1
    for bar_index, bar in enumerate(bars):
        if not filled:
            touched = bar.low <= entry <= bar.high
            if not touched:
                continue
            recorded = (bar.spread_points or 0) * POINT
            fallback = modeled_spread_pips(bar.time)
            spread = recorded if recorded > 0 else fallback * PIP
            spread_source = "HISTORICAL_BAR" if recorded > 0 else "DYNAMIC_INTRADAY_MODEL"
            if spread > .20*risk:
                return {"outcome":"REJECTED_SPREAD_GATE", "r":None,
                        "spread_pips":spread/PIP, "spread_source":spread_source,
                        "exit_bar_index":bar_index,
                        "exit_time":bar.time.isoformat().replace("+00:00", "Z")}
            spread_r, filled = spread/risk, True
            trade["spread_pips"] = spread/PIP
            trade["spread_source"] = spread_source
            trade["entry_time"] = bar.time.isoformat().replace("+00:00", "Z")
            trade["entry_bar_index"] = bar_index
        active_stop = entry if partial_hit else stop
        stopped = bar.low <= active_stop if long_side else bar.high >= active_stop
        hit_partial = bar.high >= partial if long_side else bar.low <= partial
        hit_target = bar.high >= target if long_side else bar.low <= target
        if stopped:
            gross = .75*trade["partial_r"] if partial_hit else -1.0
            return {"outcome":"PARTIAL_THEN_BE" if partial_hit else "STOP_LOSS",
                    "r":gross-spread_r, "friction_r":gross-spread_r-slippage_r,
                    "gross_r":gross, "spread_r":spread_r, "slippage_r":slippage_r,
                    "leg_a_r":trade["partial_r"] if partial_hit else -1.0,
                    "leg_b_r":0.0 if partial_hit else -1.0,
                    "breakeven_activated":partial_hit,
                    "gross_pips":gross*risk/PIP, "exit_bar_index":bar_index,
                    "exit_time":bar.time.isoformat().replace("+00:00", "Z")}
        if not partial_hit and hit_partial:
            partial_hit = True
        if hit_target:
            gross = .75*trade["partial_r"]+1.25
            return {"outcome":"TP5_HIT", "r":gross-spread_r,
                    "friction_r":gross-spread_r-slippage_r, "gross_r":gross,
                    "spread_r":spread_r, "slippage_r":slippage_r,
                    "leg_a_r":trade["partial_r"], "leg_b_r":5.0,
                    "breakeven_activated":True,
                    "profit_pips":5*risk/PIP, "gross_pips":gross*risk/PIP,
                    "exit_bar_index":bar_index,
                    "exit_time":bar.time.isoformat().replace("+00:00", "Z")}
    if not filled:
        return {"outcome":"UNFILLED", "r":None}
    last = bars[-1].close
    runner_r = ((last-entry) if long_side else (entry-last))/risk
    gross = .75*trade["partial_r"]+.25*runner_r if partial_hit else runner_r
    return {"outcome":"END_WINDOW", "r":gross-spread_r,
            "friction_r":gross-spread_r-slippage_r, "gross_r":gross,
            "spread_r":spread_r, "slippage_r":slippage_r,
            "leg_a_r":trade["partial_r"] if partial_hit else runner_r,
            "leg_b_r":runner_r, "breakeven_activated":partial_hit,
            "gross_pips":gross*risk/PIP, "exit_bar_index":len(bars)-1,
            "exit_time":bars[-1].time.isoformat().replace("+00:00", "Z")}


def run(bars: list[Bar], source: str, slippage_pips: float = 0.2,
        evaluation_days: list[date] | None = None, execution_end_hour: int = 20,
        disable_momentum_filter: bool = False,
        entry_end_hour: int = 16, m15_bias_filter: bool = False,
        entry_mode: str = "body", symbol: str = "EURUSD",
        wide_range_buffer: bool = False,
        reference_session: str = "asian") -> dict:
    sessions, trades = [], []
    generated_signals = 0
    total_cooldown_bars_skipped = 0
    selected_days = evaluation_days or trading_days()
    reference_start_hour, reference_end_hour = SESSION_CYCLES[reference_session]
    for day in selected_days:
        start = datetime.combine(day, time(0), timezone.utc)
        reference = [x for x in bars if start+timedelta(hours=reference_start_hour) <= x.time <
                     start+timedelta(hours=reference_end_hour)]
        execution = [x for x in bars if start+timedelta(hours=reference_end_hour) <= x.time <
                     start+timedelta(hours=execution_end_hour)]
        required_reference = (reference_end_hour-reference_start_hour)*4
        required_execution = (execution_end_hour-reference_end_hour)*4
        # A New-York-close broker may have no 21:00-22:00 UTC Friday bars.
        minimum_execution = required_execution - (4 if day.weekday() == 4 else 0)
        if len(reference) != required_reference or not minimum_execution <= len(execution) <= required_execution:
            sessions.append({"date":str(day), "status":"REJECTED_DATA_QUALITY",
                             "reference_session":reference_session.upper(),
                             "reference_bars":len(reference), "execution_bars":len(execution),
                             "trades":[]})
            continue
        high, low = max(x.high for x in reference), min(x.low for x in reference)
        width = high-low
        if width < MINIMUM_ASIAN_RANGE_PIPS*PIP:
            sessions.append({"date":str(day), "status":"REJECTED_TIGHT_RANGE",
                             "reference_session":reference_session.upper(),
                             "reference_range_pips":width/PIP, "trades":[]})
            continue
        cutoff = start+timedelta(hours=reference_end_hour)
        bias_cutoff = daily_bias_cutoff(start)
        structure_bias = m15_structure_bias(
            [x for x in bars if bias_cutoff-timedelta(hours=12) <= x.time < bias_cutoff],
            bias_cutoff)
        bias_history = [x for x in bars if start-timedelta(hours=12) <= x.time <
                        bias_cutoff]
        bias = daily_bias(bias_history, bias_cutoff)
        session_type = classify(reference, high, low, bias)
        wide_range_handling = False
        signal_bar_limit = min(len(execution), max(0, (entry_end_hour-reference_end_hour)*4))
        day_trades, cursor, executed = [], 0, 0
        session_realized_r = 0.0
        cooldown_until_bar_index = 0
        last_loss_timestamp = None
        circuit_breaker = None
        session_cooldown_bars_skipped = 0
        used_range_boundaries: set[float] = set()
        sweep_branch_selected = False
        carried_reference_sweep = (developing_session_sweep(reference)
                                   if reference_session == "london" and
                                   session_type == "RANGE" else None)
        carried_reference_sweep_used = False
        while cursor < signal_bar_limit and executed < MAX_TRADES_PER_SESSION:
            if circuit_breaker:
                break
            resume_cursor = max(cursor, cooldown_until_bar_index)
            skipped = max(0, resume_cursor - cursor)
            session_cooldown_bars_skipped += skipped
            total_cooldown_bars_skipped += skipped
            cursor = resume_cursor
            if cursor >= signal_bar_limit:
                break
            found = signal_for(session_type, execution[cursor:signal_bar_limit], high, low,
                               reference[-1].close, "body", False, bias,
                               allow_range_setup=not sweep_branch_selected)
            carried_signal = False
            # A completed London reclaim can define the New York Sweep Setup.
            # Prefer an ordinary post-lock signal when present; otherwise carry
            # the last causal London sweep forward as a pending body-level order.
            if not found and carried_reference_sweep and not carried_reference_sweep_used:
                _, setup, direction, entry = carried_reference_sweep
                found = 0, setup, direction, entry
                carried_signal = True
                carried_reference_sweep_used = True
            if not found:
                break
            relative_signal, setup, direction, entry = found
            if setup in {"SWEEP", "CLOSE_SWEEP"}:
                sweep_branch_selected = True
            signal_index = cursor + relative_signal
            signal_bar = (reference[carried_reference_sweep[0]] if carried_signal else
                          execution[signal_index])
            boundary_key = round(entry, 10)
            if setup == "RANGE" and boundary_key in used_range_boundaries:
                cursor = signal_index + 1
                continue
            if setup == "RANGE":
                used_range_boundaries.add(boundary_key)
            generated_signals += 1
            structural_buffer = 0.0
            risk = .25*width
            sign = 1 if direction == "LONG" else -1
            if setup in {"SWEEP", "CLOSE_SWEEP"}:
                partial = high if direction == "LONG" else low
            else:
                # RANGE breakout: one complete reference-range projection is
                # 4R because risk is 25% of that range. TREND also manages at 4R.
                partial = entry+sign*4*risk
            range_answer = "YES" if session_type == "RANGE" else "NO"
            sweep_answer = ("YES" if setup in {"SWEEP", "CLOSE_SWEEP"} else
                            "NO" if session_type == "RANGE" else "N/A")
            decision_path = (f"BIAS={bias} -> RANGE?={range_answer} -> "
                             f"SWEEP?={sweep_answer} -> {setup}_SETUP")
            entry_rule = {"SWEEP":"sweep candle body outer edge",
                          "CLOSE_SWEEP":"sweep candle body outer edge",
                          "RANGE":"session top/bottom boundary",
                          "TREND":"confirmed 45-55% retracement; midpoint order after confirmation"}[setup]
            management_rule = ("75% after one reference-range move; 25% to BE/5R"
                               if setup in {"SWEEP", "CLOSE_SWEEP", "RANGE"} else
                               "75% at 4R; move 25% runner to BE and target 5R")
            trade = {"date":str(day), "status":"TRIGGERED", "session_type":session_type,
                     "m15_structure_bias":structure_bias,
                     "reference_session":reference_session.upper(),
                     "source_decision_path":decision_path,
                     "source_entry_rule":entry_rule,
                     "source_stop_rule":"25% of reference range",
                     "source_target_rule":"5x risk (5R)",
                     "source_management_rule":management_rule,
                     "source_direction_rule":("swept boundary reversal direction"
                                              if setup in {"SWEEP", "CLOSE_SWEEP"}
                                              else "classified session direction"
                                              if setup == "TREND"
                                              else "frozen bias direction"),
                     "setup":setup, "direction":direction,
                     "signal_time":signal_bar.time.isoformat().replace("+00:00","Z"),
                     "entry":entry, "stop":entry-sign*risk, "partial":partial,
                     "partial_r":abs(partial-entry)/risk, "target":entry+sign*5*risk,
                     "sl_pips":risk/PIP, "leg_a_weight":.75, "leg_b_weight":.25,
                     "wide_range_handling":wide_range_handling,
                     "structural_buffer_pips":structural_buffer/PIP,
                     "leg_a_target":partial, "leg_b_target":entry+sign*5*risk,
                     "leg_b_stop_after_leg_a":entry}
            if m15_bias_filter and not ((structure_bias == "BULLISH" and direction == "LONG") or
                                  (structure_bias == "BEARISH" and direction == "SHORT")):
                trade.update({"status":"REJECTED_M15_BIAS", "outcome":"REJECTED_M15_BIAS",
                              "r":None})
                day_trades.append(trade); trades.append(trade)
                cursor = signal_index + 1
                continue
            if (setup in {"SWEEP", "CLOSE_SWEEP"} and
                    not disable_momentum_filter):
                rejected, body, average, upper_wick, lower_wick = opposing_expansion(
                    signal_bar, direction,
                    (reference[:carried_reference_sweep[0]] if carried_signal else
                     reference + execution[:signal_index]))
                trade["momentum_body_pips"] = body/PIP
                trade["prior_average_body_pips"] = average/PIP
                trade["momentum_threshold_multiplier"] = MOMENTUM_BODY_MULTIPLIER
                trade["upper_wick_ratio"] = upper_wick
                trade["lower_wick_ratio"] = lower_wick
                trade["minimum_sweep_wick_ratio"] = MINIMUM_SWEEP_WICK_RATIO
                if rejected:
                    trade.update({"status":"REJECTED_MOMENTUM_ALIGNMENT",
                                  "outcome":"REJECTED_MOMENTUM_ALIGNMENT", "r":None})
                    day_trades.append(trade)
                    trades.append(trade)
                    cursor = signal_index + 1
                    continue
            later = execution if carried_signal else execution[signal_index+1:]
            outcome = simulate(
                trade, later, slippage_pips,
                execution[signal_index] if setup == "RANGE" else None)
            trade.update(outcome)
            day_trades.append(trade)
            trades.append(trade)
            if trade.get("r") is not None:
                executed += 1
                session_realized_r += trade["gross_r"]
            exit_absolute = ((0 if carried_signal else signal_index + 1) +
                             int(outcome.get("exit_bar_index", 0)))
            if outcome["outcome"] == "TP5_HIT":
                circuit_breaker = "DAILY_TARGET_LOCK"
            elif outcome["outcome"] == "STOP_LOSS":
                last_loss_timestamp = outcome.get("exit_time")
                # Exit bar E is complete; ignore E+1 through E+4, resume at E+5.
                cooldown_until_bar_index = exit_absolute + POST_LOSS_COOLDOWN_BARS + 1
                if session_realized_r <= MAX_SESSION_LOSS_R + 1e-12:
                    circuit_breaker = "MAX_SESSION_LOSS_LOCK"
            if outcome["outcome"] in {"UNFILLED", "END_WINDOW"}:
                break
            # Resume only after the bar that closed/rejected the prior proposal.
            cursor = exit_absolute + 1
        sessions.append({"date":str(day), "status":"EVALUATED", "session_type":session_type,
                         "reference_session":reference_session.upper(),
                         "directional_bias":bias,
                         "m15_structure_bias":structure_bias,
                         "wide_range_handling":wide_range_handling,
                         "reference_range_pips":width/PIP,
                         "asian_range_pips":width/PIP if reference_session == "asian" else None,
                         "london_range_pips":width/PIP if reference_session == "london" else None,
                         "signals":len(day_trades),
                         "executed_trades":sum(x.get("r") is not None for x in day_trades),
                         "session_realized_gross_r":session_realized_r,
                         "cooldown_until_bar_index":cooldown_until_bar_index,
                         "last_loss_timestamp":last_loss_timestamp,
                         "cooldown_bars_skipped":session_cooldown_bars_skipped,
                         "circuit_breaker":circuit_breaker,
                         "used_range_boundaries":sorted(used_range_boundaries),
                         "trades":day_trades})
    resolved = [x for x in trades if x.get("r") is not None]
    wins = [x for x in trades if x.get("outcome") == "TP5_HIT"]
    return {"strategy":"SESSION_TRADING_SOURCE_WORKFLOW_V2", "source":source, "symbol":symbol,
            "period":{"start":str(START),"end":str(END)},
            "trading_days":len(selected_days),
            "assumptions":{"reference_session":reference_session.upper(),
             "reference_session_utc":("22:00(previous day)-07:00"
                                      if reference_session == "asian" else
                                      f"{reference_start_hour:02d}:00-{reference_end_hour:02d}:00"),
             "reference_start_offset_hours":reference_start_hour,
             "reference_end_offset_hours":reference_end_hour,
             "execution_utc":f"{reference_end_hour:02d}:00-{execution_end_hour:02d}:00",
             "range_classification":"ER=abs(session close-session open)/(session high-session low); RANGE <=0.35; directional TREND >0.35 with close in outer 35%; otherwise UNCERTAIN",
             "signals":"closed-bar confirmation; pending entry may fill only on later bars",
             "asian_close_sweeps":"wick through the final Asian close and close back across it",
             "collision":"STOP_FIRST", "trend_trail":"breakeven floor after 4R; 5R target",
             "slippage_pips_round_trip":slippage_pips,
             "spread_fallback_policy":"dynamic: transitions 1.0; active hours 0.4-0.7; off-hours 1.2 pips",
             "minimum_asian_range_pips":MINIMUM_ASIAN_RANGE_PIPS,
             "max_trades_per_symbol_session":MAX_TRADES_PER_SESSION,
             "execution_end_utc":f"{execution_end_hour:02d}:00",
             "new_entry_cutoff_utc":f"{entry_end_hour:02d}:00",
             "m15_structure_filter_enabled":m15_bias_filter,
             "m15_structure_rule":"last 48 closed M15 bars; confirmed 3-bar swing pivots; HH+HL bullish, LH+LL bearish; neutral rejects only when explicitly enabled",
              "entry_mode":"workflow: sweep candle body; range boundary; confirmed 45-55% trend retracement then midpoint order",
              "minimum_boundary_pierce_pips":MINIMUM_BOUNDARY_PIERCE_PIPS,
              "wide_range_buffer_enabled":False,
              "wide_range_threshold_pips":WIDE_RANGE_THRESHOLD_PIPS,
              "wide_range_stop_buffer_pips":WIDE_RANGE_STOP_BUFFER_PIPS,
             "momentum_filter_disabled":disable_momentum_filter,
             "daily_target_lock":"TP5_HIT",
             "max_session_loss_r":MAX_SESSION_LOSS_R,
             "post_loss_cooldown_bars":POST_LOSS_COOLDOWN_BARS,
             "sweep_momentum_body_multiplier_diagnostic":MOMENTUM_BODY_MULTIPLIER,
             "minimum_directional_sweep_wick_ratio":MINIMUM_SWEEP_WICK_RATIO},
            "sessions":sessions, "trades":trades,
            "summary":{"generated_signals":generated_signals,
             "executed_trades":len(resolved), "trades":len(resolved), "tp5_wins":len(wins),
             "win_rate":len(wins)/len(resolved) if resolved else None,
             "gross_r":sum(x["gross_r"] for x in resolved),
             "net_r_spread_only":sum(x["r"] for x in resolved),
             "net_r_with_friction":sum(x["friction_r"] for x in resolved),
             "gross_pip_gain":sum(x["gross_pips"] for x in resolved),
             "winning_target_pips":sum(x.get("profit_pips",0) for x in wins),
             "historical_spread_trades":sum(x.get("spread_source")=="HISTORICAL_BAR" for x in resolved),
             "dynamic_spread_trades":sum(x.get("spread_source")=="DYNAMIC_INTRADAY_MODEL" for x in resolved),
             "stop_losses":sum(x.get("outcome")=="STOP_LOSS" for x in resolved),
             "momentum_rejections":sum(x.get("outcome")=="REJECTED_MOMENTUM_ALIGNMENT" for x in trades),
             "m15_bias_rejections":sum(x.get("outcome")=="REJECTED_M15_BIAS" for x in trades),
             "daily_target_locks":sum(x.get("circuit_breaker")=="DAILY_TARGET_LOCK" for x in sessions),
             "max_loss_locks":sum(x.get("circuit_breaker")=="MAX_SESSION_LOSS_LOCK" for x in sessions),
             "cooldown_bars_skipped":total_cooldown_bars_skipped},
            "won_trades":wins}


def write_reports(result: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output/"backtest_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    s=result["summary"]
    summary=("# Asian Session Backtest Summary\n\n"
             f"- Source: {result['source']}\n- Calendar range: 2022-10-01 to 2022-10-22\n"
             f"- Active weekday sessions: {result['trading_days']} (2022-10-03 to 2022-10-21)\n"
             f"- Total generated signals: {s['generated_signals']}\n"
             f"- Total executed trades: {s['executed_trades']}\n"
             f"- 5R-target wins / stop losses: {s['tp5_wins']} / {s['stop_losses']}\n"
             f"- Momentum rejections: {s['momentum_rejections']}\n"
             f"- Target locks / max-loss locks: {s['daily_target_locks']} / {s['max_loss_locks']}\n"
             f"- Cooldown bars skipped: {s['cooldown_bars_skipped']}\n"
             f"- Win rate: {s['win_rate']:.2%}\n- Raw Gross R: {s['gross_r']:.3f}R\n"
             f"- Net R after spread (historical or configured fallback): {s['net_r_spread_only']:.3f}R\n"
             f"- Friction-adjusted Net R: {s['net_r_with_friction']:.3f}R\n"
             f"- Historical/dynamic-model spread trades: {s['historical_spread_trades']}/{s['dynamic_spread_trades']}\n"
             f"- Gross position-weighted pip gain: {s['gross_pip_gain']:.1f} pips\n"
             f"- Sum of winning 5R target distances: {s['winning_target_pips']:.1f} pips\n")
    if result.get("baseline_summary"):
        baseline = result["baseline_summary"]
        summary += ("\n## Comparison with unfiltered multi-trade baseline\n\n"
                    "| Metric | Baseline | Filtered | Change |\n"
                    "| --- | ---: | ---: | ---: |\n"
                    f"| Executed trades | {baseline['executed_trades']} | {s['executed_trades']} | {s['executed_trades']-baseline['executed_trades']:+d} |\n"
                    f"| 5R wins | {baseline['tp5_wins']} | {s['tp5_wins']} | {s['tp5_wins']-baseline['tp5_wins']:+d} |\n"
                    f"| Friction-adjusted R | {baseline['net_r_with_friction']:.3f}R | {s['net_r_with_friction']:.3f}R | {s['net_r_with_friction']-baseline['net_r_with_friction']:+.3f}R |\n")
    (output/"backtest_summary.md").write_text(summary, encoding="utf-8")
    lines=["# Won Trades Comparison", "", "Only trades whose final 5R price target was reached are listed. Net R reflects the specified 75% partial management, spread and slippage, so it is not necessarily +5R.", "", "| Trade # | Date & Entry Time | Setup Type | Direction | Entry Price | SL Pips / Price | TP Target (5R) | Profit (Pips) | Net R |", "| :-: | :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: |"]
    for i,x in enumerate(result["won_trades"],1):
        lines.append(f"| {i} | {x['entry_time'][:16].replace('T',' ')} | {x['setup']} | {x['direction'].title()} | {x['entry']:.5f} | {x['sl_pips']:.1f} pips ({x['stop']:.5f}) | {x['target']:.5f} | +{x['profit_pips']:.1f} pips | +{x['friction_r']:.2f}R |")
    (output/"won_trades_comparison.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def write_single_day_inspection(result: dict, bars: list[Bar], day: date,
                                summary_path: Path, trace_path: Path) -> None:
    """Render an audit trace from the deterministic result without re-simulating outcomes."""
    session = result["sessions"][0]
    start = datetime.combine(day, time.min, timezone.utc)
    reference_name = result["assumptions"].get("reference_session", "ASIAN")
    reference_start = int(result["assumptions"]["reference_start_offset_hours"])
    reference_end = int(result["assumptions"]["reference_end_offset_hours"])
    reference = [x for x in bars if start+timedelta(hours=reference_start) <= x.time <
                 start+timedelta(hours=reference_end)]
    execution_end = int(result["assumptions"]["execution_end_utc"].split(":")[0])
    execution = [x for x in bars if start + timedelta(hours=reference_end) <= x.time <
                 start + timedelta(hours=execution_end)]
    high, low = max(x.high for x in reference), min(x.low for x in reference)
    width = high-low
    wide_buffer = (result["assumptions"].get("wide_range_buffer_enabled", False) and
                   width/PIP >= result["assumptions"].get("wide_range_threshold_pips", 40.0))
    risk = width*.25 + (result["assumptions"].get("wide_range_stop_buffer_pips", 3.0)*PIP
                       if wide_buffer else 0.0)
    trades = session.get("trades", [])

    def parsed(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

    cooldown_times: set[datetime] = set()
    circuit_from = None
    realized = 0.0
    for trade in sorted(trades, key=lambda x: x.get("exit_time", "9999")):
        exit_time = parsed(trade.get("exit_time"))
        if trade.get("r") is not None:
            realized += trade["gross_r"]
        if trade.get("outcome") == "STOP_LOSS" and exit_time:
            cooldown_times.update(exit_time + timedelta(minutes=15*i) for i in range(1, 5))
            if realized <= MAX_SESSION_LOSS_R + 1e-12 and circuit_from is None:
                circuit_from = exit_time + timedelta(minutes=15)
        if trade.get("outcome") == "TP5_HIT" and exit_time and circuit_from is None:
            circuit_from = exit_time + timedelta(minutes=15)

    trace = [
        f"SINGLE-DAY EXECUTION TRACE — EURUSD M15 — {day}",
        f"Data inspection window: {day-timedelta(days=1)} 22:00 UTC to {day} 23:45 UTC",
        f"{reference_end:02d}:00 LOCK | {reference_name.title()} High={high:.5f} "
        f"Low={low:.5f} Range={width/PIP:.1f} pips "
        f"SL distance={risk/PIP:.1f} pips Close={reference[-1].close:.5f}",
        f"Session type={session.get('session_type')} | Momentum filter disabled="
        f"{result['assumptions']['momentum_filter_disabled']} | Bias={session.get('directional_bias')} | "
        f"M15 structure={session.get('m15_structure_bias')} | "
        f"New-entry cutoff={result['assumptions']['new_entry_cutoff_utc']} UTC | "
        f"Entry mode={result['assumptions']['entry_mode']}", ""
    ]
    for index, bar in enumerate(execution):
        low_sweep = bar.low < low and bar.close > low
        high_sweep = bar.high > high and bar.close < high
        close_low = bar.low < reference[-1].close and bar.open >= reference[-1].close and bar.close > reference[-1].close
        close_high = bar.high > reference[-1].close and bar.open <= reference[-1].close and bar.close < reference[-1].close
        cooldown = bar.time in cooldown_times
        circuit = circuit_from is not None and bar.time >= circuit_from
        modeled = modeled_spread_pips(bar.time)
        trace.append(
            f"[{index:02d}] {bar.time:%Y-%m-%d %H:%M} UTC | "
            f"O={bar.open:.5f} H={bar.high:.5f} L={bar.low:.5f} C={bar.close:.5f} | "
            f"GATES circuit={'LOCKED' if circuit else 'OPEN'} cooldown={'ACTIVE' if cooldown else 'CLEAR'} "
            f"spread={modeled:.2f}p(model) | "
            f"SIGNAL low_sweep={low_sweep} high_sweep={high_sweep} "
            f"close_sweep_low={close_low} close_sweep_high={close_high}")
        raw_liquidity_signal = low_sweep or high_sweep or close_low or close_high
        if raw_liquidity_signal and (circuit or cooldown):
            reason = "CIRCUIT_BREAKER" if circuit else "POST_LOSS_COOLDOWN"
            trace.append(f"    SUPPRESSED RAW LIQUIDITY TRIGGER: {reason}")
        for number, trade in enumerate(trades, 1):
            signal_time, entry_time, exit_time = (parsed(trade.get(x)) for x in
                                                   ("signal_time", "entry_time", "exit_time"))
            if signal_time == bar.time:
                trace.append(
                    f"    SIGNAL T{number}: {trade['setup']} {trade['direction']} | "
                    f"LIMIT entry={trade['entry']:.5f} SL={trade['stop']:.5f} "
                    f"TP5={trade['target']:.5f} partial={trade['partial']:.5f}")
                trace.append(f"    SOURCE FLOW: {trade.get('source_decision_path', 'N/A')}")
                trace.append(
                    f"    SOURCE RULES: entry={trade.get('source_entry_rule')} | "
                    f"SL={trade.get('source_stop_rule')} | TP={trade.get('source_target_rule')} | "
                    f"management={trade.get('source_management_rule')}")
                if trade.get("outcome") == "REJECTED_MOMENTUM_ALIGNMENT":
                    trace.append(
                        f"    GATE REJECT: required sweep wick ratio <= {MINIMUM_SWEEP_WICK_RATIO:.2f}")
            if entry_time == bar.time:
                gate_limit = .20 * trade["sl_pips"]
                trace.append(
                    f"    FILL T{number}: spread={trade.get('spread_pips', modeled):.2f}p "
                    f"limit={gate_limit:.2f}p PASS | order active")
            if entry_time and exit_time and entry_time <= bar.time <= exit_time:
                sign = 1 if trade["direction"] == "LONG" else -1
                running_r = sign * (bar.close-trade["entry"]) / (trade["sl_pips"]*PIP)
                trace.append(
                    f"    PROGRESS T{number}: bar H/L={bar.high:.5f}/{bar.low:.5f} "
                    f"vs SL={trade['stop']:.5f} TP={trade['target']:.5f}; close={running_r:+.2f}R")
            if exit_time == bar.time:
                trace.append(
                    f"    EXIT T{number}: {trade['outcome']} gross={trade.get('gross_r', 0):+.2f}R "
                    f"net={trade.get('friction_r', 0):+.2f}R")
        trace.append("")
    trace_path.write_text("\n".join(trace), encoding="utf-8")

    lines = [f"# {day:%B %d, %Y} — Single-Day Backtest", "",
             f"- Reference session: {reference_name.title()} ({result['assumptions']['reference_session_utc']} UTC)",
             f"- Reference high / low: {high:.5f} / {low:.5f}",
             f"- Reference range: {width/PIP:.1f} pips",
             f"- Stop distance: {risk/PIP:.1f} pips",
            f"- Session classification: {session.get('session_type')}",
             f"- Directional bias: {session.get('directional_bias')}",
             f"- M15 structure bias: {session.get('m15_structure_bias')}",
             f"- New-entry cutoff: {result['assumptions']['new_entry_cutoff_utc']} UTC",
             f"- Generated signals: {session.get('signals', 0)}",
             f"- Executed trades: {session.get('executed_trades', 0)}",
             f"- Circuit breaker: {session.get('circuit_breaker') or 'not triggered'}", "",
             "## Source-flowchart result basis", ""]
    for number, trade in enumerate(trades, 1):
        range_answer = "Yes" if trade["session_type"] == "RANGE" else "No"
        sweep_answer = "Yes" if trade["setup"] in {"SWEEP", "CLOSE_SWEEP"} else (
            "No" if trade["session_type"] == "RANGE" else "N/A")
        lines += [f"### Trade {number}", "",
                  "| Parameter | Result | Source-flowchart basis |",
                  "| :--- | :--- | :--- |",
                  f"| Reference | {reference_name.title()} session | Completed reference session |",
                  f"| Entry session | {'London' if reference_name == 'ASIAN' else 'New York'} | Following execution session |",
                  f"| Bias | {session.get('directional_bias', '').title()} | Step 1: determine Bias Trend |",
                  f"| Range Session? | {range_answer} | Step 2: Is Range Session? |",
                  f"| Sweep During Session? | {sweep_answer} | Step 3 when Range = Yes |",
                  f"| Setup | {trade['setup'].title()} Setup | Flowchart-selected branch |",
                  f"| Direction | {trade['direction'].title()} | {trade.get('source_direction_rule', 'Frozen bias direction')} |",
                  f"| Signal | {trade['signal_time'][11:16]} UTC | Closed M15 trigger candle |",
                  f"| Entry | {trade['entry']:.5f} | {trade.get('source_entry_rule')} |",
                  f"| Stop loss | {trade['stop']:.5f} ({trade['sl_pips']:.3f} pips) | {trade.get('source_stop_rule')} |",
                  f"| Leg A target | {trade['partial']:.5f} | {trade.get('source_management_rule')} |",
                  f"| TP5 | {trade['target']:.5f} | {trade.get('source_target_rule')} |",
                  f"| Outcome | {trade.get('outcome', 'PENDING')} | Bar-by-bar simulation |", ""]
    lines += ["", "## Trade results", "",
              "| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |",
              "| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |"]
    for number, trade in enumerate(trades, 1):
        timing = trade["signal_time"][11:16] + " / " + (trade.get("entry_time", "unfilled")[11:16]
                                                        if trade.get("entry_time") else "unfilled")
        net = f"{trade['friction_r']:+.2f}R" if trade.get("friction_r") is not None else "N/A"
        lines.append(f"| {number} | {timing} | {trade['setup']} | {trade['direction'].title()} | "
                     f"{trade['entry']:.5f} | {trade['stop']:.5f} | {trade['target']:.5f} | "
                     f"{trade['outcome']} | {net} |")
    summary_path.write_text("\n".join(lines)+"\n", encoding="utf-8")


def run_batch_inspection(bars: list[Bar], source: str, start_day: date, end_day: date,
                         slippage_pips: float, output: Path,
                         disable_momentum_filter: bool = False,
                         selected_days: list[date] | None = None,
                         master_name: str = "batch_inspection_master_summary.md",
                         entry_end_hour: int = 16, m15_bias_filter: bool = False,
                         entry_mode: str = "body", symbol: str = "EURUSD",
                         wide_range_buffer: bool = False,
                         reference_session: str = "asian") -> list[dict]:
    days = selected_days or trading_days(start_day, end_day)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for day in days:
        result = run(bars, source, slippage_pips, [day], 22,
                     disable_momentum_filter, entry_end_hour, m15_bias_filter, entry_mode,
                     symbol, wide_range_buffer, reference_session)
        stem = f"oct{day.day:02d}"
        (output/f"{stem}_results.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
        write_single_day_inspection(result, bars, day,
                                    output/f"{stem}_summary.md",
                                    output/f"{stem}_execution_trace.log")
        results.append(result)

    title = ("Targeted Single-Day Inspection" if "targeted" in master_name
             else "Batch Single-Day Inspection")
    lines = [f"# {symbol} {title}", "",
             f"- Period: {start_day} to {end_day}",
             f"- Active sessions: {len(days)}", "",
             f"| Date | {reference_session.title()} Range | State | Signals | Executed | TP5 | SL | Gross R | Friction Net R | Circuit |",
             "| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |"]
    for result in results:
        session, summary = result["sessions"][0], result["summary"]
        lines.append(
            f"| {session['date']} | {session.get('reference_range_pips', 0):.1f}p | "
            f"{session.get('session_type', session['status'])} | {summary['generated_signals']} | "
            f"{summary['executed_trades']} | {summary['tp5_wins']} | {summary['stop_losses']} | "
            f"{summary['gross_r']:+.3f}R | {summary['net_r_with_friction']:+.3f}R | "
            f"{session.get('circuit_breaker') or '—'} |")
    totals = {key: sum(r["summary"][key] for r in results) for key in
              ("generated_signals", "executed_trades", "tp5_wins", "stop_losses",
               "gross_r", "net_r_with_friction")}
    partial_be = sum(sum(t.get("outcome") == "PARTIAL_THEN_BE" for t in r["trades"])
                     for r in results)
    end_window = sum(sum(t.get("outcome") == "END_WINDOW" for t in r["trades"])
                     for r in results)
    win_rate = (totals["tp5_wins"] / totals["executed_trades"]
                if totals["executed_trades"] else 0.0)
    bias_rejections = sum(r["summary"].get("m15_bias_rejections", 0) for r in results)
    lines += ["", "## Batch totals", "",
              f"- Generated signals: {totals['generated_signals']}",
              f"- Executed trades: {totals['executed_trades']}",
              f"- TP5 wins / stop losses: {totals['tp5_wins']} / {totals['stop_losses']}",
              f"- TP5 win rate: {win_rate:.2%}",
              f"- M15 bias rejections: {bias_rejections}",
              f"- Partial-then-BE / end-window exits: {partial_be} / {end_window}",
              f"- Gross R: {totals['gross_r']:+.3f}R",
              f"- Friction-adjusted R: {totals['net_r_with_friction']:+.3f}R"]
    if "targeted" in master_name:
        lines += ["", "## Audit observations", ""]
        for result in results:
            session, summary = result["sessions"][0], result["summary"]
            outcomes = [trade.get("outcome") for trade in session.get("trades", [])]
            lines.append(
                f"- **{session['date']}** — {session.get('session_type', session['status'])}; "
                f"{summary['generated_signals']} generated / {summary['executed_trades']} executed; "
                f"outcomes: {', '.join(outcomes) if outcomes else 'no qualifying setup'}."
            )
    (output/master_name).write_text(
        "\n".join(lines)+"\n", encoding="utf-8")
    return results


def parse_target_dates(value: str) -> list[date]:
    """Parse a stable, unique comma-separated date list in user-supplied order."""
    days = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        day = date.fromisoformat(item)
        if day.weekday() >= 5:
            raise argparse.ArgumentTypeError(f"target date is not a weekday: {day}")
        if day not in days:
            days.append(day)
    if not days:
        raise argparse.ArgumentTypeError("at least one target date is required")
    return days


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected True or False")


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--csv",type=Path); p.add_argument("--csv-source")
    p.add_argument("--server-offset",type=int,choices=(2,3),default=3)
    p.add_argument("--symbol",default="EURUSD")
    p.add_argument("--date",type=date.fromisoformat,
                   help="Single UTC trading date for deep inspection (YYYY-MM-DD)")
    p.add_argument("--single-day",type=date.fromisoformat,
                   help="Alias for --date")
    p.add_argument("--batch-inspection",action="store_true",
                   help="Run isolated single-day inspections over a weekday range")
    p.add_argument("--targeted-inspection",action="store_true",
                   help="Run isolated inspections for an explicit list of dates")
    p.add_argument("--dates",type=parse_target_dates,
                   help="Comma-separated UTC dates for targeted inspection")
    p.add_argument("--start-date",type=date.fromisoformat)
    p.add_argument("--end-date",type=date.fromisoformat)
    p.add_argument("--disable-momentum-filter",action="store_true",
                   help="Audit toggle: evaluate sweeps without the momentum gate")
    p.add_argument("--slippage-pips",type=float,default=.2,
                   help="Round-trip slippage drag in pips (default: 0.2)")
    p.add_argument("--m15-bias-filter",type=parse_bool,default=False,
                   help="Optionally enforce M15 swing-structure alignment")
    p.add_argument("--entry-mode",choices=("body","limit"),default="body")
    p.add_argument("--reference-session",choices=("asian","london"),default="asian",
                   help="Use Asian for London entries or completed London 07:00-12:00 UTC for New York entries")
    p.add_argument("--wide-range-buffer",type=parse_bool,default=False,
                   help="Add a 3-pip stop buffer and bypass momentum rejection for >=40-pip ranges")
    p.add_argument("--output",type=Path,default=Path("outputs/asian_session_2022_10"))
    p.add_argument("--baseline-results",type=Path,
                   default=Path("outputs/asian_session_2022_10_realigned/backtest_results.json"))
    args=p.parse_args()
    if args.date and args.single_day:
        raise SystemExit("use either --date or --single-day, not both")
    if args.single_day:
        args.date = args.single_day
    entry_cutoff = 18 if args.reference_session == "london" else 16
    if args.csv:
        if not args.csv_source:
            raise SystemExit("--csv-source must identify the MT5 or TradingView export")
        bars,source=load_csv(args.csv),args.csv_source
    else:
        fetch_start = args.start_date or args.date or START
        fetch_end = args.end_date or args.date or END
        bars,source=load_mt5(args.server_offset, args.symbol, fetch_start, fetch_end)
    if args.targeted_inspection:
        if args.date or args.batch_inspection:
            raise SystemExit("--targeted-inspection cannot be combined with --date or --batch-inspection")
        if not args.dates:
            raise SystemExit("--targeted-inspection requires --dates")
        results = run_batch_inspection(
            bars, source, min(args.dates), max(args.dates), args.slippage_pips,
            args.output, args.disable_momentum_filter, args.dates,
            "targeted_inspection_master_summary.md",
            entry_cutoff, args.m15_bias_filter, args.entry_mode, args.symbol,
            args.wide_range_buffer, args.reference_session)
        totals = {key: sum(r["summary"][key] for r in results) for key in
                  ("generated_signals", "executed_trades", "tp5_wins",
                   "stop_losses", "gross_r", "net_r_with_friction")}
        print(json.dumps({"dates":[str(x) for x in args.dates], **totals}, indent=2))
        return 0
    if args.batch_inspection:
        if args.date:
            raise SystemExit("--date cannot be combined with --batch-inspection")
        if not args.start_date or not args.end_date or args.start_date > args.end_date:
            raise SystemExit("batch mode requires a valid --start-date and --end-date")
        results = run_batch_inspection(
            bars, source, args.start_date, args.end_date, args.slippage_pips,
            args.output, args.disable_momentum_filter, None,
            "batch_inspection_master_summary.md",
            entry_cutoff, args.m15_bias_filter, args.entry_mode, args.symbol,
            args.wide_range_buffer, args.reference_session)
        totals = {key: sum(r["summary"][key] for r in results) for key in
                  ("generated_signals", "executed_trades", "tp5_wins",
                   "stop_losses", "gross_r", "net_r_with_friction")}
        print(json.dumps(totals, indent=2))
        return 0
    selected = [args.date] if args.date else None
    execution_end = 22 if args.date else 20
    result=run(bars,source,args.slippage_pips,selected,execution_end,
               args.disable_momentum_filter,
               entry_cutoff, args.m15_bias_filter,args.entry_mode,args.symbol,
               args.wide_range_buffer,args.reference_session)
    if args.baseline_results.exists():
        result["baseline_summary"] = json.loads(
            args.baseline_results.read_text(encoding="utf-8"))["summary"]
    if args.date:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"backtest_results.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
        stem = "oct17" if args.date == date(2022,10,17) else str(args.date)
        summary_path = args.output/f"{stem}_summary.md"
        trace_path = args.output/f"{stem}_execution_trace.log"
        write_single_day_inspection(result, bars, args.date, summary_path, trace_path)
    else:
        write_reports(result,args.output)
    print(json.dumps(result["summary"],indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

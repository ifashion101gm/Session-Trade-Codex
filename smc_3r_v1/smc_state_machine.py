from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import pandas as pd
from .reference_levels import compute_reference_levels
from .smc_features import extract_smc_features
from .canonical_sessions import london_am_window, new_york_am_window


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SMCState(str, Enum):
    SEARCH_SWEEP = "SEARCH_SWEEP"
    WAIT_DISPLACEMENT_CHOCH = "WAIT_DISPLACEMENT_CHOCH"
    WAIT_IMMEDIATE_FVG = "WAIT_IMMEDIATE_FVG"


@dataclass(frozen=True)
class PendingOrder:
    setup_id: str
    model_id: str
    side: OrderSide
    limit_price: float
    sl: float
    tp: float
    activation_time: pd.Timestamp  # C3 Bar Open + 5 minutes
    expiry_time: pd.Timestamp      # Activation + 25 minutes (5 M5 bars)
    meta: dict

    def validate(self):
        if self.side == OrderSide.BUY:
            assert self.sl < self.limit_price < self.tp, (
                f"Invalid BUY geometry: SL={self.sl}, Entry={self.limit_price}, TP={self.tp}"
            )
        else:
            assert self.tp < self.limit_price < self.sl, (
                f"Invalid SELL geometry: TP={self.tp}, Entry={self.limit_price}, SL={self.sl}"
            )
        assert self.expiry_time > self.activation_time, "Expiry must be strictly after activation"
        assert abs(self.limit_price - self.sl) > 0, "Zero risk distance rejected"


class SMCStateMachine:
    def __init__(
        self,
        pip_size: float = 0.0001,
        sl_buffer_pips: float = 2.0,
        tp_r: float = 3.0,
        max_sweep_bars: int = 8
    ):
        self.pip_size = pip_size
        self.sl_buffer = sl_buffer_pips * pip_size
        self.tp_r = tp_r
        self.max_sweep_bars = max_sweep_bars

    def is_in_session_window(self, ts: pd.Timestamp) -> bool:
        # CANONICAL_SESSION_WINDOWS_V1 (config/canonical_sessions.yaml): London AM and New York AM.
        hour = ts.hour
        london = london_am_window()
        new_york = new_york_am_window()
        return (london.start_hour <= hour < london.end_hour) or (new_york.start_hour <= hour < new_york.end_hour)

    def scan_dataset(self, df_m5: pd.DataFrame, model_id: str = "EXP-D") -> List[PendingOrder]:
        df = extract_smc_features(df_m5)
        orders: List[PendingOrder] = []

        state = SMCState.SEARCH_SWEEP
        active_sweep = None
        disp_data = None

        for i in range(2, len(df)):
            ts = df.index[i]
            bar = df.iloc[i]

            if not self.is_in_session_window(ts):
                state = SMCState.SEARCH_SWEEP
                active_sweep = None
                disp_data = None
                continue

            # --- 1. STATE: SEARCH_SWEEP ---
            if state == SMCState.SEARCH_SWEEP:
                levels = compute_reference_levels(df, ts)

                # Check Long Sweep (Asian Low or PDL)
                for ref_name, ref_level in [("ASIAN_LOW", levels.asian_low), ("PDL", levels.pdl)]:
                    if pd.notna(ref_level) and (bar['low'] < ref_level) and (bar['close'] > ref_level):
                        active_sweep = {
                            "side": OrderSide.BUY,
                            "ref_source": ref_name,
                            "ref_level": ref_level,
                            "sweep_extreme": bar['low'],
                            "sweep_idx": i
                        }
                        state = SMCState.WAIT_DISPLACEMENT_CHOCH
                        break

                # Check Short Sweep (Asian High or PDH)
                if state == SMCState.SEARCH_SWEEP:
                    for ref_name, ref_level in [("ASIAN_HIGH", levels.asian_high), ("PDH", levels.pdh)]:
                        if pd.notna(ref_level) and (bar['high'] > ref_level) and (bar['close'] < ref_level):
                            active_sweep = {
                                "side": OrderSide.SELL,
                                "ref_source": ref_name,
                                "ref_level": ref_level,
                                "sweep_extreme": bar['high'],
                                "sweep_idx": i
                            }
                            state = SMCState.WAIT_DISPLACEMENT_CHOCH
                            break
                continue

            # Invalidate sweep if elapsed bars > max_sweep_bars (8 bars = 40 mins)
            if state == SMCState.WAIT_DISPLACEMENT_CHOCH:
                if (i - active_sweep['sweep_idx']) > self.max_sweep_bars:
                    state = SMCState.SEARCH_SWEEP
                    active_sweep = None
                    continue

                # Dynamically fetch latest causal swing confirmed BEFORE this displacement candle
                if active_sweep['side'] == OrderSide.BUY:
                    latest_swing_high = df['last_confirmed_swing_high'].iloc[i - 1]
                    disp = bar['disp_bull']
                    choch = pd.notna(latest_swing_high) and (bar['close'] > latest_swing_high)

                    if disp and choch:
                        disp_data = {
                            "c1_high": df['high'].iloc[i - 1],
                            "disp_idx": i,
                            "disp_body_ratio": round(bar['body'] / bar['median_body_20'], 2),
                            "choch_level": latest_swing_high
                        }
                        state = SMCState.WAIT_IMMEDIATE_FVG
                        continue

                elif active_sweep['side'] == OrderSide.SELL:
                    latest_swing_low = df['last_confirmed_swing_low'].iloc[i - 1]
                    disp = bar['disp_bear']
                    choch = pd.notna(latest_swing_low) and (bar['close'] < latest_swing_low)

                    if disp and choch:
                        disp_data = {
                            "c1_low": df['low'].iloc[i - 1],
                            "disp_idx": i,
                            "disp_body_ratio": round(bar['body'] / bar['median_body_20'], 2),
                            "choch_level": latest_swing_low
                        }
                        state = SMCState.WAIT_IMMEDIATE_FVG
                        continue

            # --- 3. STATE: WAIT_IMMEDIATE_FVG ---
            if state == SMCState.WAIT_IMMEDIATE_FVG:
                assert i == disp_data['disp_idx'] + 1, "C3 evaluation must immediately follow displacement C2"

                if active_sweep['side'] == OrderSide.BUY:
                    c1_high = disp_data['c1_high']
                    c3_low = bar['low']
                    fvg_confirmed = c3_low > c1_high

                    if fvg_confirmed:
                        limit_entry = c3_low
                        sl = active_sweep['sweep_extreme'] - self.sl_buffer
                        risk = limit_entry - sl

                        if risk > 0:
                            activation_time = ts + pd.Timedelta(minutes=5)
                            expiry_time = activation_time + pd.Timedelta(minutes=25)
                            order = PendingOrder(
                                setup_id=f"EURUSD_{ts.strftime('%Y%m%d_%H%M')}_BUY",
                                model_id=model_id,
                                side=OrderSide.BUY,
                                limit_price=limit_entry,
                                sl=sl,
                                tp=limit_entry + (self.tp_r * risk),
                                activation_time=activation_time,
                                expiry_time=expiry_time,
                                meta={
                                    "liquidity_source": active_sweep['ref_source'],
                                    "sweep_extreme": active_sweep['sweep_extreme'],
                                    "choch_level": disp_data['choch_level'],
                                    "displacement_ratio": disp_data['disp_body_ratio'],
                                    "fvg_width_pips": round((c3_low - c1_high) / self.pip_size, 2)
                                }
                            )
                            order.validate()
                            orders.append(order)

                elif active_sweep['side'] == OrderSide.SELL:
                    c1_low = disp_data['c1_low']
                    c3_high = bar['high']
                    fvg_confirmed = c3_high < c1_low

                    if fvg_confirmed:
                        limit_entry = c3_high
                        sl = active_sweep['sweep_extreme'] + self.sl_buffer
                        risk = sl - limit_entry

                        if risk > 0:
                            activation_time = ts + pd.Timedelta(minutes=5)
                            expiry_time = activation_time + pd.Timedelta(minutes=25)
                            order = PendingOrder(
                                setup_id=f"EURUSD_{ts.strftime('%Y%m%d_%H%M')}_SELL",
                                model_id=model_id,
                                side=OrderSide.SELL,
                                limit_price=limit_entry,
                                sl=sl,
                                tp=limit_entry - (self.tp_r * risk),
                                activation_time=activation_time,
                                expiry_time=expiry_time,
                                meta={
                                    "liquidity_source": active_sweep['ref_source'],
                                    "sweep_extreme": active_sweep['sweep_extreme'],
                                    "choch_level": disp_data['choch_level'],
                                    "displacement_ratio": disp_data['disp_body_ratio'],
                                    "fvg_width_pips": round((c1_low - c3_high) / self.pip_size, 2)
                                }
                            )
                            order.validate()
                            orders.append(order)

                state = SMCState.SEARCH_SWEEP
                active_sweep = None
                disp_data = None

        return orders

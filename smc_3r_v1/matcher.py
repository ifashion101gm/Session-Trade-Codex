from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
from .smc_state_machine import OrderSide, PendingOrder


class OrderStatus(str, Enum):
    WAITING = "WAITING"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"
    DATA_GAP = "DATA_GAP"


class TradeOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    FORCED_EXIT = "FORCED_EXIT"
    DATA_GAP = "DATA_GAP"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class TradeRecord:
    setup_id: str
    model_id: str
    side: OrderSide
    order_status: OrderStatus
    activation_time: pd.Timestamp
    expiry_time: pd.Timestamp
    fill_time: Optional[pd.Timestamp]
    exit_time: Optional[pd.Timestamp]
    entry_price: float
    sl: float
    tp: float
    exit_price: Optional[float]
    outcome: Optional[TradeOutcome]
    realized_r: Optional[float]
    mae_r: Optional[float]
    mfe_r: Optional[float]
    latency_m1_bars: Optional[int]
    meta: dict
    execution_authority: str = "SIMULATED_SPREAD"
    intrabar_ambiguity: bool = False


class M1OrderMatcher:
    def __init__(self, spread_pips: float = 1.0, pip_size: float = 0.0001):
        self.spread_pips = spread_pips
        self.pip_size = pip_size
        self.spread = spread_pips * pip_size

    def evaluate_order(self, order: PendingOrder, m1_df: pd.DataFrame) -> TradeRecord:
        bars = m1_df[m1_df.index >= order.activation_time]

        record = TradeRecord(
            setup_id=order.setup_id,
            model_id=order.model_id,
            side=order.side,
            order_status=OrderStatus.WAITING,
            activation_time=order.activation_time,
            expiry_time=order.expiry_time,
            fill_time=None,
            exit_time=None,
            entry_price=order.limit_price,
            sl=order.sl,
            tp=order.tp,
            exit_price=None,
            outcome=None,
            realized_r=None,
            mae_r=None,
            mfe_r=None,
            latency_m1_bars=None,
            meta=order.meta,
        )

        # Gap Check 1: No data available at or after activation
        if bars.empty:
            record.order_status = OrderStatus.DATA_GAP
            record.outcome = TradeOutcome.DATA_GAP
            return record

        # Gap Check 2: First available bar must start exactly at activation_time
        if bars.index[0] != order.activation_time:
            record.order_status = OrderStatus.DATA_GAP
            record.outcome = TradeOutcome.DATA_GAP
            return record

        fill_idx = -1
        bars_waiting = 0

        # --- Phase 1: Search for Limit Fill [activation, expiry) ---
        for i, (ts, bar) in enumerate(bars.iterrows()):
            if i > 0 and (ts - bars.index[i - 1]).total_seconds() != 60:
                record.order_status = OrderStatus.DATA_GAP
                record.outcome = TradeOutcome.DATA_GAP
                return record

            if ts >= order.expiry_time:
                record.order_status = OrderStatus.EXPIRED
                return record

            bars_waiting += 1

            if order.side == OrderSide.BUY:
                if (bar['low'] + self.spread) <= order.limit_price:
                    record.order_status = OrderStatus.FILLED
                    record.fill_time = ts
                    record.latency_m1_bars = bars_waiting
                    fill_idx = i
                    break
            else:
                if bar['high'] >= order.limit_price:
                    record.order_status = OrderStatus.FILLED
                    record.fill_time = ts
                    record.latency_m1_bars = bars_waiting
                    fill_idx = i
                    break

        if record.order_status != OrderStatus.FILLED:
            record.order_status = OrderStatus.EXPIRED
            return record

        # --- Phase 2: Chronological Exit Evaluation ---
        post_fill_bars = bars.iloc[fill_idx:]
        risk_dist = abs(order.limit_price - order.sl)
        mae_dist, mfe_dist = 0.0, 0.0
        daily_cutoff = order.activation_time.floor('D') + pd.Timedelta(hours=21, minutes=55)

        for i, (ts, bar) in enumerate(post_fill_bars.iterrows()):
            if i > 0 and (ts - post_fill_bars.index[i - 1]).total_seconds() != 60:
                record.outcome = TradeOutcome.DATA_GAP
                record.exit_time = ts
                return record

            if ts >= daily_cutoff:
                record.outcome = TradeOutcome.FORCED_EXIT
                record.exit_time = ts
                if order.side == OrderSide.BUY:
                    record.exit_price = bar['close']
                    current_pnl = bar['close'] - order.limit_price
                else:
                    record.exit_price = bar['close'] + self.spread
                    current_pnl = order.limit_price - record.exit_price

                record.realized_r = round(current_pnl / risk_dist, 2)
                break

            if order.side == OrderSide.BUY:
                bid_low, bid_high = bar['low'], bar['high']
                hit_sl = bid_low <= order.sl
                hit_tp = bid_high >= order.tp

                mae_dist = max(mae_dist, max(0.0, order.limit_price - bid_low))
                mfe_dist = max(mfe_dist, max(0.0, bid_high - order.limit_price))

                if hit_sl and hit_tp:
                    record.outcome = TradeOutcome.LOSS
                    record.exit_price = order.sl
                    record.realized_r = -1.0
                    record.exit_time = ts
                    record.intrabar_ambiguity = True
                    break
                elif hit_sl:
                    record.outcome = TradeOutcome.LOSS
                    record.exit_price = order.sl
                    record.realized_r = -1.0
                    record.exit_time = ts
                    break
                elif hit_tp:
                    record.outcome = TradeOutcome.WIN
                    record.exit_price = order.tp
                    record.realized_r = (order.tp - order.limit_price) / risk_dist
                    record.exit_time = ts
                    break

            else:  # OrderSide.SELL
                ask_low = bar['low'] + self.spread
                ask_high = bar['high'] + self.spread
                hit_sl = ask_high >= order.sl
                hit_tp = ask_low <= order.tp

                mae_dist = max(mae_dist, max(0.0, ask_high - order.limit_price))
                mfe_dist = max(mfe_dist, max(0.0, order.limit_price - ask_low))

                if hit_sl and hit_tp:
                    record.outcome = TradeOutcome.LOSS
                    record.exit_price = order.sl
                    record.realized_r = -1.0
                    record.exit_time = ts
                    record.intrabar_ambiguity = True
                    break
                elif hit_sl:
                    record.outcome = TradeOutcome.LOSS
                    record.exit_price = order.sl
                    record.realized_r = -1.0
                    record.exit_time = ts
                    break
                elif hit_tp:
                    record.outcome = TradeOutcome.WIN
                    record.exit_price = order.tp
                    record.realized_r = (order.limit_price - order.tp) / risk_dist
                    record.exit_time = ts
                    break

        record.mae_r = round(mae_dist / risk_dist, 2) if risk_dist > 0 else 0.0
        record.mfe_r = round(mfe_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        if record.outcome is None:
            record.outcome = TradeOutcome.UNRESOLVED

        return record

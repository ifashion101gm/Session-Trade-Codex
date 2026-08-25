import logging
import math
import time

import MetaTrader5 as mt5


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class MT5RangeBarExecutor:
    """Demo-only live executor for pure one-bar momentum on synthetic range bars."""

    def __init__(
        self,
        symbol: str = "EURUSD",
        magic_number: int = 108801,
        range_pips: float = 8.0,
        fixed_rr: float = 1.5,
        sl_buffer_pips: float = 1.0,
        risk_pct: float = 0.01,
        max_slippage_points: int = 10,
    ):
        self.symbol = symbol
        self.magic = magic_number
        self.range_pips = range_pips
        self.fixed_rr = fixed_rr
        self.sl_buffer_pips = sl_buffer_pips
        self.risk_pct = risk_pct
        self.max_slippage = max_slippage_points
        self.curr_bar_open = None
        self.curr_bar_high = -math.inf
        self.curr_bar_low = math.inf
        self.last_completed_bar = None
        self.point = 0.00001
        self.pip_size = 0.0001
        self.range_size = range_pips * self.pip_size

    def initialize_mt5(self) -> bool:
        if not mt5.initialize():
            logging.error("MT5 initialization failed: %s", mt5.last_error())
            return False

        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            logging.error("MT5 account or terminal information unavailable: %s", mt5.last_error())
            return False
        if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            logging.error("Refusing to run: connected account is not demo (trade_mode=%s)", account.trade_mode)
            return False
        if not account.trade_allowed or not account.trade_expert or not terminal.trade_allowed:
            logging.error("Refusing to run: MT5 trading permissions are disabled")
            return False
        if not mt5.symbol_select(self.symbol, True):
            logging.error("Failed to select symbol %s", self.symbol)
            return False

        info = mt5.symbol_info(self.symbol)
        if info is None:
            logging.error("Symbol %s information unavailable", self.symbol)
            return False
        self.point = float(info.point)
        self.pip_size = self.point * 10 if info.digits in (3, 5) else self.point
        self.range_size = self.range_pips * self.pip_size
        logging.info(
            "Connected to demo account %s; %s point=%s pip=%s range=%s",
            str(account.login)[-3:], self.symbol, self.point, self.pip_size, self.range_size,
        )
        return True

    def get_open_position(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            logging.warning("Could not read positions: %s", mt5.last_error())
            return None
        return next((position for position in positions if position.magic == self.magic), None)

    def calculate_lot_size(self, stop_distance_price: float) -> float:
        account = mt5.account_info()
        info = mt5.symbol_info(self.symbol)
        if account is None or info is None:
            return 0.0
        if stop_distance_price <= 0 or info.trade_tick_value <= 0 or info.trade_tick_size <= 0:
            return float(info.volume_min)
        risk_amount = float(account.equity) * self.risk_pct
        raw_lot = risk_amount / ((stop_distance_price / info.trade_tick_size) * info.trade_tick_value)
        lot = round(raw_lot / info.volume_step) * info.volume_step
        return round(max(info.volume_min, min(info.volume_max, lot)), 2)

    def send_order(self, order_type: int, entry_price: float, sl: float, tp: float) -> None:
        info = mt5.symbol_info(self.symbol)
        if info is None:
            logging.error("Cannot send order: symbol information unavailable")
            return
        volume = self.calculate_lot_size(abs(entry_price - sl))
        if volume <= 0:
            logging.error("Cannot send order: calculated volume is invalid")
            return
        filling = mt5.ORDER_FILLING_IOC
        if not (info.filling_mode & mt5.ORDER_FILLING_IOC):
            filling = mt5.ORDER_FILLING_FOK
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price,
            "sl": round(sl, info.digits),
            "tp": round(tp, info.digits),
            "deviation": self.max_slippage,
            "magic": self.magic,
            "comment": "RangeBar_1Bar_Momentum",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error("Order failed: result=%s error=%s", result, mt5.last_error())
            return
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        logging.info("Executed %s %.2f lots @ %s SL=%s TP=%s", direction, volume, entry_price, sl, tp)

    def update_range_bars(self, price: float) -> bool:
        if self.curr_bar_open is None:
            self.curr_bar_open = price
            self.curr_bar_high = price
            self.curr_bar_low = price
            return False
        self.curr_bar_high = max(self.curr_bar_high, price)
        self.curr_bar_low = min(self.curr_bar_low, price)
        if self.curr_bar_high - self.curr_bar_low < self.range_size:
            return False
        if price >= self.curr_bar_open:
            close = self.curr_bar_low + self.range_size
            self.last_completed_bar = {
                "open": self.curr_bar_open, "high": close,
                "low": self.curr_bar_low, "close": close, "direction": 1,
            }
            self.curr_bar_open = close
            self.curr_bar_low = close
            self.curr_bar_high = max(close, price)
        else:
            close = self.curr_bar_high - self.range_size
            self.last_completed_bar = {
                "open": self.curr_bar_open, "high": self.curr_bar_high,
                "low": close, "close": close, "direction": -1,
            }
            self.curr_bar_open = close
            self.curr_bar_high = close
            self.curr_bar_low = min(close, price)
        logging.info("Range bar closed: %s %s", "BULL" if self.last_completed_bar["direction"] == 1 else "BEAR", self.last_completed_bar)
        return True

    def run(self, poll_interval_sec: float = 0.5) -> None:
        if not self.initialize_mt5():
            mt5.shutdown()
            return
        logging.info("Demo execution loop started; press Ctrl+C to stop")
        try:
            while True:
                tick = mt5.symbol_info_tick(self.symbol)
                if tick is None:
                    time.sleep(poll_interval_sec)
                    continue
                bar_closed = self.update_range_bars((tick.bid + tick.ask) / 2.0)
                if bar_closed and self.get_open_position() is None:
                    bar = self.last_completed_bar
                    buffer = self.sl_buffer_pips * self.pip_size
                    if bar["direction"] == 1:
                        entry = tick.ask
                        sl = bar["low"] - buffer
                        risk = entry - sl
                        if risk > 0:
                            self.send_order(mt5.ORDER_TYPE_BUY, entry, sl, entry + risk * self.fixed_rr)
                    else:
                        entry = tick.bid
                        sl = bar["high"] + buffer
                        risk = sl - entry
                        if risk > 0:
                            self.send_order(mt5.ORDER_TYPE_SELL, entry, sl, entry - risk * self.fixed_rr)
                time.sleep(poll_interval_sec)
        except KeyboardInterrupt:
            logging.info("Demo bot stopped by user")
        finally:
            mt5.shutdown()
            logging.info("MT5 connection terminated")


if __name__ == "__main__":
    MT5RangeBarExecutor().run()

import os
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_demo_credentials():
    """Read MT5 demo account credentials from environment variables.

    Expected variables:
        MT5_DEMO_LOGIN      – integer login ID
        MT5_DEMO_PASSWORD   – account password (string)
        MT5_DEMO_SERVER     – MT5 server name (e.g. "MetaQuotes-Demo")
    """
    try:
        login = int(os.getenv("MT5_DEMO_LOGIN"))
        password = os.getenv("MT5_DEMO_PASSWORD")
        server = os.getenv("MT5_DEMO_SERVER")
        if not all([login, password, server]):
            raise ValueError("Missing one or more MT5_DEMO_* environment variables")
        return login, password, server
    except Exception as e:
        raise RuntimeError(f"Failed to read demo credentials: {e}")

def main():
    import MetaTrader5 as mt5

    login, password, server = get_demo_credentials()

    # Initialise connection to the demo account
    if not mt5.initialize(login=login, password=password, server=server, timeout=5000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    logger.info("MT5 connection initialised – demo account ready")

    # Verify the account type
    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError(f"Unable to retrieve account info: {mt5.last_error()}")
    logger.info(f"Account #{account_info.login} – type: {account_info.trade_mode}")

    # Prepare a tiny market BUY order (0.01 lot) for EURUSD
    symbol = "EURUSD"
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Symbol {symbol} not available: {mt5.last_error()}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 10,
        "magic": 123456,
        "comment": "Sample demo order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order failed – retcode {result.retcode}: {mt5.last_error()}")
    else:
        logger.info(
            f"Order placed – ticket {result.order}, price {result.price}, volume {result.volume}"
        )

    # Give the broker a moment to process then shut down
    time.sleep(1)
    mt5.shutdown()
    logger.info("MT5 shutdown complete")

if __name__ == "__main__":
    main()

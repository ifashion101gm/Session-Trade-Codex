# Sample script to place a demo order on a MetaTrader5 demo account
#
# This script is **stand‑alone** and does **not** modify the existing read‑only
# MT5 gateway used by the Session‑Trade‑Codex project.  It demonstrates how a
# developer can place a market order on a demo account for testing purposes.
#
# NOTE: Do NOT commit real credentials to the repository.  Store them in
# environment variables or a secure vault and reference them here.

import os
import time
import logging

# Configure logging – the MT5 library uses the standard logging module.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: load connection parameters from environment variables.
# ---------------------------------------------------------------------------
def get_demo_credentials():
    """Retrieve demo account credentials from the environment.

    Expected environment variables:
        MT5_DEMO_LOGIN   – integer login id for the demo account
        MT5_DEMO_PASSWORD – string password
        MT5_DEMO_SERVER   – server name (e.g. "MetaQuotes-Demo")
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

# ---------------------------------------------------------------------------
# Main flow – initialize MT5, place a market BUY order, then shut down.
# ---------------------------------------------------------------------------
def main():
    import MetaTrader5 as mt5

    login, password, server = get_demo_credentials()

    # Initialise the connection.  ``login`` is a demo account, so the
    # ``trade_mode`` will be ``ACCOUNT_TRADE_MODE_DEMO``.
    if not mt5.initialize(login=login, password=password, server=server, timeout=5000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    logger.info("MT5 connection initialised – demo account ready")

    # Verify the account type.
    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError(f"Unable to retrieve account info: {mt5.last_error()}")
    logger.info(f"Account #{account_info.login} – type: {account_info.trade_mode}")

    # -----------------------------------------------------------------------
    # Place a simple market BUY order for 0.01 lots of EURUSD (or any available
    # symbol).  Adjust the symbol, volume, and price as needed for your demo.
    # -----------------------------------------------------------------------
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "EURUSD",
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick("EURUSD").ask,
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

    time.sleep(1)  # give the broker a moment to process
    mt5.shutdown()
    logger.info("MT5 shutdown complete")

if __name__ == "__main__":
    main()

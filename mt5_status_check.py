import os
from session_strategy.mt5_gateway import MT5ReadOnlyGateway

def main():
    # Load configuration (default or overridden via TRADING_CONFIG)
    # The gateway does not need explicit permissions for read‑only actions.
    try:
        with MT5ReadOnlyGateway() as gw:
            acc = gw.account()
            print(f"Account: {acc.login_masked} ({acc.account_type})")
            print(f"Balance: {acc.balance:.2f}, Equity: {acc.equity:.2f}")
            print(f"Positions open: {len(gw.positions())}")
            print(f"Pending orders: {len(gw.orders())}")
    except Exception as e:
        print(f"Failed to retrieve MT5 status: {e}")

if __name__ == "__main__":
    main()

import MetaTrader5 as mt5
if not mt5.initialize():
    print("init failed", mt5.last_error())
else:
    acc = mt5.account_info()
    term = mt5.terminal_info()
    print("login:", acc.login)
    print("server:", acc.server)
    print("trade_mode:", acc.trade_mode, "(0=demo,1=contest,2=real)")
    print("trade_allowed(account):", acc.trade_allowed)
    print("trade_expert:", acc.trade_expert)
    print("terminal trade_allowed:", term.trade_allowed)
    print("balance:", acc.balance, "equity:", acc.equity)
    for sym in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD.crp"]:
        info = mt5.symbol_info(sym)
        print(sym, "exists:", info is not None,
              "visible:", info.visible if info else None,
              "spread:", info.spread if info else None)
    mt5.shutdown()

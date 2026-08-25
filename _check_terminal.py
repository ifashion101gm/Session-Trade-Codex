import MetaTrader5 as mt5

if not mt5.initialize():
    raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

term = mt5.terminal_info()
acc = mt5.account_info()
print("terminal.trade_allowed (algo trading toggle):", term.trade_allowed)
print("terminal.data_path:", term.data_path)
print("terminal.commondata_path:", term.commondata_path)
print("account.trade_expert:", acc.trade_expert)
print("account.trade_mode:", acc.trade_mode)

positions = mt5.positions_get()
print("ALL open positions:", len(positions) if positions else 0)
for p in (positions or []):
    print(f"  ticket={p.ticket} symbol={p.symbol} magic={p.magic} comment={p.comment} volume={p.volume}")

orders = mt5.orders_get()
print("ALL pending orders:", len(orders) if orders else 0)
for o in (orders or []):
    print(f"  ticket={o.ticket} symbol={o.symbol} magic={o.magic} comment={o.comment}")

mt5.shutdown()

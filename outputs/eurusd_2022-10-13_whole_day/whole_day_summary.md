# EUR/USD M15 — October 13, 2022 Whole-Day Backtest

- Data: VT Markets (Pty) Ltd / VTMarkets-Demo, normalized to UTC
- Daily bias: Bullish, frozen at 07:00 UTC
- Execution: two causal cycles; cycle-level target locks
- Costs: dynamic spread plus 0.2-pip round-trip slippage

| Cycle | Reference state | Setup | Entry / time | Stop | 4R partial | TP5 / exit | Gross R | Friction-adjusted R |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| Asian → London | Trend | Long Trend | 0.97054 / 08:00 | 0.969705 | 0.97388 | 0.974715 / 11:30 | +4.25R | +4.154R |
| London → New York | Trend | Long Trend | 0.971925 / 15:00 | 0.9702325 | 0.978695 | 0.9803875 / 17:30 | +4.25R | +4.197R |

## Combined result

- Generated signals: 2
- Executed trades: 2
- TP5 wins: 2
- Stop losses: 0
- Win rate: 100%
- Gross R: +8.50R
- Net R after spread and slippage: +8.351R
- Position-weighted gross pip gain: +107.419 pips

The New York session itself is described for market context but is not used as a
third same-day reference/entry cycle. Each Trend trade closes 75% at 4R and the
remaining 25% at 5R, producing 4.25R gross per completed setup.

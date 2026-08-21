# October 20, 2022 — London to New York Screenshot Validation

## Identification

- Symbol/timeframe: EURUSD M15
- Completed reference: London 07:00–12:00 UTC
- Execution session: New York 12:00–18:00 UTC
- Candle-path match: October 20, 2022 MT5 history

## Screenshot source trade

| Parameter | Result | Rule basis |
| :--- | :--- | :--- |
| Bias | Bullish | Frozen daily bias |
| Session state | Range | User-confirmed source branch |
| Setup | Range Long | Range + no prior source Sweep |
| London high / low | 0.98289 / 0.97716 | Frozen 07:00–12:00 reference |
| Entry | 0.97716 | London low boundary |
| Stop | 0.9757275 | 25% of 57.3-pip range |
| Leg A | 0.98289 | One full range / 4R |
| TP5 | 0.9843225 | Five times 14.325-pip risk |
| Screenshot outcome | MISSED_TRADE | Entry boundary is never filled |

## Connected MT5 comparison

The connected New York bars reach a minimum of `0.97798`, so the exact source
long order at `0.97716` is not filled. This confirms the screenshot's missed
trade result. The later move above TP5 cannot be counted without an entry.
Connected bars subsequently form a separate short Sweep that stops out; it is a
different causal trade and does not change the missed Range order.

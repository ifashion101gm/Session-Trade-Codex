# October 13, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.97221 / 0.96887
- Reference range: 33.4 pips
- Stop distance: 8.4 pips
- Session classification: BULLISH_TREND
- Directional bias: BULLISH
- M15 structure bias: BULLISH
- New-entry cutoff: 16:00 UTC
- Generated signals: 1
- Executed trades: 1
- Circuit breaker: DAILY_TARGET_LOCK

## Source-flowchart result basis

### Trade 1

| Parameter | Result | Source-flowchart basis |
| :--- | :--- | :--- |
| Reference | Asian session | Completed reference session |
| Entry session | London | Following execution session |
| Bias | Bullish | Step 1: determine Bias Trend |
| Range Session? | No | Step 2: Is Range Session? |
| Sweep During Session? | N/A | Step 3 when Range = Yes |
| Setup | Trend Setup | Flowchart-selected branch |
| Direction | Long | frozen bias direction |
| Signal | 07:45 UTC | Closed M15 trigger candle |
| Entry | 0.97054 | middle of reference range |
| Stop loss | 0.96970 (8.350 pips) | 25% of reference range |
| Leg A target | 0.97388 | 75% at 4R; trail 25% runner |
| TP5 | 0.97471 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 07:45 / 08:00 | TREND | Long | 0.97054 | 0.96970 | 0.97471 | TP5_HIT | +4.15R |

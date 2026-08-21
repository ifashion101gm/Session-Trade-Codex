# October 20, 2022 — Single-Day Backtest

- Reference session: Asian (00:00-07:00 UTC)
- Reference high / low: 0.97942 / 0.97544
- Reference range: 39.8 pips
- Stop distance: 9.9 pips
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
| Signal | 07:00 UTC | Closed M15 trigger candle |
| Entry | 0.97743 | middle of reference range |
| Stop loss | 0.97644 (9.950 pips) | 25% of reference range |
| Leg A target | 0.98141 | 75% at 4R; trail 25% runner |
| TP5 | 0.98240 | 5x risk (5R) |
| Outcome | TP5_HIT | Bar-by-bar simulation |


## Trade results

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 07:00 / 07:00 | TREND | Long | 0.97743 | 0.97644 | 0.98240 | TP5_HIT | +4.13R |

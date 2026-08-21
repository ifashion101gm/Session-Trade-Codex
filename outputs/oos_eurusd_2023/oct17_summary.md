# February 17, 2023 — Single-Day Backtest

- Asian high / low: 1.06656 / 1.06296
- Asian range: 36.0 pips
- Stop distance: 9.0 pips
- Session classification: RANGE
- Directional bias: BEARISH
- M15 structure bias: BEARISH
- New-entry cutoff: 18:00 UTC
- Generated signals: 3
- Executed trades: 2
- Circuit breaker: DAILY_TARGET_LOCK

| # | Signal / Entry UTC | Setup | Side | Entry | SL | TP5 | Outcome | Net R |
| :-: | :--- | :--- | :-: | ---: | ---: | ---: | :--- | ---: |
| 1 | 10:15 / 10:15 | SWEEP | Long | 1.06296 | 1.06206 | 1.06746 | STOP_LOSS | -1.07R |
| 2 | 12:15 / unfilled | SWEEP | Long | 1.06296 | 1.06206 | 1.06746 | REJECTED_MOMENTUM_ALIGNMENT | N/A |
| 3 | 12:30 / 12:30 | SWEEP | Long | 1.06296 | 1.06206 | 1.06746 | TP5_HIT | +4.16R |

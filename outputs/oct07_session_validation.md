# EURUSD M15 Session Validation — 2022-10-07

Source: VT Markets demo history, server offset +3 normalized to UTC.

## OHLCV quality

| Check | Result |
| --- | --- |
| Expected M15 bars, 00:00–22:00 UTC | 88 |
| Available bars | 84 |
| Duplicate timestamps | 0 |
| Impossible OHLC candles | 0 |
| Available interval | 00:00–20:45 UTC |
| Missing interval | 21:00–21:45 UTC (Friday broker close) |

No synthetic bars were inserted. Both reference sessions are complete; only the
late management window is shortened.

## Asian reference → London execution

| Parameter | Result |
| --- | --- |
| Reference | 00:00–07:00 UTC, 28/28 bars |
| Open / close | 0.97886 / 0.97816 |
| High / low | 0.98118 / 0.97657 |
| Range | 46.1 pips |
| Path efficiency | 0.066 |
| Bias / M15 structure | Bearish / Bearish |
| Classification | Range |
| Aligned sweep before entry | No |
| Setup | Short Range |
| Signal / entry | 08:15 UTC / 0.98118 |
| Stop / TP5 | 0.9823325 / 0.9754175 |
| Outcome | TP5_HIT at 12:30 UTC |
| Gross / friction-adjusted | +4.25R / +4.183R |

A later 14:30 Asian-low sweep passes the wick/reclaim test, but it implies a
Long and is rejected because the frozen bias is Bearish.

## London reference → New York execution

| Parameter | Result |
| --- | --- |
| Reference | 07:00–12:00 UTC, 20/20 bars |
| Open / close | 0.97819 / 0.97873 |
| High / low | 0.98168 / 0.97815 |
| Range | 35.3 pips |
| Path efficiency | 0.055 |
| Bias / M15 structure | Bearish / Bearish |
| Classification | Range |
| Aligned sweep before entry | No |
| Setup | Short Range |
| Signal / entry | 12:30 UTC / 0.97815 |
| Stop / TP5 | 0.9790325 / 0.9737375 |
| Outcome | TP5_HIT at 12:45 UTC |
| Gross / friction-adjusted | +4.25R / +4.205R |

Low sweeps detected from 15:00 through 15:45 imply Long entries and are rejected
against the frozen Bearish bias. They do not change the earlier causal result.

## Status

Data quality: PASS for both decision windows.  
Asian classification: RANGE.  
London classification: RANGE.  
These are engine-derived results and are not promoted to source-video truth
until confirmed against the corresponding chart or walkthrough.

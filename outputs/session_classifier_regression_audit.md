# Session Classifier Regression Audit

Date: 2026-08-14  
Data: EURUSD M15, VT Markets, normalized to UTC  
Reference windows: Asian 00:00–07:00; London 07:00–12:00

## Truth-labelled regression set

| Date | Reference | Bias | Efficiency | Close location | Expected | Actual | Result |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| 2022-10-03 | Asian | Bearish | 0.029 | 0.265 | Range | Range | PASS |
| 2022-10-03 | London | Bearish | 0.198 | 0.210 | Range | Range | PASS |
| 2022-10-04 | London | Bullish | 0.167 | 0.740 | Range | Range | PASS |
| 2022-10-05 | Asian | Bullish | 0.036 | 0.513 | Range | Range | PASS |
| 2022-10-05 | London | Bearish | 0.632 | 0.074 | Range | Range | PASS |
| 2022-10-06 | Asian | Bearish | 0.123 | 0.105 | Range | Range | PASS |
| 2022-10-06 | London | Bearish | 0.237 | 0.169 | Trend | Trend | PASS |

Result: **7/7 truth-labelled cycles pass (100%)**. This is a regression result,
not a statistically reliable estimate of future classification accuracy.

## Full 15-day behavior check

| Reference | Range labels | Trend labels | Trend dates |
| --- | ---: | ---: | --- |
| Asian | 13 | 2 | Oct 13 bearish; Oct 20 bullish |
| London | 13 | 2 | Oct 6 bearish; Oct 13 bullish |

The classifier does not collapse into an all-Range or all-Trend output. The 23
unlabelled cycles in this matrix are diagnostic only and require chart/source
confirmation before they can be counted as correct or incorrect.

## Decision rule under test

1. Path efficiency above 0.70 is Trend.
2. A low-efficiency reversal is also Trend when the counter-bias extreme occurs
   after the open but within the first 25% of the reference bars, the opposite
   extreme occurs in the final 25%, and the close locks inside the directional
   terminal 20% of the range.
3. Otherwise the reference session is Range.
4. Only reference-session bars available at lock time are used.

## Capacity and limitation

The current evidence validates backward compatibility for all stored session
types and confirms causal operation. It does not prove generalization: only
seven cycles have authoritative labels, with one labelled Trend example. More
source-labelled Trend and borderline sessions are required before changing the
thresholds or treating the classifier as production-calibrated.

# October 21, 2022 — Asian to London Screenshot Validation

- Symbol/timeframe: EURUSD M15
- Reference: Asian 00:00–07:00 UTC
- Execution: London 07:00–16:00 UTC
- Bias: Bearish
- Session state: Range
- Setup: Range Short
- Entry: `0.97835`
- Stop: `0.9788925` (`5.425` pips; 25% of reference range)
- Leg A: `0.97618` (4R)
- TP5: `0.9756375`
- Outcome: `STOP_LOSS`, `−1R`, on the 07:15 trigger candle

The former engine output was a counter-bias Long Sweep because body mode treated
a 0.7-pip low breach as valid. Applying the configured 1-pip minimum breach in
all modes removes that false Sweep and exposes the correct bearish Range setup.

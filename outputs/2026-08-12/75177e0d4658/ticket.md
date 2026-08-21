# ASIAN_SESSION_V1 v1.0 — Trade Analysis Ticket

- Status: **SIGNAL_ACCEPTED**
- Analysis ID: `75177e0d4658`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `936249f5ee059177`)
- Symbol: USDJPY
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T08:23:20.103114+00:00
- Timestamp (Myanmar): 2026-08-12 14:53 MMT
- Asian session: 2026-08-11T22:00:00+00:00 → 2026-08-12T07:00:00+00:00
- Last closed execution candle: 2026-08-12T08:00:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 159.323 / 159.326 / 0.003

## Asian range (locked)

- High / Low: 159.461 / 159.2
- Range: 0.2610000000000241
- Midpoint: 159.3305
- Quartiles: 159.26524999999998 / 159.39575000000002
- Risk unit R (25% of range): 0.06525000000000603
- Efficiency ratio: 0.4789272030650899 · Close location: 0.6973180076628336
- Session type: **BULLISH_TREND**
- Setup: **TREND_CONTINUATION** LONG

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=USDJPY
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G4_SESSION_DATA: 36 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.261, allowed=[0.15, 1.2]
- PASS — G6_SPREAD: spread=0.003, maximum=0.03
- PASS — G7_SESSION_CLASSIFIED: type=BULLISH_TREND, ER=0.4789, close_location=0.6973
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_SETUP_DETECTED: setup=TREND_CONTINUATION LONG
- PASS — G10_STRUCTURAL_STOP: not applicable to this setup
- PASS — G11_STOPS_LEVEL: distance=0.065, broker minimum=0
- PASS — G12_VOLUME_BOUNDS: volume=0.12, allowed=[0.01, 100.0]
- PASS — G13_DAILY_RISK: used+proposed=4.90, limit=19.76
- PASS — G14_DRAWDOWN: drawdown=0.00%, maximum=15.00%
- PASS — G15_EXECUTION_WINDOW: now=2026-08-12T08:23:20.103114+00:00, window=[2026-08-12T07:00:00+00:00, 2026-08-12T09:00:00+00:00)

## Proposed signal — manual execution only

- Direction: LONG
- Signal candle close (UTC): 2026-08-12T07:00:00+00:00
- Entry: 159.391
- Stop loss: 159.326
- Initial risk (1R): 0.06499999999999773
- TP1 (75% off): 159.651 (4R)
- TP2 (runner): 159.716 (5R)
- Volume: 0.12 lots  (partial 0.09 / runner 0.03)
- Risk: $4.94 intended / $4.90 actual
- Signal expires: 2026-08-12T09:00:00+00:00
- Estimated cost: 0.077R  ->  net TP1 3.92R, net TP2 4.92R (gross 5.0R)

### Management sequence

1. Open the position with the original stop.
2. At +4R (159.651): close 75% and move the remaining stop to entry (159.391).
3. Exit the remainder at 5R (159.716).
4. Never move the initial stop farther away.
5. Do not re-enter this setup after the trade completes or is stopped.

## Reason codes

`TREND_SESSION` `MIDPOINT_RETRACEMENT`

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

# SSPF v2.2 Unified Trade Ticket

- Status: **NO_TRADE**
- Analysis ID: `c48291226c2c`
- Timestamp (UTC): 2026-08-10T13:37:17.065579+00:00
- Symbol: EURUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.15516 / 1.15517 / 1.0000000000065512e-05
- Session High / Low: 1.15655 / 1.1548
- Range / Midpoint: 0.0017499999999999183 / 1.155675
- Efficiency Ratio: 0.13381995133814864 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=EURUSD
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.00175, required=0.0004
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BULLISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.00044, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.22
- PASS — G10_DAILY_RISK: used+proposed=9.68, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- FAIL — G12_EXECUTION_WINDOW: now=13:37:17 UTC

## Proposed limit order — manual execution only

- Type: BUY_LIMIT
- Volume: 0.22 lots
- Entry: 1.1548
- Protected SL: 1.15436
- Actual R: 0.00043999999999999595
- Take Profit: 1.157 (5R)
- Partial Target: close 75% at 1.15655 (3.98R), then manually move SL to breakeven
- Intended / Actual Risk: $9.88 / $9.68
- Expiry: 2026-08-10T11:00:00+00:00

## Rejection reasons

- G12_EXECUTION_WINDOW: now=13:37:17 UTC

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

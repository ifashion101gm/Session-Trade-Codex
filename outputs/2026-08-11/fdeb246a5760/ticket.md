# SSPF v2.2 Unified Trade Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `fdeb246a5760`
- Timestamp (UTC): 2026-08-11T09:07:14.042956+00:00
- Symbol: USDJPY
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 159.361 / 159.364 / 0.0030000000000143245
- Session High / Low: 159.377 / 158.918
- Range / Midpoint: 0.4590000000000032 / 159.1475
- Efficiency Ratio: 0.16666666666667437 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=USDJPY
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=2s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.459, required=0.12
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BULLISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.115, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.13
- PASS — G10_DAILY_RISK: used+proposed=9.41, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=09:07:14 UTC

## Proposed limit order — manual execution only

- Type: BUY_LIMIT
- Volume: 0.13 lots
- Entry: 158.918
- Protected SL: 158.803
- Actual R: 0.1150000000000091
- Take Profit: 159.493 (5R)
- Partial Target: close 75% at 159.377 (3.99R), then manually move SL to breakeven
- Intended / Actual Risk: $9.88 / $9.41
- Expiry: 2026-08-11T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

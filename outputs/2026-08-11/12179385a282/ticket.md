# SSPF v2.2 Unified Trade Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `12179385a282`
- Timestamp (UTC): 2026-08-11T10:22:23.688797+00:00
- Symbol: EURUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.15336 / 1.15337 / 1.0000000000065512e-05
- Session High / Low: 1.1549800000000001 / 1.15318
- Range / Midpoint: 0.0018000000000000238 / 1.15408
- Efficiency Ratio: 0.29809725158563916 → RANGE
- Session Bias: BEARISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=EURUSD
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=6s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.0018, required=0.0004
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BEARISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.00045, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.21
- PASS — G10_DAILY_RISK: used+proposed=9.45, limit=19.76
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=10:22:23 UTC

## Proposed limit order — manual execution only

- Type: SELL_LIMIT
- Volume: 0.21 lots
- Entry: 1.1549800000000001
- Protected SL: 1.1554300000000002
- Actual R: 0.00045000000000006146
- Take Profit: 1.15273 (5R)
- Partial Target: close 75% at 1.15318 (4.00R), then manually move SL to breakeven
- Intended / Actual Risk: $9.88 / $9.45
- Expiry: 2026-08-11T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

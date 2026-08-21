# SSPF v2.2 Trade Analysis Ticket

- Status: **APPROVED_FOR_MANUAL_ENTRY**
- Analysis ID: `b372652248fe`
- Timestamp (UTC): 2026-08-10T08:08:16.837861+00:00
- Symbol: EURUSD
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 1.15616 / 1.15617 / 9.999999999843467e-06
- Session High / Low: 1.1562000000000001 / 1.1548
- Range / Midpoint: 0.0014000000000000679 / 1.1555
- Efficiency Ratio: 0.12903225806448057 → RANGE
- Session Bias: BEARISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=EURUSD
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=0.0014, required=0.0004
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BEARISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=0.00035, minimum=0
- PASS — G9_VOLUME_BOUNDS: volume=0.14
- PASS — G10_DAILY_RISK: used+proposed=4.90, limit=9.88
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=08:08:16 UTC

## Proposed limit order — manual execution only

- Type: SELL_LIMIT
- Volume: 0.14 lots
- Entry: 1.1562000000000001
- Protected SL: 1.1565500000000002
- Actual R: 0.0003500000000000725
- Take Profit: 1.1544500000000002 (5R)
- Intended / Actual Risk: $4.94 / $4.90
- Expiry: 2026-08-10T11:00:00+00:00

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

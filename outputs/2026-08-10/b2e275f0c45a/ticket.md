# SSPF v2.2 Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `b2e275f0c45a`
- Timestamp (UTC): 2026-08-10T08:08:55.152284+00:00
- Symbol: XAUUSD.crp
- Account: DEMO `****985` | Balance: $987.82
- Bid / Ask / Spread: 4353.98 / 4354.24 / 0.2600000000002183
- Session High / Low: 4359.69 / 4313.39
- Range / Midpoint: 46.29999999999927 / 4336.54
- Efficiency Ratio: 0.056849128540301254 → RANGE
- Session Bias: BULLISH
- Sweep: NO
- Setup: RANGE

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985
- PASS — G3_UNIVERSE: symbol=XAUUSD.crp
- PASS — G0_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G2_DATA_INTEGRITY: valid session and fresh tick
- PASS — G4_RANGE_FLOOR: range=46.3, required=10.4
- PASS — G5_BREACH_QUALITY: qualified or not required
- PASS — G6_BIAS_AGREEMENT: bias=BULLISH, setup=RANGE
- PASS — G7_STOP_PROTECTION: protected
- PASS — G8_STOPS_LEVEL: distance=11.575, minimum=0
- FAIL — G9_VOLUME_BOUNDS: profit calculation or volume invalid
- PASS — G10_DAILY_RISK: used+proposed=4.94, limit=9.88
- PASS — G11_DRAWDOWN: drawdown=0.00%
- PASS — G12_EXECUTION_WINDOW: now=08:08:55 UTC

## Proposed limit order — manual execution only

- Type: BUY_LIMIT
- Volume: 0.0 lots
- Entry: 4313.39
- Protected SL: 4301.8150000000005
- Actual R: 11.574999999999818
- Take Profit: 4371.265 (5R)
- Intended Risk: $4.94
- Expiry: 2026-08-10T11:00:00+00:00

## Rejection reasons

- G9_VOLUME_BOUNDS: profit calculation or volume invalid

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

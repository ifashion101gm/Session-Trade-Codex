# ASIAN_SESSION_V1 v1.0 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `e60e4b990616`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `f10cfb4cb99a1bd8`)
- Symbol: EURUSD
- Trading date: 2026-08-25
- Timestamp (UTC): 2026-08-25T18:13:12.569255+00:00
- Timestamp (Myanmar): 2026-08-26 00:43 MMT
- Asian session: 2026-08-25T00:00:00+00:00 → 2026-08-25T07:00:00+00:00
- Last closed execution candle: 2026-08-25T15:45:00Z
- Account: DEMO `*****746` | Equity: $999.70
- Bid / Ask / Spread: 1.16737 / 1.1675 / 0.00013

## Asian range (locked)

- High / Low: 1.16704 / 1.16506
- Range: 0.001980000000000093
- Midpoint: 1.16605
- Quartiles: 1.165555 / 1.1665450000000002
- Risk unit R (25% of range): 0.0004950000000000232
- Efficiency ratio: 0.7676767676767144 · Close location: 0.08080808080804569
- Session type: **BEARISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VantageMarkets-Demo, login=*****746 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=EURUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=11s
- PASS — G4_SESSION_DATA: 28 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00198, allowed=[0.0015, 0.012]
- PASS — G6_SPREAD: spread=0.00013, maximum=0.0003
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.7677, close_location=0.0808
- FAIL — G8_SESSION_QUOTA: taken=1, allowed=1

## Reason codes

`TREND_SESSION` `TRADE_ALREADY_TAKEN` `MAX_SESSION_TRADES_EXCEEDED`

## Rejection reasons

- G8_SESSION_QUOTA: taken=1, allowed=1

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

# ASIAN_SESSION_V1 v1.0 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `4dbeb87685b1`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `f10cfb4cb99a1bd8`)
- Symbol: GBPUSD
- Trading date: 2026-08-25
- Timestamp (UTC): 2026-08-25T15:53:37.843414+00:00
- Timestamp (Myanmar): 2026-08-25 22:23 MMT
- Asian session: 2026-08-25T00:00:00+00:00 → 2026-08-25T07:00:00+00:00
- Last closed execution candle: 2026-08-25T15:30:00Z
- Account: DEMO `*****746` | Equity: $999.70
- Bid / Ask / Spread: 1.36361 / 1.36376 / 0.00015

## Asian range (locked)

- High / Low: 1.36399 / 1.36212
- Range: 0.0018700000000000383
- Midpoint: 1.3630550000000001
- Quartiles: 1.3625875 / 1.3635225
- Risk unit R (25% of range): 0.0004675000000000096
- Efficiency ratio: 0.5294117647058963 · Close location: 0.304812834224571
- Session type: **BEARISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VantageMarkets-Demo, login=*****746 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=7s
- PASS — G4_SESSION_DATA: 28 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00187, allowed=[0.0018, 0.015]
- PASS — G6_SPREAD: spread=0.00015, maximum=0.0004
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.5294, close_location=0.3048
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 35 closed execution candle(s)

## Reason codes

`TREND_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 35 closed execution candle(s)

## Warnings

- Trend setup cancelled: 2026-08-25T07:00:00+00:00 violated the opposite quartile

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

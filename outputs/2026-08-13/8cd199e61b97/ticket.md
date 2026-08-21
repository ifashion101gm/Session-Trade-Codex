# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `8cd199e61b97`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: GBPUSD
- Trading date: 2026-08-13
- Timestamp (UTC): 2026-08-13T10:23:05.021605+00:00
- Timestamp (Myanmar): 2026-08-13 16:53 MMT
- Asian session: 2026-08-13T00:00:00+00:00 → 2026-08-13T08:00:00+00:00
- Last closed execution candle: 2026-08-13T10:00:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.3497 / 1.34971 / 1e-05

## Asian range (locked)

- High / Low: 1.35007 / 1.3474300000000001
- Range: 0.0026399999999999757
- Midpoint: 1.3487500000000001
- Quartiles: 1.34809 / 1.3494100000000002
- Risk unit R (25% of range): 0.0006599999999999939
- Efficiency ratio: 0.5454545454545914 · Close location: 0.3219696969696224
- Session type: **BEARISH_TREND**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=2s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00264, allowed=[0.0018, 0.015]
- PASS — G6_SPREAD: spread=1e-05, maximum=0.00035
- PASS — G7_SESSION_CLASSIFIED: type=BEARISH_TREND, ER=0.5455, close_location=0.3220
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 9 closed execution candle(s)

## Reason codes

`TREND_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 9 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

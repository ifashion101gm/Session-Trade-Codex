# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `769bd9c5ecd8`
- Strategy: SSPF_V2_2 v2.2 (config `8ce0fd901f3091e0`)
- Symbol: EURUSD
- Trading date: 2026-08-13
- Timestamp (UTC): 2026-08-13T10:22:46.731451+00:00
- Timestamp (Myanmar): 2026-08-13 16:52 MMT
- Asian session: 2026-08-13T00:00:00+00:00 → 2026-08-13T08:00:00+00:00
- Last closed execution candle: 2026-08-13T10:00:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.15365 / 1.15366 / 1e-05

## Asian range (locked)

- High / Low: 1.15314 / 1.15118
- Range: 0.0019599999999999618
- Midpoint: 1.15216
- Quartiles: 1.1516700000000002 / 1.15265
- Risk unit R (25% of range): 0.0004899999999999904
- Efficiency ratio: 0.10204081632652136 · Close location: 0.7091836734694028
- Session type: **RANGE**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=EURUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=3s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- PASS — G5_RANGE_BOUNDS: range=0.00196, allowed=[0.0015, 0.012]
- PASS — G6_SPREAD: spread=1e-05, maximum=0.0003
- PASS — G7_SESSION_CLASSIFIED: type=RANGE, ER=0.1020, close_location=0.7092
- PASS — G8_SESSION_QUOTA: taken=0, allowed=1
- PASS — G9_NEWS_FILTER: no relevant high-impact event in blocked window
- FAIL — G10_SETUP_DETECTED: no qualifying setup in 9 closed execution candle(s)

## Reason codes

`RANGE_SESSION` `NO_QUALIFYING_SETUP`

## Rejection reasons

- G10_SETUP_DETECTED: no qualifying setup in 9 closed execution candle(s)

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

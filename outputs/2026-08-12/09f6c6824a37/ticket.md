# ASIAN_SESSION_V1 v1.0 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `09f6c6824a37`
- Strategy: ASIAN_SESSION_V1 v1.0 (config `936249f5ee059177`)
- Symbol: GBPUSD
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T08:23:19.985529+00:00
- Timestamp (Myanmar): 2026-08-12 14:53 MMT
- Asian session: 2026-08-11T22:00:00+00:00 → 2026-08-12T07:00:00+00:00
- Last closed execution candle: 2026-08-12T08:00:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.3510499999999999 / 1.35106 / 1e-05

## Asian range (locked)

- High / Low: 1.35114 / 1.3501699999999999
- Range: 0.0009700000000001374
- Midpoint: 1.350655
- Quartiles: 1.3504125 / 1.3508974999999999
- Risk unit R (25% of range): 0.00024250000000003435
- Efficiency ratio: 0.02061855670093417 · Close location: 0.7422680412370638
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G4_SESSION_DATA: 36 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=0.00097, allowed=[0.0018, 0.015]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=0.00097, allowed=[0.0018, 0.015]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

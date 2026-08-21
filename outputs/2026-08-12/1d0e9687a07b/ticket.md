# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `1d0e9687a07b`
- Strategy: SSPF_V2_2 v2.2 (config `47c20587123f3296`)
- Symbol: GBPUSD
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T09:06:26.266186+00:00
- Timestamp (Myanmar): 2026-08-12 15:36 MMT
- Asian session: 2026-08-12T00:00:00+00:00 → 2026-08-12T08:00:00+00:00
- Last closed execution candle: 2026-08-12T08:45:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.35141 / 1.3514300000000001 / 2e-05

## Asian range (locked)

- High / Low: 1.35115 / 1.3501699999999999
- Range: 0.000980000000000203
- Midpoint: 1.35066
- Quartiles: 1.350415 / 1.350905
- Risk unit R (25% of range): 0.00024500000000005073
- Efficiency ratio: 0.09183673469378045 · Close location: 0.6734693877550697
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=GBPUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=0.00098, allowed=[0.0018, 0.015]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=0.00098, allowed=[0.0018, 0.015]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

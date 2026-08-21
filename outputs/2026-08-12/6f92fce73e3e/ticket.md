# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `6f92fce73e3e`
- Strategy: SSPF_V2_2 v2.2 (config `47c20587123f3296`)
- Symbol: EURUSD
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T08:53:15.598603+00:00
- Timestamp (Myanmar): 2026-08-12 15:23 MMT
- Asian session: 2026-08-12T00:00:00+00:00 → 2026-08-12T08:00:00+00:00
- Last closed execution candle: 2026-08-12T08:30:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 1.15387 / 1.15388 / 1e-05

## Asian range (locked)

- High / Low: 1.1544699999999999 / 1.15322
- Range: 0.0012499999999999734
- Midpoint: 1.153845
- Quartiles: 1.1535324999999998 / 1.1541575
- Risk unit R (25% of range): 0.00031249999999999334
- Efficiency ratio: 0.4960000000000625 · Close location: 0.41600000000006965
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=EURUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=1s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=0.00125, allowed=[0.0015, 0.012]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=0.00125, allowed=[0.0015, 0.012]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

# SSPF_V2_2 v2.2 — Trade Analysis Ticket

- Status: **NO_TRADE**
- Analysis ID: `d9b750ea08d8`
- Strategy: SSPF_V2_2 v2.2 (config `47c20587123f3296`)
- Symbol: XAUUSD
- Trading date: 2026-08-12
- Timestamp (UTC): 2026-08-12T10:53:26.171960+00:00
- Timestamp (Myanmar): 2026-08-12 17:23 MMT
- Asian session: 2026-08-12T00:00:00+00:00 → 2026-08-12T08:00:00+00:00
- Last closed execution candle: 2026-08-12T09:00:00Z
- Account: DEMO `****985` | Equity: $987.82
- Bid / Ask / Spread: 4410.79 / 4411.05 / 0.26

## Asian range (locked)

- High / Low: 4416.04 / 4366.47
- Range: 49.56999999999971
- Midpoint: 4391.255
- Quartiles: 4378.8625 / 4403.6475
- Risk unit R (25% of range): 12.392499999999927
- Efficiency ratio: 0.7010288480936091 · Close location: 0.8022997780915828
- Session type: **UNCERTAIN**
- Setup: **NONE**

## Gate evaluation

- PASS — G1_ENVIRONMENT: account=demo, server=VTMarkets-Demo, login=****985 via exact allowlist (gateway verified)
- PASS — G2_UNIVERSE: symbol=XAUUSD
- PASS — G3_BROKER_CLOCK: verified UTC+3:00, normalized tick age=0s
- PASS — G4_SESSION_DATA: 32 contiguous closed candles
- FAIL — G5_RANGE_BOUNDS: range=49.57, allowed=[2, 25]

## Reason codes

`INVALID_ASIAN_RANGE`

## Rejection reasons

- G5_RANGE_BOUNDS: range=49.57, allowed=[2, 25]

Analysis only. Levels are proposals, not automated signals. Verify against your own chart, size to your own risk tolerance, and place the order manually.

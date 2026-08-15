# Configuration Reference — ASIAN_SESSION_V1

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

Two files drive behaviour. `config/strategy.yaml` is validated on load: unknown keys, missing
keys, and internally inconsistent values all raise rather than being silently accepted.

Active hash: **`2530b751134fbf6e`**

---

## 1. Hash impact — read this first

`StrategyConfig.hash` is `sha256` of the entire raw YAML mapping, truncated to 16 characters.
Every key contributes. Stage 1 enforces an exact hash match, so **any edit invalidates every
previously generated artifact for conformance purposes.**

Change one value at a time, record the hash before and after, and treat the change as starting a
new evidence set. Superseded hashes so far: `fddb7465a73fd724`, `92279f3d42d32fc3` (both SSPF
v2.2, a different contract entirely).

## 2. Identity

| Key | Value | Effect |
|---|---|---|
| `mode` | `analysis_only` | Any other value raises at load. The only hard-coded refusal. |
| `strategy_id` | `ASIAN_SESSION_V1` | Stamped on every artifact; Stage 1 and Stage 2 both check it |
| `contract_version` | `"1.0"` | Stops v2.2 evidence being reused under the new contract |

## 3. Environment

| Key | Value | Effect |
|---|---|---|
| `expected_account_suffix` | `"985"` | G1. Quote it — YAML would read `985` as an integer and `.endswith` would fail |
| `expected_server` | `VTMarkets-Demo` | G1, exact match. With the demo check, this is what keeps a live account out |

## 4. Time model

| Key | Value | Effect |
|---|---|---|
| `session_start_utc` | `"22:00"` | Asian open, inclusive. Crosses midnight; the trading date is the date the session **ends** |
| `session_end_utc` | `"07:00"` | Asian close, exclusive. Levels lock here and never change |
| `session_candles` | `36` | 9 h ÷ 15 min. **Cross-checked at load** against the window — a mismatched pair raises |
| `execution_start_utc` | `"07:00"` | G15 lower bound |
| `execution_end_utc` | `"16:00"` | G15 upper bound and the signal expiry |
| `post_session_candles` | `36` | 9 h ÷ 15 min, also cross-checked |
| `maximum_tick_age_seconds` | `300` | G3. Age must fall in `[-5, 300]`; the −5 s tolerance absorbs clock skew |

## 5. Classification — research parameters

| Key | Value | Effect |
|---|---|---|
| `efficiency_ratio_threshold` | `0.35` | `ER <= threshold` → RANGE. ER here is `net move ÷ range`, **not** the Kaufman path-length ratio used by the superseded contract |
| `close_location_trend` | `0.65` | Bullish trend needs `close_location >= 0.65`; bearish needs `<= 0.35` |

The specification states plainly that these are research parameters, not proven optimal values.
Lock them before each backtest and never change them after seeing out-of-sample results.

## 6. Setup geometry

| Key | Value | Effect |
|---|---|---|
| `stop_range_fraction` | `0.25` | `R = 0.25 × asian_range`. The **exact** stop distance for every setup — never a floor, never widened |
| `partial_target_r` | `4.0` | TP1, where 75% comes off |
| `final_target_r` | `5.0` | TP2, the runner. Must exceed `partial_target_r` |
| `partial_close_percent` | `75.0` | Printed in the management sequence |
| `midpoint_zone_low_fraction` | `0.45` | Trend retracement zone floor |
| `midpoint_zone_high_fraction` | `0.55` | Trend retracement zone ceiling |
| `rejection_quality_fraction` | `0.50` | Sweep candle must close in the far half of its own range |

### Provisional — require sign-off

The specification names these but gives no values. They are set conservatively and flagged;
they are not the engine's to keep.

| Key | Provisional | Effect |
|---|---|---|
| `sweep_buffer_fraction` | `0.02` × range | How far beyond a boundary counts as a sweep |
| `stop_buffer_fraction` | `0.02` × range | How far beyond the extreme the fixed stop must sit |
| `touch_tolerance_fraction` | `0.05` × range | Boundary-touch tolerance for range rejection |

`sweep_buffer` and `stop_buffer` together determine how often a sweep is tradeable at all — see
`STRATEGY_SPEC.md` §7. Raising either narrows the feasible band.

## 7. Risk

| Key | Value | Effect |
|---|---|---|
| `risk_percent_per_trade` | `0.5` | Percent of **equity** (not balance) |
| `daily_risk_limit_percent` | `2.0` | Ceiling on today's realised loss plus today's open risk |
| `maximum_drawdown_percent` | `15.0` | G14 threshold on peak-to-trough from closed matches |
| `maximum_trades_per_symbol_session` | `1` | Enforced by G8 |
| `maximum_open_positions_per_symbol` | `1` | Recorded; enforcement rides on the session quota |

## 8. Symbols

Each entry defines an exact broker symbol. Anything absent fails G2. **Gold must not reuse FX
limits** — the ranges below are on different scales for that reason.

```yaml
symbols:
  EURUSD:     { pip_size: 0.0001, minimum_range: 0.0015, maximum_range: 0.0120, maximum_spread: 0.00030 }
  GBPUSD:     { pip_size: 0.0001, minimum_range: 0.0018, maximum_range: 0.0150, maximum_spread: 0.00035 }
  USDJPY:     { pip_size: 0.01,   minimum_range: 0.150,  maximum_range: 1.200,  maximum_spread: 0.030 }
  XAUUSD.crp: { pip_size: 0.01,   minimum_range: 2.00,   maximum_range: 25.00,  maximum_spread: 0.60 }
```

Range and spread limits are **provisional** and need the same sign-off as §6. USDJPY is retained
pending an answer to Q2 in `STRATEGY_SPEC.md` §8 — the specification lists only EURUSD, GBPUSD and
XAUUSD.

## 9. `config/lifecycle.json`

Consumed only by the release gate; it never affects analysis.

| Key | Value | Effect |
|---|---|---|
| `strategy_id` / `contract_version` | `ASIAN_SESSION_V1` / `1.0` | Stage 2 rejects any record from another contract |
| `require_demo_account` | `true` | Artifact must record a demo account |
| `require_exact_config_hash` | `true` | Artifact hash must equal the live hash |
| `require_all_gates_in_ticket` | `true` | Every gate name in the JSON must appear in `ticket.md` |
| `require_disclaimer` | `true` | `ticket.md` must contain `render.DISCLAIMER` verbatim |
| `require_reason_codes` | `true` | Every artifact must carry at least one reason code |
| `minimum_total_trades` | `50` | Records supplied, before filtering |
| `minimum_out_of_sample_trades` | `30` | Records surviving eligibility |
| `minimum_expectancy_r` | `0.1` | Mean R |
| `minimum_profit_factor` | `1.2` | Infinite (no losses) is an explicit failure |
| `minimum_bootstrap_confidence` | `0.9` | Fraction of 2000 seeded resamples with positive mean |
| `maximum_drawdown_r` | `10.0` | Peak-to-trough of the cumulative R curve |
| `require_per_setup_breakdown` / `setups` | `true` / three setups | Backtest each setup separately — a profitable one can otherwise hide a losing one |

## 10. Changing configuration safely

1. Record the current hash:
   `python -c "from session_strategy.config import load_config; print(load_config().hash)"`
2. Change **one** value.
3. Run the tests — several load the live config and assert against real thresholds.
4. Record the new hash and note which artifacts it supersedes.
5. Treat evidence collected under the old hash as belonging to the old version.

Values that change what a setup *means*, not merely how often one appears: `session_start_utc`,
`session_end_utc`, `stop_range_fraction`, `partial_target_r`, `final_target_r`,
`efficiency_ratio_threshold`, `close_location_trend`, and the three buffer fractions.

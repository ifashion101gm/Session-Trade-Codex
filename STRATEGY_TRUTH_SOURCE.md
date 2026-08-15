# Session Trading Strategy Specification

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

Version: **3.0**  
Status: **Authoritative project contract**  
Source: Episode 18 session-trading workflow supplied by the user  
Updated: 2026-08-15

This specification governs the backtester, reports, reusable analysis skill, and
future live-execution code. Source rules are immutable unless the user explicitly
revises them. Quantitative definitions added for deterministic execution are
labelled as implementation rules.

Version 3.0 is the user's explicit classifier upgrade. Evidence created under
v2.23 used a different Asian window, classifier, and unconfirmed trend entry;
those database rows and reports are retained as legacy evidence and are not
conformance proof for v3.0 until replayed and revalidated.

## Validation protocol for source screenshots

Every screenshot validation follows this order:

1. Identify the screenshot date, symbol, timeframe, reference session, and entry
   session from visible labels and candle sequence.
2. Render the corresponding MT5 M15 candles in UTC and compare the completed
   reference-session path—not merely its high and low—with the screenshot.
3. If the reference candles materially differ, report a data/timezone mismatch;
   do not modify strategy logic to compensate.
4. If the reference candles are materially similar, treat a different setup,
   direction, entry, SL, or TP as an engine-classification/execution defect.
5. Refine only a general causal rule, rerun the screenshot date, and regress all
   earlier truth fixtures. Never add a date-specific outcome or price override.
6. Store a truth entry only after session data, setup branch, geometry, and the
   user-confirmed outcome agree.

## 1. Source decision workflow

1. Determine the directional bias: Bullish or Bearish.
2. Decide whether the completed reference session is a Range Session.
3. If Range = Yes, decide whether a valid sweep is available. Normally this is
   a sweep of the frozen reference range during the following execution session.
   For London → New York, a sweep completed inside the developing London session
   may also be carried forward after the London box freezes at 12:00 UTC.
4. Select exactly one branch:

| Decision | Setup |
| --- | --- |
| Range = Yes and Sweep = Yes | Sweep Setup |
| Range = Yes and Sweep = No | Range Setup |
| Range = No | Trend Setup |

## 2. Source setup rules

| Rule | Sweep Setup | Range Setup | Trend Setup |
| --- | --- | --- | --- |
| Entry | Sweep candle body | Session top/bottom | Confirmed 45–55% retracement, then midpoint |
| Stop distance | 25% of reference range | 25% of reference range | 25% of reference range |
| Full target | 5R | 5R | 5R |
| Management | Close 75% after one session-range move; move 25% runner to BE | Close 75% after one session-range move; move 25% runner to BE | Close 75% at 4R; move 25% runner to BE and target 5R |

For reference high `H`, low `L`, width `A = H − L`, risk `D = 0.25A`,
entry `E`, and direction sign `S` (`+1` long, `−1` short):

```text
Stop = E − S×D
TP5  = E + S×5D
```

No structural buffer may be added to `D` in a truth-strategy run.

## 3. Causal session cycles — implementation rule

All stored bars are normalized to UTC. Broker GMT+2/GMT+3 timestamps must be
converted before session construction.

| Cycle | Completed reference | Execution window | Reference used for all calculations |
| --- | --- | --- | --- |
| Asian → London | Asian 22:00 previous day–07:00 | London entry 07:00–16:00; management may continue | Asian high, low, width |
| London → New York | London morning 07:00–12:00 | New York 12:00–18:00 | Frozen London high, low, width |

The cycles overlap intentionally. A London-to-New-York decision at 12:00 cannot
use London candles after 12:00. Position management may continue to 22:00 UTC.
No future reference or execution candle may influence an earlier decision.

### London sweep carried into New York

For the London → New York cycle, inspect the completed 07:00–12:00 London bars
for a causal internal liquidity sweep. For each London candle, compare its high
and low only with London bars completed before it. A low/high breach of at least
1 pip followed by a close back inside the prior developing boundary is a Sweep
candidate; the normal wick-or-reversal-body confirmation still applies.

When no post-lock New York boundary signal has priority, carry the last confirmed
London sweep into New York as a pending Sweep Setup. Entry is the sweep candle's
outer body edge. Stop distance and 5R target use the final frozen London width.
This rule must never inspect a post-12:00 candle when constructing London levels
or selecting the carried sweep.

## 4. Deterministic signal definitions — implementation rule

### Bias

Establish one directional bias for the trading day using only M15 candles
closed by the Asian-session close at 07:00 UTC. Freeze that bias for both the
London and New York execution cycles; do not recalculate it from the London
move at 12:00 UTC.

At the 07:00 decision point:

1. Confirmed higher swing high plus higher swing low → Bullish.
2. Confirmed lower swing high plus lower swing low → Bearish.
3. A strong four-swing majority is also directional: three consecutive moves
   in one swing series plus a positive majority in the other series overrides
   one contrary pullback in the last pair.
4. If swing structure is inconclusive, compare the latest close with the mean of
   the previous closed M15 bars and disclose that fallback.

Bias must be stored with its evidence. It must not be reconstructed from future
price action or reversed between London and New York execution.

### Range versus Trend

Calculate reference-session efficiency from net displacement relative to the
completed high-low range:

```text
efficiency_ratio = abs(session close − session open) / (session high − session low)
close_location = (session close − session low) / (session high − session low)
```

- `efficiency_ratio ≤ 0.35` → Range.
- `efficiency_ratio > 0.35`, close location `≥ 0.65`, and close above open →
  Bullish Trend.
- `efficiency_ratio > 0.35`, close location `≤ 0.35`, and close below open →
  Bearish Trend.
- Every other geometry → Uncertain and no trade.

No opening-expansion, terminal-expansion, path-length, or external-bias override
may change this classification.

### Sweep candle

A completed M15 candle is a sweep only when:

- The boundary breach is at least 1 pip. This is a deterministic
  implementation threshold that filters sub-pip quote noise and applies in
  every entry mode.
- Short: its high breaches `H` by that threshold and its close returns below `H`.
- Long: its low breaches `L` by that threshold and its close returns above `L`.
- The sweep candle must open inside the relevant boundary. A candle that opens
  outside and merely re-enters the box is not a new sweep candle.
- Direction comes from the swept boundary: low reclaim → Long; high reclaim →
  Short. Daily bias is contextual and does not veto a counter-bias Sweep.
- Confirmation is either a rejection wick ratio greater than `0.35` or a candle
  body closing in the proposed reversal direction. The momentum gate may reject
  only a large body moving against the proposed trade; it must not reject an
  aligned reversal body merely because its wick is small.

A candle closing outside the reference range is a breakout, not a sweep.
The Sweep entry is the outer body edge:

- Short entry: `max(open, close)`.
- Long entry: `min(open, close)`.

### Range setup

If the reference is Range and no confirmed bias-aligned sweep has occurred when
a reference boundary setup becomes executable:

- Bias determines direction: Bullish → Long; Bearish → Short.
- Price location determines entry: use whichever reference boundary (`H` or `L`)
  first produces a valid setup.
- At the bias-direction breakout boundary (Bullish `H`, Bearish `L`), require the
  M15 candle to close outside the range in the bias direction.
- At the opposite support/resistance boundary (Bullish `L`, Bearish `H`), a touch
  is sufficient after Sweep precedence has been evaluated.
- If one M15 candle touches both boundaries, reject it as ambiguous.

Range entries are causal provisional signals. A later valid Sweep may also occur
in the same execution cycle and must remain eligible under the configured
multi-trade and circuit-breaker limits. Do not delete an earlier Range trade
because a Sweep becomes visible later; doing so would introduce lookahead.

Setup evaluation order on each closed M15 candle is:

1. Test for a completed, bias-aligned Sweep.
2. Once a boundary breach has closed back inside, keep the cycle on the Sweep
   branch while awaiting valid directional confirmation. Do not downgrade an
   intervening outside-close candle into a Range entry.
3. Before any reclaim has occurred, if no Sweep is confirmed on that candle,
   test whether either Range boundary was touched and enter in the frozen bias
   direction.
4. A Sweep signal always has precedence over a Range signal on the same candle.
5. Each reference boundary may execute at most one Range Setup per cycle. A stop
   and cooldown do not reactivate the same boundary order. A later distinct Sweep
remains eligible under the normal trade and circuit limits.

After the first valid Sweep selects the Sweep branch for a reference/execution
cycle, do not downgrade later signals in that cycle to Range Setup. Later
distinct Sweep signals remain eligible under the trade limit, cooldown, and
circuit-breaker rules.

### Trend setup

The Trend entry is not armed at the reference-session lock. During the execution
window, price must overlap the 45–55% equilibrium zone and a completed M15 candle
must close in the trend direction. A Bullish Trend is cancelled if an execution
candle trades below the lower quartile; a Bearish Trend is cancelled if an
execution candle trades above the upper quartile.

Only after that confirmation may the engine propose the frozen midpoint. A
historical simulation may fill that proposal only on a later candle; using the
confirmation candle itself as a retrospective midpoint fill is lookahead.

If the reference is Trend:

- Entry: `(H + L) / 2`.
- Direction: classified session direction.
- Leg A: 75% at 4R.
- Leg B: 25%; stop moves to breakeven after Leg A and the target is 5R.

## 5. Position management and R accounting

Sweep and Range setups:

1. Sweep Leg A exits after one complete reference-range move, normally at the
   opposite reference boundary when the body entry is near the swept boundary.
2. Range-breakout Leg A exits after one full reference-range projection from
   entry. Because risk is 25% of range, this projection equals 4R.
3. When Leg A fills, Leg B stop moves to entry (BE).
4. Leg B is 25% and targets the full 5R price.

`TP5_HIT` means the 5R runner price was touched. Because 75% exits earlier, the
position-weighted realized R is generally not +5R. Reports must show both:

- Runner target result (`TP5_HIT`, 5R price distance).
- Position-weighted gross and friction-adjusted R.

## 6. Operational backtest rules — implementation rule

- Timeframe: M15.
- Evaluate only closed candles.
- Same-bar SL/target ambiguity: stop-first.
- Spread gate: reject when spread exceeds 20% of stop distance.
- Slippage model: 0.2 pip round trip unless explicitly overridden.
- Maximum three executed trades per reference/execution cycle.
- After a stop: four M15-bar cooldown.
- Cycle lock: full TP5 hit or cumulative gross loss of −2R.
- Never hardcode an outcome or mark an untouched price as filled.
- Report unresolved positions and broker/source discrepancies explicitly.
- Every trade record and summary must show its source-flowchart path:
  `Bias → Range? → Sweep? → Setup`, followed by the applicable source entry,
  25%-range stop, 5R target, and management rules.
- Every row in `benchmarks/entry_database.csv` must store the same path and rule
  basis. `benchmarks/entry_database_report.md` is regenerated from that database
  to present all historical entries in Parameter / Result / Source Basis format.

These risk controls are not visible in the source flowchart and must remain
separately configurable during source-strategy validation.

## 7. User-confirmed truth benchmarks

Machine-readable fixtures: `benchmarks/truth_source_setups.json`.
Canonical entry inventory: `benchmarks/entry_database.csv`.

| Date | Cycle | Setup | Direction | Entry | Stop | TP5 | Confirmed outcome |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 2022-10-03 | Asian → London | Sweep | Short | 0.98342 | 0.9846725 | 0.9771575 | TP5 reached (+5R runner target) |
| 2022-10-03 | London → New York | Sweep | Short | 0.98181 | 0.9836775 | 0.9724725 | Stop loss (−1R) |

## 8. Chart-validated next-day benchmark

The October 4 chart and connected M15 history validate the repaired bullish
Range Setup:

| Date | Cycle | Setup | Direction | Entry | Stop | Leg A (4R) | TP5 | Outcome |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 2022-10-04 | London → New York | Range | Long | 0.99039 | 0.98911 | 0.99551 | 0.99679 | TP5_HIT at 15:00 UTC |
| 2022-10-05 | Asian → London | Range | Long | 0.99592 | 0.9950275 | 0.99949 | 1.0003825 | STOP_LOSS at 07:30 UTC (−1R) |

The 5R runner target was reached. With 75% closed at 4R and 25% at 5R,
position-weighted gross return is `+4.25R` before friction.

The October 5 case validates first-touched-boundary selection: bullish bias fixes
the Long direction, while price first touches the Asian low, so the Range entry
is placed at `L`. The same boundary cannot be re-entered later in that cycle.

### October 5 London → New York geometry validation

- Bias: Bearish; London path efficiency: `0.632`, classified Range under the
  calibrated `≤0.70` threshold.
- A 12:00 low pierce that closes back inside is not the bearish Range breakout.
- The 13:00 close below the frozen London low confirms the short Range entry.
- Entry `0.98995`; SL `0.99192`; Leg A `0.98207`; TP5 `0.98010`.
- Source-chart result: `TP5_HIT`; the image visibly trades through the plotted
  5R target. Position-weighted source result is `+4.25R` before friction.
- Connected-feed result: `END_WINDOW`, gross `+0.8376R` at 21:45 UTC.
- This is retained as `SOURCE_DATA_MISMATCH`: chart outcome and connected-feed
  outcome are separate evidence and neither may overwrite the other.

### October 6 Asian → London validation

- Bias: Bearish; reference: Asian `00:00–07:00` UTC.
- Setup: short Range entry at the first valid Asian-low boundary break.
- Signal `08:15` UTC; entry `0.98930`; SL `0.9901325`.
- Risk `8.325` pips; Leg A `0.98597`; TP5 `0.9851375`.
- Source chart and connected feed both record `STOP_LOSS` at `09:15` UTC,
  gross `−1R`. Geometry and outcome fully match.

### October 6 London → New York correction

- Bias: Bearish; reference: London `07:00–12:00` UTC.
- London high/low: `0.99207 / 0.98580`; range: `62.7` pips.
- Session state: `BEARISH_TREND`, not Range. The session first makes its high
  during the opening quarter, subsequently makes its low during the final
  quarter, and locks in the bottom 17% of its range. This terminal expansion
  overrides the low whole-path efficiency caused by the initial reversal.
- Source branch: `RANGE?=NO -> TREND_SETUP`.
- Frozen London midpoint entry: `0.988935`.
- Exact 25% stop distance: `15.675` pips; short stop: `0.9905025`.
- Exact 5R target: `0.9810975`; 75% management level: `0.982665` (4R).
- Connected UTC feed result: `NO_FILL`; New York's maximum `0.98823` does not
  retrace to the frozen midpoint. Therefore the screenshot and connected feed
  remain a source-data/session-alignment mismatch requiring separate evidence.

### October 7 Asian → London validation

- The screenshot timestamp is displayed in Myanmar local time; the completed
  reference box maps to the Asian `00:00–07:00` UTC session.
- Bias: Bearish; session state: Range; no aligned Sweep precedes the entry.
- Source branch: `RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP`.
- Asian high/low: `0.98118 / 0.97657`; range: `46.1` pips.
- Short entry `0.98118`; exact 25% stop `0.9823325` (`11.525` pips).
- Leg A `0.97657`; exact 5R target `0.9754175`.
- Source chart and connected feed both record `TP5_HIT` at the 12:30 UTC
  selloff. Position-weighted gross result is `+4.25R`.

### October 7 London → New York validation

- Bias: Bearish; London reference `07:00–12:00` UTC is Range.
- London high/low: `0.98168 / 0.97815`; range: `35.3` pips.
- The 12:30 UTC candle closes below the London low, so it is a continuation
  breakout rather than a sweep rejection.
- Source branch: `RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP`.
- Short boundary entry `0.97815`; exact 25% stop `0.9790325` (`8.825` pips).
- Leg A `0.97462`; exact 5R target `0.9737375`.
- Source chart and connected feed both record `TP5_HIT` on the 12:45 UTC bar.
  Position-weighted gross result is `+4.25R`.

### October 20 Asian → London screenshot validation

- The source screenshot is EURUSD M15 on October 20, 2022. Its visible Asian
  candle path, London midpoint retracement, consolidation, and 10:30–11:00 UTC
  bullish expansion match the connected MT5 history.
- Reference: Asian `00:00–07:00` UTC; execution: London `07:00–16:00` UTC.
- Bias: Bullish; session state: `BULLISH_TREND`; source branch:
  `RANGE?=NO -> TREND_SETUP`.
- Asian high/low: `0.97942 / 0.97544`; range: `39.8` pips.
- Midpoint long entry `0.97743`; exact 25% stop `0.976435` (`9.95` pips).
- Leg A `0.98141` at 4R; exact 5R target `0.982405`.
- The order is active at the 07:00 lock and the 07:00 candle trades through the
  midpoint. MT5 reaches TP5 on the 11:00 candle, matching the screenshot.
- Position-weighted gross result is `+4.25R`; friction-adjusted result is
  `+4.129R` under the documented spread/slippage model.
- The previous October 17 London-to-New-York interpretation was invalid and was
  removed from the entry database before this result was stored.

### October 20 London → New York screenshot validation

- The second source screenshot is the October 20 London → New York cycle. The
  user confirms that it is a Range Setup, not a Trend Setup.
- Frozen London high/low: `0.98289 / 0.97716`; range: `57.3` pips; frozen daily
  bias: Bullish.
- Source branch: `RANGE?=YES -> SWEEP?=NO -> RANGE_SETUP`; direction: Long;
  source entry is the London low boundary at `0.97716`.
- Exact 25% stop: `0.9757275` (`14.325` pips); one-range/4R management level:
  `0.98289`; exact 5R target: `0.9843225`.
- The source entry is never filled. Its confirmed source outcome is
  `MISSED_TRADE`; the later move above the plotted 5R level cannot be counted.
- The connected MT5 execution path confirms the missed entry: its New York
  minimum is `0.97798`, 8.2 pips above the source boundary order, so that exact
  long order is also `UNFILLED`. The connected bars later confirm a distinct
  short Sweep which stops out; this must not overwrite the screenshot Range
  result.
- Classification and price formulas already follow the source workflow. No
  strategy refinement is required for this missed source order.

### October 21 Asian → London screenshot validation

- The source screenshot candle path matches EURUSD M15 on October 21, 2022.
  The user confirms `Range Setup` and a `−1R` result.
- Reference: Asian `00:00–07:00` UTC; high/low `0.97835 / 0.97618`; range
  `21.7` pips; frozen bias: Bearish.
- The 07:00 candle breaches the Asian low by only `0.7` pip. It is below the
  configured 1-pip liquidity threshold and must not select the Sweep branch.
- The 07:15 candle touches the Asian high, selecting the bearish Range short at
  `0.97835` under the opposite-boundary touch rule.
- Exact 25% stop: `0.9788925` (`5.425` pips); Leg A: `0.97618`; exact 5R target:
  `0.9756375`.
- The 07:15 trigger candle also reaches the stop. Under stop-first same-bar
  handling, source and connected-feed outcomes are both `STOP_LOSS (−1R)`.
- Engine refinement: the existing 1-pip minimum breach now applies in all entry
  modes. Previously body mode silently used a zero threshold and mislabeled
  sub-pip noise as a Sweep.

The source benchmark and connected-broker simulation are separate evidence
layers. If bars disagree, preserve both and flag `SOURCE_DATA_MISMATCH`.

## 9. Regression status after Range Setup repair

- October 3 Asian → London short Sweep geometry: **PASS**.
- October 3 London → New York short Sweep geometry and −1R: **PASS**.
- October 4 London → New York bullish Range geometry and TP5: **PASS**.
- October 5 Asian → London bullish Range geometry and −1R: **PASS**.
- October 6 Asian → London bearish Range geometry and −1R: **PASS**.
- October 6 London → New York classification: **CORRECTED TO TREND**; the
  connected UTC feed does not fill the required midpoint entry.
- October 7 Asian → London bearish Range geometry and TP5: **PASS**.
- October 7 London → New York bearish Range geometry and TP5: **PASS**.
- The October 3 Asian → London cycle additionally produces a causal 09:30 Range
  trade under the new boundary rule. The later 15:15 Sweep remains unchanged.

See `outputs/strategy_regression_validation.md` for the run evidence.

## 10. Acceptance requirements

A strategy change is valid only when:

1. Entry, stop, target, partial, and BE prices follow Sections 2–5.
2. Every decision uses data available at that timestamp.
3. Both October 3 benchmark geometries and the October 4–5 Range geometries
   remain reproducible.
4. Any outcome difference is traced to bars, collision policy, or friction—not
   corrected by date-specific conditions.
5. Automated tests and the reusable skill validator pass.

The session classifier regression evidence is maintained in
`outputs/session_classifier_regression_audit.md`. Its current truth-labelled
score is 7/7, but only one labelled Trend cycle is available; this is regression
coverage rather than proof of out-of-sample classifier accuracy.

## 11. Prohibited silent deviations

- Stop buffers beyond 25% of the reference range.
- Reference-boundary entry for Sweep Setup.
- Targets other than exactly 5R.
- Forced Range classification for every session.
- Using the full London day to make a 12:00 New York decision.
- Counter-bias trades without a separately named experiment.
- Hardcoded dates, prices, wins, or losses in the trading engine.
- Describing an implementation assumption as a source rule.
Terminal expansion is Trend when the counter-direction extreme forms in the
opening quarter, the opposite extreme forms in the final 35% of the reference,
and the session closes in the terminal 35% of its range. This recognizes a
directional session whose whole-path efficiency is reduced by its opening
reversal or later overlap.

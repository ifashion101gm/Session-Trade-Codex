# SSPF v2.2 — Project Audit

> **SUPERSEDED 2026-08-15.** Written against a previous contract. The active contract is
> `SESSION_FLOW_V1` — see **`STATUS.md`** for current state and `SESSION_FLOW_V1_SPEC.md`
> for the rules. Retained for its analysis; do not act on its parameters.

> **⚠ Written against SSPF v2.2, superseded 2026-08-11.** The project migrated to
> **ASIAN_SESSION_V1** — different session window (22:00–07:00 UTC), classification metric,
> entry model, partial target and risk fraction. Findings below that describe v2.2 behaviour are
> retained as history, not as a description of the current engine. Items still live under V1 are
> listed in `STAGE1_QUALIFICATION.md`: **A1** (conformance status model), **A3** (config
> snapshot), **A4/A5** (journal reconciliation — partially repaired), **A6** (broker-clock failure
> writes no artifact), **A8** (orphan chart script), **A10** (automations out of tree),
> **A11** (test fixtures), **A12–A16** (traceability and hygiene), **A25** (connector setting),
> **A27** (no backtest engine). Current strategy conformance is in `STRATEGY_SPEC.md` §6.


Audit date: **2026-08-11** · Auditor: program-management review · Scope: full project tree
Method: full source read, static cross-check of docs against code, test-suite execution, and
targeted reproduction scripts for suspected defects.

**No code was changed by this audit.** Every finding below is a logged item; §5 is the
remediation backlog.

---

## 1. Summary

| | |
|---|---|
| Status | **Amber** — the engine now conforms to its source of truth on **12 of 12** checkable rules; the remaining blockers are release-gate and traceability defects, not strategy deviations |
| Lifecycle stage | Stage 1 (Recommendation Correctness) — 4 of 8 exit criteria still blocked |
| Alignment score | **75 / 100** (see §1.2) |
| Test suite | **31 tests, 31 pass** (`python -m unittest discover -s tests -v`) |
| Config hash | **`92279f3d42d32fc3`** (was `fddb7465a73fd724` before the D1/D4 fixes) |
| Findings | 4 High · 10 Medium · 8 Low · 4 fixed (A20, A21, A26; A25 partial) · 1 resolved (A2) |
| Purpose | The project **applies the trader's strategy**; it does not create one. Deviations from the trader's specification are defects even when they look like improvements. |

> **Revision 2, 2026-08-11.** Findings A20–A25 were added after an external review was
> adjudicated against the source. That adjudication is in `REVIEW_RESPONSE.md`.
>
> **Revision 3, 2026-08-11.** The trader-supplied Session Trading Strategy diagram was adopted as
> the source of truth for setup definitions and transcribed into `STRATEGY_SPEC.md` §0. This
> added **A26**, confirmed A21 as a specification deviation rather than merely an unbounded
> control, and **partly reversed A23** — the code's session-boundary partial is correct and the
> external reviewer's 4R prescription was not.
>
> **Revision 4, 2026-08-11.** The complete diagram was supplied; the copy used in revision 3 was
> cropped and showed the TREND column blank. **A26 is substantially retracted and downgraded to
> MEDIUM** — the engine conforms to the TREND specification on entry, stop, target, and the 4R
> partial, and deviates only on the management instruction. **A2 is closed as resolved by
> specification.** A21 is unaffected and is now the most serious open conformance finding.

### 1.1 What is genuinely good

- The read-only boundary is real and **enforced by a test**, not just asserted in prose.
  `MT5ReadOnlyGateway` exposes no mutating method and `tests/test_safety.py` greps the source
  for `mt5.order_send` / `mt5.login`.
- Time handling is correct: all timestamps are timezone-aware UTC, the broker offset is
  re-derived per run from a cross-symbol consensus rather than hard-coded, and DST therefore
  needs no special case. This is the failure mode that kills most MT5 projects and it is solved.
- `analyze()` is a pure function with `now`, account, spec, tick, and candles all injected. That
  makes it testable and reproducible, and the test suite exploits it properly.
- Failure is closed, not open: stale journal → G10/G11 fail; non-positive spread → G2 fails;
  historical date → G12 fails. Ambiguity produces `NO_TRADE` with a named gate.

### 1.2 Alignment score

| Dimension | Score | Note |
|---|---|---|
| Safety boundary (read-only) | 19 / 20 | boundary now asserted at connect time and scanned package-wide; only the external connector remains (A25) |
| Conformance to source of truth | 20 / 20 | **12 of 12** rules conform; TREND is switched off rather than approximated |
| Release-gate integrity | 5 / 20 | A1 and A3 still make Stage 1 unpassable — unchanged |
| Documentation completeness | 17 / 20 | source of truth transcribed and decisions D1/D4 closed; D2 and D3 remain unsigned |
| Test coverage of critical paths | 8 / 10 | 31 tests, with negative tests on G7 and TREND; reconciliation layer still untested |
| Operational traceability | 6 / 10 | config hash recorded against the change; still not a git repo |
| **Total** | **75 / 100** | strategy conformance is closed; the remaining debt is release-gate and traceability |

*Scoring note: "Determinism & time correctness" was replaced with "Conformance to source of
truth" in revision 3. Time handling remains the project's strongest property and is now folded
into the safety and conformance lines.*

---

## 2. High-severity findings

### A1 — Stage 1 rejects every provisional artifact `HIGH`

`lifecycle.assess_analysis` recognises exactly two statuses. `models.AnalysisResult.status` emits
three. A `PROVISIONAL_RANGE_SETUP` result has all gates passing but `approved = False`, so the
Stage 1 check raises two failures on a perfectly correct artifact.

*Evidence — reproduced:*

```
PROVISIONAL CASE  status=PROVISIONAL_RANGE_SETUP  approved=False  all_gates_pass=True  n_gates=13
STAGE1 passed=False failures=[
  'approved flag does not equal the recorded gate results',
  'status does not match gate results' ]
```

*Location:* `session_strategy/lifecycle.py:53-57` vs `session_strategy/models.py:91-103`.

*Impact:* the 08:05 baseline run — the one the operational workflow says happens **every
weekday for every symbol** — produces artifacts that can never pass the conformance gate. Stage 1
therefore cannot be used as designed.

### A2 — TREND setups are approved with zero post-session data `RESOLVED BY SPECIFICATION`

> **Closed in revision 4.** The complete strategy diagram places TREND on the branch that never
> consults sweeps, so requiring post-session evidence for it would contradict the trader's rules.
> The behaviour below is correct. Retained for the record; excluded from the finding counts.


`provisional` is defined as `setup == "RANGE" and not post_session_candle_times`. A `TREND`
setup never consults post-session candles at all, so at 08:05 UTC — with zero completed
post-session bars and zero sweep coverage — a TREND proposal reaches
`APPROVED_FOR_MANUAL_ENTRY`.

*Evidence — reproduced:*

```
TREND @ 08:05, zero post-session candles -> status=APPROVED_FOR_MANUAL_ENTRY
                                            provisional=False  post_times=[]
```

*Location:* `session_strategy/models.py:91-93`.

*Impact:* the protection that `OPERATIONAL_WORKFLOW.md` §2 describes for range setups is absent
for trend setups. Either TREND genuinely needs no post-session confirmation — in which case say
so explicitly in `STRATEGY_SPEC.md` §12 — or this is an unguarded approval path.

### A3 — Artifact schema drift makes 100% of stored artifacts non-conformant `HIGH`

- 27 of 28 `analysis.json` files predate the `partial_target` / `partial_target_r` fields and do
  not contain them.
- The journal holds **four distinct config hashes** across four trading days
  (`b86b5f490fe58ce1`, `b443c80d540f964c`, `1f011b92abb718ca`, `fddb7465a73fd724`). Only the last
  is current.
- `lifecycle.assess_analysis` enforces `require_exact_config_hash` against the *live* config.

*Impact:* every artifact on disk fails Stage 1 on the hash check alone. There is no schema
version field in `analysis.json`, no migration path, and no retention or supersession policy.
`STAGED_IMPLEMENTATION.md` tells the trader to "retain its configuration hash" but nothing in the
project maps a hash back to the config that produced it.

*Evidence — the drift is behavioural, not cosmetic.* Analysis `483000815969` (USDJPY,
2026-08-10, hash `1f011b92abb718ca`) is stored as `APPROVED_FOR_MANUAL_ENTRY` with
`classification: RANGE` and a `BUY_LIMIT` at the session low of 157.652. Its own recorded inputs
are `efficiency_ratio = 0.5795` and `session_range = 0.805`. Under the **current** config
(`fddb7465a73fd724`, ER threshold 0.45, USDJPY `trend_min_range` 0.35), those same inputs
classify as **`TREND`** — a different setup, with a midpoint entry, a different stop, and a
different volume. It would also be a setup with no specification at all (A26).

So a stored, approved artifact records a trade the current rulebook would not propose. Past
evidence is not merely unverifiable against the live config; it is contradictory. Any Stage 2
sample drawn from the existing `outputs/` tree would mix incompatible rule versions.

---

### A26 — TREND management instruction contradicts the source `FIXED 2026-08-11`

> **Closed on both halves.** The ticket's management line is now setup-aware: SWEEP and RANGE
> print the session-boundary partial then breakeven; TREND prints the 4R partial then **trail**.
> And because the trailing *mechanics* remain undefined, TREND is switched off entirely via
> `enable_trend_setup: false` — the engine returns `NO_TRADE` with
> `G6: TREND_SETUP_DISABLED: trailing mechanics undefined in specification` (decision D4).
>
> This follows the governing directive: where a rule is ambiguous, stand aside rather than invent.
> Re-enable by setting the flag true once §0 defines the trail. Regression test:
> `test_trend_setup_is_gated_off_while_trailing_is_undefined`; the mapping itself stays covered by
> `test_trend_midpoint_mapping_when_explicitly_enabled`.

Original finding follows.


> **Substantially retracted from revision 3.** A26 originally read "the TREND setup has no
> specification and is nonetheless approvable", based on a cropped copy of the strategy diagram in
> which the TREND column appeared blank. The complete diagram defines all four TREND attributes.
> The implementation **conforms** on entry, stop, target, and partial. The finding narrows to the
> management tail. The original severity of `HIGH` was wrong and is corrected to `MEDIUM`.

The source specifies TREND management as "**Close 75% at 4R and Trail**". `render.markdown` prints
a single hard-coded instruction for every setup:

```python
f"- Partial Target: close 75% at {result.partial_target} ({result.partial_target_r:.2f}R), "
f"then manually move SL to breakeven"
```

*Evidence — measured against a constructed TREND session:*

```
entry   = midpoint?      1.10206 vs 1.10207        CONFORMS
stop    = 25% of range?  actual_r / R0 = 0.993     CONFORMS
target  = 5R?            5.00R                     CONFORMS
partial = 4R?            4.00R                     CONFORMS
management text  ->  "close 75% at 1.10626 (4.00R), then manually move SL to breakeven"
says "trail"?        NO   <-- source says Trail, ticket says breakeven
```

*Impact:* a trader following the ticket literally will move the stop to breakeven on a TREND
position where the strategy calls for a trailing stop. Breakeven caps the runner at 0R if price
retraces; trailing is intended to let it extend. These are materially different management
regimes, and the ticket instructs the wrong one on the setup designed to capture extended moves.

*Secondary issue — the trail is specified but not defined.* The source says "Trail" without
naming a structural reference, step size, confirmation requirement, or invalidation rule. So
`TREND` management is currently **half-specified**: the requirement exists, the mechanics do not.
Until they are defined, a trailed TREND trade cannot be judged `rule_compliant` for Stage 2,
because there is no rule to judge it against.

*Recommended:* (a) make the management line setup-aware so TREND prints the trail instruction;
(b) define the trailing mechanics in `STRATEGY_SPEC.md` before recording TREND trades as
evidence. This is decision D4.

*Consequential correction — A2 is resolved by the source.* A2 flagged that a TREND proposal can be
approved at 08:05 with zero post-session candles. The diagram places TREND on the branch that
never consults sweeps, so requiring post-session evidence for it would contradict the strategy.
A2 is closed as **resolved by specification**, not fixed.

### A27 — Stage 2 cannot be run: no backtest engine exists `HIGH`

Stage 2 is defined as validating the trader's strategy with a suitable backtest
(`STAGED_IMPLEMENTATION.md`). The project can **score** a trade log but cannot **produce** one:

- `sspf.py stage profitability` reads a JSON array of completed trades and applies the six
  thresholds in `config/lifecycle.json`.
- Nothing in the project generates that array. There is no historical simulation, no event loop
  over past candles, no cost or slippage model, and no development/out-of-sample split.
- `IMPLEMENTATION_PLAN.md` Phase 7 specified exactly this capability and was never delivered.

*Impact:* the entire second half of the project's purpose has no implementation. Stage 2 is not
merely blocked by a defect — the component it depends on does not exist. This is the largest
single piece of outstanding work, and it is materially larger than every other item in this
backlog combined.

*Secondary observation:* `accepted_samples` admits `forward_demo` records, so forward evidence
from day trading will eventually satisfy the record counts. But 50 records at roughly one
qualifying setup per symbol per day, with a high `NO_TRADE` rate, is months of trading — and it
would be evidence gathered *while* trading the unvalidated strategy rather than before. A backtest
answers the question faster and without capital at risk.

*Recommended:* build the backtester against `engine.analyze`, which is already a pure function
with every input injected — historical candles can be fed to it directly with no modification to
the strategy code. That design choice was made for testability and it makes this build far
smaller than it would otherwise be. Note that a backtest will also expose A21 immediately, since
deep sweeps are common in historical data.

### A20 — `G7_STOP_PROTECTION` is tautological and can never fail `FIXED 2026-08-11`

> **Closed.** G7 now evaluates the flat `R0` stop against the sweep extreme plus buffer and fails
> with `STOP_NOT_PROTECTED` when it does not clear. Verified falsifiable: of five sweep depths
> tested, one passes and four fail. Regression tests
> `test_unprotected_flat_stop_fails_g7_and_returns_no_trade` and
> `test_shallow_sweep_keeps_protected_stop_and_passes_g7` pin both directions.
>
> Note on the original prompt wording: G7 deliberately does **not** also check broker stop levels
> — that remains `G8_STOPS_LEVEL`'s job, so each gate keeps one reason to fail.

Original finding follows.


The gate that certifies "the stop is beyond the sweep extreme" is mathematically incapable of
failing. For a BUY:

```python
result.stop_loss = min(candle.low - buffer, result.entry - result.r0)
sweep_stop_ok    = result.stop_loss < candle.low - buffer + spec.tick_size / 2
```

`stop_loss` is defined as `≤ candle.low - buffer`, so the test `stop_loss < candle.low - buffer +
half a tick` is true by construction. The SELL branch has the identical structure. `sweep_stop_ok`
is also initialised to `True` and only ever assigned inside the `SWEEP` branch, so it passes
trivially on `RANGE` and `TREND` too.

*Evidence — attempted falsification across sweep depths from 2× to 99× the nominal R:*

```
sweep_low=1.0985  actual_r=2.08x R0   G7=True
sweep_low=1.0960  actual_r=7.08x R0   G7=True
sweep_low=1.0900  actual_r=19.08x R0  G7=True
sweep_low=1.0500  actual_r=99.08x R0  G7=True
```

*Impact:* a named safety gate appears in every ticket with `PASS` and in every `analysis.json`
as evidence, while testing nothing. It is worse than an absent gate, because it manufactures
assurance. No test asserts a G7 failure — which is why the tautology survived.

### A21 — Stop widening on deep sweeps is unbounded `FIXED 2026-08-11`

> **Closed by decision D1: flat `R0`, reject when unprotected.** The `min()`/`max()` widening is
> removed; the stop is now always `entry ∓ 0.25 × range`. Measured across sweep depths from
> shallow to 99×: `dist/R0 = 1.000` in every case, and the four unprotected cases return
> `NO_TRADE` instead of a repriced trade.
>
> **Consequence to expect:** this is materially more selective. A `SWEEP` is only tradeable when
> the reclaim candle's body closes back to within 15% of the session range above the session low
> (mirrored for sells) — derived in `STRATEGY_SPEC.md` §6.4. Expect a higher `NO_TRADE` rate on
> SWEEP, which is the intended price of holding the risk distance fixed.

Original finding follows.


Because the stop is `min(sweep_low - buffer, entry - R0)`, a deep sweep silently replaces the
nominal 25%-of-range risk distance with an arbitrarily larger one. Risk *cash* is preserved —
volume floors down — but three things break at once, as the same run shows:

| Sweep depth | `actual_r` vs `R0` | `partial_target_r` | Take profit |
|---|---|---|---|
| shallow | 2.08× | **1.44R** | 1.10470 |
| deeper | 7.08× | **0.42R** | 1.11720 |
| deep | 19.08× | **0.16R** | 1.14720 |
| extreme | 99.08× | **0.03R** | 1.34720 |

1. **The management model inverts.** The instruction is "close 75% at the opposite Asian
   boundary". At 19× widening that boundary sits at 0.16R — the 75% partial fires essentially at
   breakeven, so the strategy books a near-zero result on three-quarters of the position while
   still carrying a full unit of risk.
2. **The target leaves the map.** `TP = entry + 5 × actual_r` reaches 1.3472 on a session whose
   range was 20 pips. It is not a reachable price.
3. **No gate objects.** G7 passes (A20), G8 compares against the broker minimum and passes more
   easily as the stop widens, and G9 only fails once volume floors below `volume_min`.

*Impact:* this is the concrete failure the external review sensed but misdiagnosed as an
arithmetic contradiction. There is no contradiction in the code — there is an unbounded
substitution with no ceiling and no rejection path.

*Recommended control:* cap the widening (for example, reject when `actual_r > 1.5 × R0`) **or**
adopt the reviewer's model — fix the stop at `entry ∓ R0` and return
`INVALID_STOP_NOT_PROTECTED` when that distance fails to clear the sweep extreme. Either makes
G7 a real gate. This is a strategy decision; see `STRATEGY_SPEC.md` §12.

*Update after adopting the source of truth:* the diagram specifies the stop as a flat
**"25% of range"** for both SWEEP and RANGE, with no protection clause and no widening. The
current `min()` behaviour is therefore not merely unbounded — it is a **deviation from
specification**. The only remaining question is whether to implement the flat stop exactly as
written, or to add the reviewer's protection check as a deliberate safety extension beyond the
source. See `STRATEGY_SPEC.md` §0.4.

### A22 — Configured risk contradicts stated risk policy `HIGH`

`config/strategy.yaml` sets `risk_percent_fx: 1.0` and `risk_percent_gold: 2.0`. The external
review states the established policy is **0.5% per trade**, with the 1% figure described as
carried over from an example rather than a formal policy change. `STAGE1_QUALIFICATION.md`
records 1%/2% as a completed qualification item, so the discrepancy is currently baked into the
qualification evidence.

*Impact:* every forward-demo record collected to date is sized at two to four times the stated
policy. If 0.5% is the real policy, the sizing evidence does not transfer. Compounding this,
`maximum_trades_per_symbol_session` is loaded but never enforced (A13), so there is no
overtrading guard of any kind.

*This is a governance decision, not a defect to be patched silently.* Recorded pending sign-off.

---

## 3. Medium-severity findings

### A23 — Partial-target semantics differ between setups `MEDIUM`

`SWEEP` and `RANGE` take the partial at the opposite Asian boundary; `TREND` takes it at exactly
`entry ± 4R`. These coincide only when the entry sits exactly on a range boundary — true for
`RANGE` (the test pins `partial_target_r` to 4.00), never guaranteed for `SWEEP`, where the entry
is the reclaim candle body. In the reproduction above the `SWEEP` partial ranged from 1.44R down
to 0.03R.

*Impact:* the ticket reports one `Partial Target` line, so a trader reading two tickets from two
setups is reading two different rules under one label. The blended expectancy differs
accordingly: the `TREND` model returns `0.75 × 4R + 0.25 × 5R = 4.25R`, while a `SWEEP` at 1.44R
returns `0.75 × 1.44R + 0.25 × 5R = 2.33R`.

*Recommended:* report the 4R price and the opposite-boundary price as **separate lines** on the
ticket, and state explicitly which one is the instruction for each setup.

*Update after adopting the source of truth — the recommendation is partly reversed.* The diagram
specifies management as "**Close 75% at session range and Breakeven**" — the session boundary, not
4R. So the code is **correct** for SWEEP and RANGE, and the external reviewer's prescription
("use Entry ± 4R; do not replace the 4R target with the opposite Asian boundary") is **wrong**
against the source. What survives is the reviewer's *observation*: the two levels are different
numbers and the ticket should show both, because the resulting R multiple varies and the trader
should see it. The 4R partial in the TREND branch is doubly unspecified — TREND itself has no
definition (A26).

### A24 — Reference-session definition is disputed `MEDIUM`

The implementation uses **00:00–08:00 UTC** (32 M15 candles), which is 06:30–14:30 Myanmar. The
external review specifies **22:00–07:00 UTC** (04:30–13:30 Myanmar), which is nine hours and
would require `session_candles: 36`.

Both definitions are internally consistent — Myanmar is UTC+6:30 and the review's conversion is
arithmetically correct — but they are not the same session, and no source document in the project
settles which one v2.2 means. `Session_Trading_Hybrid_Workflow_v2.2.md` remains absent (A3).

*Impact:* if the review's definition is correct, every session level, classification, and stored
artifact is computed from the wrong window. This is the single highest-consequence open question
in the project. Recorded pending sign-off.

### A25 — Order-capable MT5 tools are exposed in the assistant session `PARTIALLY FIXED`

> **Codebase side closed 2026-08-11.** `mt5_gateway` now declares `FORBIDDEN_MT5_CALLS` and
> asserts on connect that the gateway exposes none of them, failing closed with
> `Read-only boundary violated` if a mutator is ever added. Two new tests cover it: one scans
> **every module in the package** for `mt5.order_send`-class calls, one proves the assertion fires.
> Connection now logs `mt5_connected mode=read_only trading_calls_exposed=0`.
>
> **Environment side still open, and it is the part that matters.** No code in this project can
> prevent an order submitted through the MT5 MCP connector directly. That requires
> `MT5_TRADING_ENABLED=false` and `MT5_DEMO_ONLY=true` in the connector's own settings — a change
> only the trader can make.

Original finding follows.


Outside the repository, and therefore outside the scope of `tests/test_safety.py`: the assistant
session that operates this project has an MT5 connector loaded whose tool surface includes
`place_market_order`, `place_pending_order`, `modify_position`, `close_position`,
`close_all_positions`, `close_all_positions_by_symbol`, `cancel_all_pending_orders`, and
related mutating calls.

The project's read-only guarantee is real but narrow: it covers `session_strategy`, not the
environment. Nothing in the codebase can prevent an order submitted through the connector
directly.

*Recommended:* run the MT5 MCP server with `MT5_TRADING_ENABLED=false` and `MT5_DEMO_ONLY=true`,
or connect a read-only variant exposing only `get_account_info`, `get_symbols`,
`get_symbol_price`, `get_candles_latest`, `get_all_positions`, `get_all_pending_orders`, and
`get_deals`. This is the highest-value item in this revision and it costs nothing to implement.

### A4 — Permanent spurious "unmatched MT5 item" warning `MEDIUM`

`journal.match_active` returns `unmatched_active = max(0, len(active) - matched)` where `matched`
counts only items matched **during this run**. Anything matched on a previous run is skipped by
the `SELECT 1 FROM matches` guard but still counted in `len(active)`.

*Impact:* once any position is matched, every subsequent ticket carries
`"N unmatched discretionary/open MT5 item(s)"` forever. A warning that is always on is a warning
that gets ignored — which defeats its purpose when a genuinely unmatched position appears.

*Location:* `session_strategy/journal.py:126`, surfaced at `session_strategy/cli.py:87-88`.

### A5 — Open risk is not date-scoped `MEDIUM`

`risk_stats` sums `actual_risk` over **all** matches in state `POSITION` or `ORDER`, with no date
filter, and adds it to today's realised loss to form `daily_used_cash`.

*Impact:* a position carried overnight permanently consumes the current day's risk budget. With
`daily_limit = min(2% of balance, $20)` ≈ $19.76 at the current balance, one carried FX position
at 1% risk silently halves every subsequent day's budget until it closes. This may be intended
conservatism — it is not documented anywhere, and G10 gives no indication that the consumption is
historical rather than same-day.

*Location:* `session_strategy/journal.py:150`.

### A6 — Broker-clock consensus is a single point of total failure `MEDIUM`

`broker_utc_offset` raises unless **at least two** symbols return a tick that is both fresh
(≤300 s) and within ±14 h. `analyze_command` calls it before anything else, so the exception
propagates to `main()` and the whole run exits 1 with no artifact and no `NO_TRADE` record.

*Impact:* if gold is between sessions, or a Monday open staggers quotes, or three of four symbols
are briefly unsubscribed, the analysis does not degrade to `NO_TRADE` — it disappears. There is no
audit trail of the attempt. Fail-closed is right; failing *silently* is not.

*Location:* `session_strategy/mt5_gateway.py:67-81`, `session_strategy/cli.py:69-71`.

### A7 — G2 evidence is overwritten `MEDIUM`

After levels are computed, `engine.py:133-135` locates the existing `G2_DATA_INTEGRITY` gate and
**replaces** it, discarding the candle-validation detail string (`"32 consecutive closed M15
candles (complete)"`) in favour of `"valid session and fresh tick"`.

*Impact:* the ticket loses the evidence Stage 1 exists to preserve. `lifecycle` checks that gate
*names* appear in the ticket, so this passes — but the audit trail is thinner than the design
intends.

### A8 — `render_mt5_charts.py` is an orphan that contradicts the engine `MEDIUM`

A standalone top-level script, imported by nothing and covered by no test, that duplicates the
charting concern owned by `session_strategy/render.py` and disagrees with it on three points:

| | `render_mt5_charts.py` | Strategy |
|---|---|---|
| Broker offset | hard-coded `timedelta(hours=3)` | derived per run |
| Asian session | `0 <= hour < 7` | `00:00–08:00` |
| Symbols | `EURUSD` only | four configured symbols |
| **Timeframes** | **fetches H1, M15 and M5** | **M15 only** |

The timeframe row is the sharpest of these: the strategy is M15-only by trader instruction, and
this script is the sole place in the project that reads any other timeframe. A chart pack showing
H1 and M5 context invites exactly the higher-timeframe reasoning the strategy excludes.

*Impact:* a chart pack generated from this script will not reconcile against a ticket, which
directly undermines the "verify visually in MT5" step in `OPERATIONAL_WORKFLOW.md` §3. This is a
duplicate-module violation: two renderers, one owner.

### A9 — Documentation described a structure that was never built `MEDIUM`

`IMPLEMENTATION_PLAN.md` §5 specifies `time_utils.py`, `bias.py`, `classifier.py`, `setups.py`,
`risk.py`, `validation.py`, `tickets.py`, `monitor.py`, `charts.py`, `main.py`, and
`config/strategy.example.yaml`. None exist. The real package is eight consolidated modules. §7's
configuration template shares almost no keys with the real `config/strategy.yaml` and specifies
`basis: equity` where the code uses balance.

*Status:* corrected in this pass — see §6.

### A10 — Scheduled automations are undefined in-tree `MEDIUM`

`README.md` and `OPERATIONAL_WORKFLOW.md` describe three active automations — `sspf-asian-close`,
`sspf-sweep-monitor`, `sspf-session-freeze` — and `STAGE1_QUALIFICATION.md` lists the first as a
completed qualification item. No scheduler definition, wrapper script, or configuration for any of
them exists in the project.

*Impact:* the daily operating model depends on three unversioned external objects. They cannot be
reviewed, restored, or reconciled against a config hash.

### A11 — Reconciliation layer is untested `MEDIUM`

*Partially addressed 2026-08-11: the suite grew from 25 to 31 with negative tests on G7, the TREND
gate, and a package-wide read-only scan. The reconciliation gap below is unchanged.*

25 tests passed at the time of this finding, but coverage is concentrated in `engine`, plus two shallow journal tests, two
lifecycle tests, and four safety tests. There is **no** test for `cli.py`, `render.py`,
`mt5_gateway.broker_utc_offset`, `journal.match_active`, `journal.update_closed`, or
`risk_stats` with populated data — which is precisely where A4 and A5 live. The plan's Phase 8
"golden-case tests using saved candle fixtures" were never built; there is no `tests/fixtures/`.

---

## 4. Low-severity findings

| ID | Finding | Location |
|---|---|---|
| A12 | **Not a git repository, no `.gitignore`.** `__pycache__/`, `.pytest_cache/`, `data/*.sqlite3`, and `outputs/` all sit in the tree. Config-hash → commit traceability, which Stage 2 assumes, is impossible. | project root |
| A13 | **Four config keys loaded but never used:** `maximum_simultaneous_positions`, `maximum_trades_per_symbol_session`, `proposal_ttl_minutes`. Expiry uses `execution_end_utc` instead of the TTL. They still change the config hash, so editing a dead key invalidates every prior artifact. | `config.py:27,28,42` |
| A14 | **Dead code:** `execution_start` assigned and unused (recomputed 27 lines later as `start_t`); `pips` assigned and unused; redundant dict comprehension immediately overwritten by a `setdefault` loop. | `engine.py:207`, `render.py:18`, `journal.py:130` |
| A15 | **Duplicate entry points:** `sspf.py` and `session_strategy/__main__.py` both call `main()`. Only `sspf.py` is documented. | root |
| A16 | **No config validation.** An unknown YAML key raises a bare `TypeError` from the dataclass; negative risk, `ER threshold > 1`, or `session_candles = 0` load silently. | `config.py:56-62` |
| A17 | **Symbol naming inconsistency.** Config and README use `XAUUSD.crp`; the installed `session-trade` skill and related material reference `XAUUSD-VIP`. | `config/strategy.yaml` |
| A18 | **Risk-basis contradiction.** README says "1% of balance"; `IMPLEMENTATION_PLAN.md` §7 says `basis: equity`. Code uses balance. | corrected in §6 |
| A19 | **Gold risk consumes the entire daily budget.** `risk_percent_gold = 2.0` equals `daily_risk_limit_percent = 2.0`, so one gold proposal exhausts the day. Arithmetically consistent, but it makes gold a strictly one-shot instrument — worth stating as intent. | `config/strategy.yaml` |

---

## 5. Remediation backlog

Ordered by unblocking value, not by severity alone.

| # | Action | Addresses | Effort |
|---|---|---|---|
| ~~0a~~ | ~~Assert the read-only boundary in code~~ **DONE 2026-08-11.** Still outstanding on the trader's side: set `MT5_TRADING_ENABLED=false` / `MT5_DEMO_ONLY=true` in the MT5 connector settings. | A25 | S |
| ~~0b~~ | ~~Decide the stop model and make G7 assert it~~ **DONE 2026-08-11** — flat `R0`, reject when unprotected (D1). | A20, A21 | ✅ |
| ~~0b2~~ | ~~Make the management line setup-aware and gate TREND~~ **DONE 2026-08-11** (D4). Still outstanding: **define the trailing mechanics** in §0 — structural reference, step, confirmation, invalidation — before TREND can be re-enabled. | A26 | M |
| 0c | **Sign off the session definition** (00:00–08:00 vs 22:00–07:00 UTC) and the **risk policy** (1%/2% vs 0.5%). Both invalidate existing evidence if changed; neither should be changed silently. Note the coupling: a nine-hour window also requires `session_candles: 36`. | A22, A24 | S |
| 1 | Teach `lifecycle.assess_analysis` the three-status model: derive the expected status the same way `models.status` does, including the provisional branch. Add a regression test that round-trips a provisional artifact through Stage 1. | A1 | S |
| 2 | Decide and record whether TREND requires post-session confirmation. If yes, extend `provisional` to any setup with zero post-session candles. If no, state the exemption in `STRATEGY_SPEC.md` §12 and add a test pinning the behaviour. | A2 | S |
| 3 | Add `schema_version` to `analysis.json`, and a `config_snapshot` (or the raw config) alongside the hash so an artifact can be re-verified after the config moves on. Define a retention/supersession policy for `outputs/`. | A3 | M |
| 4 | Initialise git, add `.gitignore` for `__pycache__/`, `.pytest_cache/`, `data/`, `outputs/`, `mt5_chart_pack/`. Tag the config hash on every commit that touches `config/`. | A3, A12 | S |
| 5 | Fix `unmatched_active` to count active MT5 items with no row in `matches`, rather than subtracting this run's match count. | A4 | S |
| 6 | Date-scope open risk in `risk_stats`, or keep it and document the carry-over rule explicitly in the G10 detail string. | A5 | S |
| 7 | Catch the broker-offset failure in `analyze_command` and emit a `NO_TRADE` artifact with a failed `G0_BROKER_CLOCK` gate instead of exiting 1 with no record. | A6 | S |
| 8 | Append a second `G2_DATA_INTEGRITY_RANGE` gate instead of overwriting G2. | A7 | S |
| 9 | Delete `render_mt5_charts.py`, or move it to `tools/` and rewrite it to consume `session_strategy.config` + the derived broker offset. | A8 | M |
| 10 | Commit the three automation definitions into the project and reference them from `OPERATIONAL_WORKFLOW.md`. | A10 | M |
| 11 | Add `tests/fixtures/` with saved candle sets and golden tickets; add tests for the journal reconciliation layer and the CLI. | A11 | L |
| 11b | **Build the backtest engine** against `engine.analyze` — historical candles, no look-ahead, explicit cost and slippage assumptions, setup-specific management, development/out-of-sample split. Without it Stage 2 does not exist. | A27 | XL |
| 12 | Either enforce or delete the four dead config keys; add range validation and an explicit "unknown key" error to `load_config`. | A13, A16 | S |
| 13 | Remove dead assignments and settle on one entry point. | A14, A15 | S |
| 14 | Reconcile the `XAUUSD.crp` / `XAUUSD-VIP` naming across project and skills. | A17 | S |

0a, 0b and 0b2 are done in code. **0c is now the top item** — it determines whether any evidence
collected from here is worth keeping. Items 1–2 then unblock Stage 1, and 11b (the backtester) is
the whole of Stage 2.

### Deviations found in the supplied engineering brief, not implemented

Per the governing directive, these were logged rather than coded, because implementing them as
written would have changed the trader's rules:

| Brief says | Actual rule | Action |
|---|---|---|
| G3 universe includes `XAUUSD` | the configured exact symbol is `XAUUSD.crp`; `XAUUSD` fails G3 | kept `.crp` |
| "ER ≥ 0.45 → TREND" | ER ≥ 0.45 **and** `range ≥ trend_min_range` → TREND, else `UNCLASSIFIED` | unchanged. Moot while TREND is off — both paths yield `NO_TRADE` — but the `UNCLASSIFIED` band must not be dropped silently |
| G7 should also check broker stop levels | that is `G8_STOPS_LEVEL` | kept separate, one reason to fail per gate |
| G7 caps `ActualR ≤ 1.5 × R0` | under the chosen flat-stop model `ActualR ≡ R0`, so the cap can never bind | not implemented; it would be dead code |

---

## 6. Documentation delivered in this pass

| File | Status |
|---|---|
| `STRATEGY_SPEC.md` | **new** — Phase 0 deliverable, reconstructed from source; freezes formulas, the G0–G12 gate table, and open spec items |
| `AUDIT_REPORT.md` | **new** — this document |
| `ARCHITECTURE.md` | **new** — module ownership, data flow, entry points, extension rules |
| `CONFIGURATION.md` | **new** — every key in `strategy.yaml` and `lifecycle.json`, with effect, range, and hash impact |
| `IMPLEMENTATION_PLAN.md` | **corrected** — §5 structure and §7 template replaced with what actually exists; risk basis reconciled to balance |
| `README.md` | **corrected** — points to the new docs; automation and risk-basis claims qualified |

---

## 7. Safety state

Unchanged and re-verified. The project remains demo/shadow only. `MT5ReadOnlyGateway` exposes no
order-mutating call, `mode` is pinned to `analysis_only`, and the environment gate requires the
demo account and server. Nothing in this audit alters that boundary, and passing any operational
check does not establish a profitable strategy or authorise live trading.

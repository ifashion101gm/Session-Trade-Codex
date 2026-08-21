# Strategy Engine and Agent Skills Audit

Audit date: **2026-08-20**  
Scope: **Phase A only — inventory, authority analysis, contract-gap analysis, and minimal target design**

## Executive decision

```text
ARCHITECTURE_READY = YES
CONTRACT_READY     = NO
REFACTOR_READY     = NO
```

`SESSION_FLOW_V2` has enough signed material to define a small target architecture,
but not enough to implement the complete three-entry strategy. The signed V2 spec
itself blocks implementation on the complete Entry 1 contract and reconciliation of
Entry 2 with the Range-only master route. This audit therefore stops before code
refactoring, scheduling, ticket generation, or execution changes.

The current working tree was already dirty before this audit. Existing modified and
untracked files are treated as user-owned. This report is the only file added by the
audit.

## Repository state

| Field | Value |
| --- | --- |
| Branch | `master` |
| HEAD | `2b58c4f011de45bd6d15fca72a091ad72aa99958` |
| Working tree | Dirty: 6 tracked files modified and numerous untracked specifications, datasets, outputs, scripts, tests, and artifacts |
| Active historical runtime | `ASIAN_SESSION_V1` via `config/strategy.yaml` and `session_strategy/engine.py` |
| Frozen/rejected ledger baseline | `SESSION_FLOW_V1`, id `a6188c364c63f39f`, retained as rejected historical lineage |
| New target contract | `SESSION_FLOW_V2`, version `2.0-draft`, specification-only and incomplete |

### Baseline preservation finding

`SESSION_FLOW_V2_SPEC.md` names `SSPF_V1_3_BASELINE_FROZEN`, but no separately
identifiable file, module, configuration, ledger entry, or test fixture with that
exact identity exists in the repository search. One experiment comments that it keeps
the SSPF-v1.3 classifier fixed, but that is not a reproducible frozen baseline package.

Disposition: **LEGACY_ONLY / DOCUMENTATION GAP**. Do not delete or reinterpret any
candidate legacy implementation. Before Phase B, identify the exact spec, config,
engine revision, data fingerprint, and golden outputs that constitute
`SSPF_V1_3_BASELINE_FROZEN`.

## Authority and provenance inventory

### Authoritative or governance specifications

| Artifact | Status and authority | Disposition |
| --- | --- | --- |
| `SESSION_FLOW_V2_SPEC.md` | Signed V2 session timing, ER-only regime classifier, and master E1/E2/E3 routing; explicitly says the full strategy is not implementation-ready | **KEEP** as V2 master contract |
| `RANGE_SETUP_V2_SPEC.md` | Signed and implementation-ready Entry 3 component, including trigger, windows, risk, targets, no automatic breakeven, fill authority, and one-trade limit | **KEEP** as subordinate V2 contract |
| `config/session_flow_v2.yaml` | Machine-readable V2 draft; mirrors signed timing/classifier and records E1/E2 blockers | **SIMPLIFY/COMPLETE LATER** after remaining decisions are signed |
| `session_strategy/session_contract.py` | Frozen, side-effect-free V2 session-leg definitions and exact contiguous-bar validation | **KEEP**, then generalize only if Phase B is authorized |
| `SESSION_FLOW_V1_SPEC.md` | Historical V1 contract with later corrections and unresolved readings | **LEGACY_ONLY** |
| `STRATEGY_LEDGER.md` + `versions/ledger.json` | Append-only version lineage and rejected `SESSION_FLOW_V1` record | **KEEP** |
| `ENGINE_FIX_SPEC.md` | V1 defect/ambiguity register; not V2 authority | **LEGACY_ONLY / INPUT TO GAP ANALYSIS** |
| `DECISION_2026-08-16.md` | Research decisions and rejected-engine findings, including unsigned bias and trail issues | **LEGACY_ONLY** |
| `SIGNOFF_2026-08-16.md` | Explicitly states that its listed items are not signed | **LEGACY_ONLY / UNSIGNED** |
| `STRATEGY_SPEC.md`, `STRATEGY_TRUTH_SOURCE.md`, `config/strategy.yaml` | Superseded/active ASIAN_SESSION_V1 material used by the current runtime | **LEGACY_ONLY** until a versioned compatibility path is proven |
| `config/source_v1.yaml`, `config/source_v2_agent.yaml`, `config/user_resolved_v2.yaml` | Source-comparison and research contracts with materially different timing, classifier, bias, and management rules | **KEEP ISOLATED; NEVER MERGE INTO V2 BY DEFAULT** |

### Data audit precondition

The repository contains master, UTC, audit, manifest, and sealed datasets plus
`scripts/verify_datasets.py` and `market-data-quality` guidance. No single V2 data-audit
artifact is named by `SESSION_FLOW_V2_SPEC.md`. Phase B must bind its tests to an
explicit audited dataset fingerprint. The sealed datasets must remain unopened until
the repository's existing freeze/governance conditions are satisfied.

## Existing strategy engines

| File / function | Current responsibility | Embedded authority and duplication | Baseline dependency | Recommended disposition |
| --- | --- | --- | --- | --- |
| `session_strategy/engine.py::analyze` | Production-shaped ASIAN_SESSION_V1 analysis pipeline: environment, data, regime, setup routing, entry, risk, volume, costs, and authorization gates | Monolith owns session timing, classifier, fallback bias, setup precedence, entry prices, SL/TP, structural gate, position sizing, and authorization. It duplicates its helper functions and several backtest scripts. | Active ASIAN_SESSION_V1 artifacts/tests | **LEGACY_ONLY**; do not mutate into V2 |
| `session_strategy/engine.py::{lock_asian_levels,classify_session,detect_sweep,detect_range_rejection,detect_trend_continuation}` | Reusable-looking calculations coupled to StrategyConfig | Classifier formula differs from signed V2 path-based ER; detectors embed thresholds and directions; trend logic embeds entry confirmation and invalidation | ASIAN_SESSION_V1 | **SIMPLIFY** only through new pure adapters in Phase B; preserve old functions |
| `scripts/session_flow.py::{levels,plan,simulate}` | SESSION_FLOW_V1 two-leg planner and fill simulator | Owns ER threshold, close-location bias, sweep/rejection threshold, route selection, E1/E2/E3 entries, 25% risk, TP and breakeven | Rejected V1 ledger baseline | **LEGACY_ONLY** |
| `scripts/backtest_session_flow.py` | Costed V1 historical runner and collision bounds | Reuses `session_flow.plan` but duplicates fill/accounting logic and exposes alternative classifier | Rejected V1 results | **LEGACY_ONLY** |
| `asian_session_backtester.py` | Large experimental multi-session backtester | Independently owns classifier, bias, sweep, range/trend entries, trade limits, cooldown, loss lock, fill simulation, management, reporting | Many historical output folders and golden comparisons | **LEGACY_ONLY; DEPRECATE FOR NEW V2 WORK** |
| `scripts/run_flowchart.py` | Literal flowchart experiment | Independent classifier, bias modes, routing, entry/risk/targets | Research-only V1 interpretation | **DEPRECATE / LEGACY_ONLY** |
| `scripts/backtest_session.py` | ASIAN_SESSION_V1 setup-by-setup historical evaluation | Duplicates entry, risk, SL/TP and fill simulation around `engine.py` detectors | ASIAN_SESSION_V1 research | **LEGACY_ONLY** |
| `session_strategy/source_v1.py` | Historical Episode 18 comparison model | Independent classifier, route detection, entry, risk and outcome management | Source V1 tests | **LEGACY_ONLY** |
| `session_strategy/source_v2.py` | User-resolved source research primitives | Independent London-local timing, classifier, bias and trailing | Source V2 tests | **KEEP ISOLATED / LEGACY RESEARCH** |
| `scripts/sweep_entry_experiment.py` | Causal Entry 2 experiment | Hard-codes a different ER threshold/formula, bias convention, 25% risk, structural gate, idealized same-close fill, targets and breakeven | Explicitly separate experiment | **RECONCILE, THEN SIMPLIFY**; not V2 authority |
| `replay_source_v1.py`, `replay_source_v2.py`, `replay_source_v2_agent.py` | Contract-specific replay entry points | Each binds a different contract and engine | Historical reproduction | **LEGACY_ONLY** |

No current module implements the signed `SESSION_FLOW_V2` master router. The only V2
code is the session-leg contract and its tests.

## Existing Agent Skills

There are two meanings of “skill” in the repository and they must not be conflated.

1. `.agents/skills/*` contains general research-method skills. They guide agents but
   are not runtime strategy components.
2. `AGENT_SKILLS.md` describes conceptual Tier A/Tier B trading capabilities, mostly
   implemented as ordinary Python functions spread across engines and scripts.

### Installed research-method skills

| Skill | Current responsibility | Inputs / outputs | Strategy authority embedded? | Reusable? | Disposition |
| --- | --- | --- | --- | --- | --- |
| `strategy-specification` | Turn hypotheses into causal signed specs | Hypothesis -> contract | No runtime authority | Yes | **KEEP** |
| `market-data-quality` | Audit historical data integrity | Raw data -> audit evidence | No | Yes | **KEEP** |
| `multi-asset-conventions` | Instrument/P&L conventions | Instrument metadata -> conventions | No | Yes | **KEEP** |
| `backtest-engineering` | Causal implementation/review workflow | Contract + audit -> backtest design/tests | No | Yes | **KEEP** |
| `risk-position-sizing` | Research sizing and risk controls | Portfolio inputs -> sizing evidence | May propose research rules, but not this strategy's authority | Yes | **KEEP** |
| `performance-analysis` | Analyze completed costed results | Ledger/equity -> metrics | No | Yes | **KEEP** |
| `robustness-validation` | Falsification and OOS validation | Frozen backtest -> robustness evidence | No | Yes | **KEEP** |

### Conceptual trading-skill implementation audit

| Capability / current location | Current inputs -> outputs | Embedded strategy authority | Reusable? | Disposition |
| --- | --- | --- | --- | --- |
| Session boxing: `session_contract.SessionLeg`, `engine.lock_asian_levels`, `session_flow.levels` | Bars -> immutable bounds/OHLC/geometry | Legacy versions also calculate risk and classifier fields | Partly | **KEEP** V2 `SessionLeg`; **SIMPLIFY** geometry into facts only |
| Regime evidence: multiple `levels` functions | Bars -> ER/mid/location | Each chooses a different ER formula and often classification threshold | No, as written | **MOVE_RULE_TO_CONTRACT; MERGE_DUPLICATE** calculation after V2 formula is fixed |
| Bias: fallback in `engine.analyze`, `session_flow.levels`, `asian_session_backtester`, `source_v2` | Bars/structure -> direction | Hard-coded direction and sometimes veto behavior | No | **MISSING** for V2 until causal source is signed |
| Sweep detection: `engine.detect_sweep`, `asian_session_backtester.signal_for`, `session_flow.plan`, experiment | Box + bars -> sweep/direction/candidate | Thresholds, eligibility, direction, entry and structural policy are mixed together | Partly | **MOVE_ROUTING_TO_ENGINE; MOVE_RULE_TO_CONTRACT; SIMPLIFY** to structured evidence |
| Range rejection: `engine.detect_range_rejection`, `asian_session_backtester.signal_for`, `source_v1.detect` | Box + bar -> rejection/candidate | Tolerance, bias gate, direction and entry are mixed | Partly | **SIMPLIFY** using signed RANGE_SETUP_V2 evidence |
| Trend entry: `engine.detect_trend_continuation`, `source_v1.detect`, flowchart/session scripts | Box + bar + bias -> candidate | Multiple incompatible triggers and invalidations | No | **MISSING** for V2 contract |
| Entry builders | Detector-specific inline branches | Entry price and direction embedded in engines/backtests | No | **MERGE_DUPLICATE** only after E1/E2 contracts close |
| Risk math: inline in engine/scripts | Candidate + range -> SL/TP | 25%, boundary-vs-4R partial, breakeven and structural gates vary | Partly | **SIMPLIFY** into common V2 math; retain setup gates separately |
| Position sizing: `engine.analyze` | Account/spec/risk -> volume | Risk-percent, daily limit and broker constraints mixed with routing | Yes with injected policy | **SIMPLIFY**; facts/math only |
| Ticket formatting: `session_strategy/render.py`, report writers | Analysis result -> JSON/Markdown/chart | Assumes legacy field names and statuses | Partly | **SIMPLIFY** after a versioned V2 decision schema exists |
| Chart drawing: `session_strategy/render.py`, render scripts | Candles/result -> images | Presentation only, but labels assume legacy TP semantics | Yes after schema adapter | **KEEP SEPARATE** |
| M1 execution | No authoritative V2 implementation found | M15 signal close is sometimes treated as an idealized fill | No | **MISSING** |
| Contract validation: lifecycle validator and engine gates | Artifact/config -> pass/fail | Validates ASIAN_SESSION_V1 artifact conformance, not engine/skill consistency for V2 | Partly | **MISSING** as a V2 decision validator |

## Skill coverage matrix

| Required capability | Exists? | Current implementation | Strategy logic embedded? | Action |
| --- | --- | --- | --- | --- |
| Session box | Partial/V2 foundation | `session_strategy/session_contract.py`; several legacy level functions | Legacy functions: yes | Keep V2 leg; extract pure geometry later |
| Draw session box | Yes | `session_strategy/render.py`, `scripts/render_*` | Labels/schema only | Keep outside engine |
| Calculate midpoint | Yes, duplicated | Engine, source, flow and experiment level functions | Usually bundled with rules | Merge into pure evidence calculation |
| Calculate ER | Yes, conflicting | Range-normalized ER in legacy code; path-based ER signed for V2 but not implemented | Threshold often embedded | Implement only signed V2 formula in a new versioned evidence function |
| Bias | Many legacy proxies; V2 missing | close location, session direction, H1/M15 structure, daily bias | Yes | Do not choose; close V2 contract |
| Sweep detection | Partial/conflicting | Four principal implementations plus experiment | Yes | Reconcile V2 Entry 2, then return evidence only |
| Range rejection | Yes for V2 spec, not V2 code | Legacy detectors; signed RANGE_SETUP_V2 trigger | Yes in legacy | Implement later as pure structured evidence |
| Trend entry | Legacy only | Midpoint-zone/retrace variants | Yes | V2 contract missing |
| Sweep entry | Experimental only | `scripts/sweep_entry_experiment.py` | Yes | Reconcile and separate evidence from entry construction |
| Range entry | Spec only for V2 | `RANGE_SETUP_V2_SPEC.md`; legacy implementations differ | Yes in legacy | Implement after full-contract gate |
| Risk calculation | Yes, duplicated | Engine and backtest scripts | Yes | Common V2 risk math after candidate construction |
| Position sizing | Yes, legacy runtime | `engine.analyze` | Policy mixed with math | Reuse math behind explicit policy inputs |
| Ticket generation | Yes, legacy | `render.py`, report scripts | Legacy schema/status assumptions | Versioned V2 formatter later |
| M1 execution | No authoritative implementation | Idealized or M15 OHLC fill simulators only | Fill policy embedded | Missing; execution adapter must own fill truth |
| Contract validation | Partial, wrong boundary | `lifecycle.assess_analysis` and inline gates | ASIAN_SESSION_V1-specific | Add lightweight V2 validator after contract closure |

## Duplicate authority register

The count below is by decision category, not by occurrence. Each category has two or
more components currently acting as authority.

| # | Decision category | Duplicate authorities | Classification |
| ---: | --- | --- | --- |
| 1 | Asian timing / candle count | `config/strategy.yaml`, source configs, flow scripts, backtester constants, V2 spec/config/code | **DUPLICATE_AUTHORITY**; version-isolate |
| 2 | London timing / observation window | Flow/backtester constants, source-local contracts, V2 spec/config/code | **DUPLICATE_AUTHORITY**; version-isolate |
| 3 | ER formula | Legacy range-normalized ER and V2 close-path ER | **DUPLICATE_AUTHORITY**; V2 contract owns V2 |
| 4 | ER threshold / boundary equality | 0.35, 0.40, 0.50 and 0.60 appear in active/research components | **DUPLICATE_AUTHORITY** |
| 5 | Midpoint / close-location regime rule | Active engine, source model and experiments differ; V2 says diagnostic only | **DUPLICATE_AUTHORITY** |
| 6 | Bias source and role | Close location, open/close sign, H1/M15 structure, daily bias, deferred bias | **DUPLICATE_AUTHORITY / V2 GAP** |
| 7 | Sweep definition and threshold | Buffer/quality detector, wick-ratio detector, V1 rejection-ratio plan, reclaim-clearance experiment | **DUPLICATE_AUTHORITY / V2 GAP** |
| 8 | Range rejection | Touch tolerance, exact boundary, bias-gated and close-trigger variants | **DUPLICATE_AUTHORITY**; V2 spec supersedes only for V2 |
| 9 | Setup precedence | ASIAN_SESSION_V1 uses Sweep > Range > Trend across eligible detectors; V1/V2 routers differ | **DUPLICATE_AUTHORITY**; version-isolate |
| 10 | Entry selection | Sweep body edge vs close; Range boundary vs close; Trend midpoint vs confirmed retrace | **DUPLICATE_AUTHORITY / E1-E2 GAP** |
| 11 | SL/TP and management | Opposite-boundary partial, fixed 4R, breakeven, trail, fixed 5R appear in different paths | **DUPLICATE_AUTHORITY** |
| 12 | Position sizing / risk authorization | Inline engine policy, experimental fixed-R studies, and missing-metadata analytical modes | **DUPLICATE_AUTHORITY** |
| 13 | Ticket authorization / terminal status | Inline gates, lifecycle artifact validator, experiment status fields | **DUPLICATE_AUTHORITY** |
| 14 | Fill simulation / collision policy | At least four simulators; idealized close fill, resting-limit fill, and STOP_FIRST/TARGET_FIRST variants | **DUPLICATE_AUTHORITY** |

Total duplicate-authority categories: **14**.

Versioned legacy compatibility is a valid reason for duplicate code, but it is not a
reason to share authority within `SESSION_FLOW_V2`. Every V2 artifact must carry its
contract/version and must never silently fall through to a legacy rule.

## Required authority matrix for SESSION_FLOW_V2

| Decision | Authoritative owner |
| --- | --- |
| Asian timing | Strategy Contract: `SESSION_FLOW_V2` |
| London timing | Strategy Contract: `SESSION_FLOW_V2` |
| Expected candle count | Strategy Contract |
| ER formula and threshold | Strategy Contract |
| Midpoint routing role | Strategy Contract (diagnostic only in signed V2) |
| Trend/Range routing | Strategy Engine |
| E1/E2/E3 precedence | Strategy Engine |
| Bias requirement and accepted source | Strategy Contract; Engine checks availability |
| Session OHLC, midpoint, ER calculation | Calculation component (“skill”), returning evidence |
| Sweep evidence | Calculation component, after Entry 2 contract is signed |
| Range-rejection evidence | Calculation component implementing RANGE_SETUP_V2 |
| Entry price rule | Strategy Contract; calculation component applies it |
| Risk parameters and management | Strategy Contract |
| Risk mathematics | Calculation component |
| Structural Sweep gate | Entry 2 Contract + Validator; never inherited by Entry 3 |
| Position-size policy | Strategy Contract/account policy |
| Position-size mathematics | Calculation component |
| Route and direction consistency | Contract Validator |
| Order authorization | Strategy Engine + Contract Validator |
| Ticket formatting | Presentation component |
| Broker submission | Execution layer only |
| Fill truth | M1/broker execution layer only |

## Strategy contract gap analysis

### Regime classifier

| Item | Status | Evidence |
| --- | --- | --- |
| Exact ER formula | **SIGNED** | Path-based formula in `SESSION_FLOW_V2_SPEC.md` |
| ER threshold | **SIGNED** | `0.40` |
| Threshold equality | **SIGNED** | `ER >= 0.40 -> TREND` |
| Open/Close vs midpoint rule | **SIGNED** | Diagnostic only; cannot route or veto |
| Equality at midpoint | **SIGNED** | Explicit diagnostic labels required; no routing effect |
| Conflicting ER/midpoint cases | **SIGNED** | No conflict state; ER alone governs |
| Implementation | **MISSING** | Legacy `lock_asian_levels` uses displacement divided by range, not path length |

The user request's conceptual “midpoint plus ER” classifier is not the current signed
V2 contract. The signed repository contract is ER-only. Implementing a combined rule
would be a new challenger contract, not a refactor.

### Entry 1 — Trend

| Item | Status | Minimum missing decision |
| --- | --- | --- |
| Eligibility | **SIGNED** | `REGIME = TREND` |
| Direction | **PARTIAL** | “causally resolved bias” is required, but its authoritative source and resolution timestamp are not signed |
| Exact trigger | **UNSIGNED** | Define completed-bar event or resting-order condition |
| Signal/entry price | **UNSIGNED** | Define price and order semantics |
| Invalidation / expiry | **UNSIGNED** | Define pre-fill cancellation and post-fill invalidation |
| Management | **CONFLICT/PARTIAL** | V2 common 4R/5R/no-BE intent exists, while historical Trend material includes trailing variants; state V2 rule explicitly for E1 |

### Entry 2 — Sweep

| Item | Status | Minimum missing decision |
| --- | --- | --- |
| Eligibility and precedence | **SIGNED** | Range-only, evaluated before Entry 3 |
| Direction mapping | **SIGNED** | High -> Short; Low -> Long |
| Sweep qualification | **PARTIAL/CONFLICT** | Select/version the authoritative definition; current experiment includes 2.5% reclaim clearance and structural gate but the master spec calls reconciliation required |
| Exact entry | **PARTIAL** | Sweep Close is the experimental candidate, not yet reconciled/frozen as full V2 authority |
| Signal vs fill | **PARTIAL** | M15 signal authority is clear for Entry 3; Entry 2 still uses idealized signal-close fill in the experiment |
| Structural stop treatment | **PARTIAL** | Gate is intended for Sweep, but exact evidence/schema and failure terminal must be frozen |
| Observation window / trade limit | **PARTIAL** | Master routing implies shared legs; explicitly bind Entry 2 to the V2 windows and one-fill limit |

### Entry 3 — Range

All material strategy decisions are **SIGNED** in `RANGE_SETUP_V2_SPEC.md`: eligibility,
precedence, exact-zero boundary tolerance, dual-boundary ambiguity, directional trigger,
M15 signal price, M1 fill authority, fixed 1R stop, 75% at 4R, 25% at 5R, no automatic
breakeven, observation windows, cancellation, and one filled trade per leg.

Implementation status: **MISSING**, intentionally blocked until the full contract gate.

### Common downstream rules

| Item | Status | Note |
| --- | --- | --- |
| `1R = 0.25 × reference range` | **SIGNED for Range; intended common rule** | Explicitly restate in completed E1/E2 contracts |
| 75% partial at fixed 4R | **SIGNED for Range; intended common rule** | Legacy opposite-boundary partial must not leak into V2 |
| 25% final at fixed 5R | **SIGNED for Range; intended common rule** | Preserve original stop after partial in V2 Range |
| Automatic breakeven | **SIGNED ABSENT for V2 Range** | Do not reuse legacy simulators that move to BE |
| Observation windows | **SIGNED for master sessions and Range** | Bind E1/E2 explicitly |
| Maximum trades | **SIGNED for Range** | One filled trade per leg; bind strategy-wide behavior explicitly |
| Account-risk fraction / position sizing | **UNSIGNED for executable V2** | `risk_fraction = 0.25` is price-risk distance, not account-risk fraction; do not conflate them |
| Costs and executable metadata | **PARTIAL** | Required but values/source are run-dependent; missing fields must yield `ANALYSIS_ONLY` |

## Minimal target architecture

Do not create one class per box in the flowchart. The smallest useful V2 design is:

```text
session_strategy/v2/
  contract.py      immutable parsed SESSION_FLOW_V2 parameters and version
  evidence.py      pure session geometry, path ER, sweep facts, range-rejection facts
  engine.py        one run_session_strategy() router for both reference legs
  validator.py     deterministic candidate/risk/contract consistency checks
  schema.py        structured evidence, candidate, validation, trace, and result records
  risk.py          common price-risk/target math and optional sizing math
  execution.py     interface only; M1/broker fill truth lives behind it
```

Existing `session_contract.py` may become the session portion of `contract.py`; do not
move it merely to match this sketch. Legacy modules remain importable on their frozen
paths.

Conceptual V2 router:

```text
validate and freeze reference
  -> calculate geometry and ER evidence
  -> contract classifies ER
  -> TREND: require signed bias, build E1, stop setup routing
  -> RANGE: calculate Sweep evidence
       -> qualified: build E2
       -> not qualified: calculate Range evidence, build E3 or no setup
  -> common risk math
  -> validate contract, direction, causality, quota, risk, and execution fields
  -> authorized analytical ticket OR deterministic no-trade/analysis-only result
```

The engine must not import MT5, render charts, compute broker volume without injected
metadata, or simulate fills. Calculation functions return evidence and never choose
E1/E2/E3. A skill/engine direction mismatch yields:

```text
reason_code      = STRATEGY_SKILL_CONFLICT
order_authorized = false
trade_opened     = false
```

## Lightweight V2 validator contract

Required checks and deterministic failure codes:

| Check | Example failure code |
| --- | --- |
| Contract/version and reference leg present | `INVALID_CONTRACT_ID`, `INVALID_REFERENCE` |
| Exact completed contiguous M15 reference | `INVALID_REFERENCE_SESSION` |
| Regime is contract-derived from recorded ER evidence | `REGIME_EVIDENCE_MISMATCH` |
| Setup is eligible for regime and precedence | `INVALID_SETUP_ROUTE` |
| Candidate direction matches signed boundary/bias mapping | `STRATEGY_SKILL_CONFLICT` |
| Entry model and price match component contract | `ENTRY_MODEL_MISMATCH` |
| SL/TP/partial sizes match common risk math | `RISK_CONTRACT_MISMATCH` |
| Sweep structural gate applies only to E2 | `INVALID_STRUCTURAL_GATE_SCOPE` |
| Signal uses no future/unclosed bar | `CAUSALITY_VIOLATION` |
| Signal/order lies inside observation window | `OUTSIDE_OBSERVATION_WINDOW` |
| One filled trade per leg | `TRADE_LIMIT_EXCEEDED` |
| Required M1/broker/account metadata present for executable claims | `ANALYSIS_ONLY_MISSING_EXECUTION_FIELDS` |

Validation failure always sets `order_authorized = false`. The validator does not
repair, reinterpret, or choose a competing strategy path.

## Required Engine/Skill boundary tests for Phase B

Do not add these tests until the missing contracts are signed; their expected values
would otherwise invent rules.

1. Trend + Up bias -> E1 Long; Trend + Down bias -> E1 Short.
2. Range + qualified High sweep -> E2 Short; Low sweep -> E2 Long.
3. Range + no Sweep + upper rejection -> E3 Short; lower rejection -> E3 Long.
4. Trend never evaluates Sweep or Range evidence.
5. Range evaluates Sweep before Range and cancels only an unfilled Range candidate.
6. Engine/skill direction mismatch -> `STRATEGY_SKILL_CONFLICT`, order blocked.
7. Future-data perturbation and dataset truncation leave earlier decisions unchanged.
8. Exact ER hand calculation, zero-path behavior, and `ER == 0.40` boundary.
9. Midpoint diagnostic conflict cannot change ER-only regime.
10. No same-close executable fill claim without authoritative M1 data.
11. Entry 3 keeps the original SL after 4R and never inherits the Sweep structural gate.
12. Both V2 legs run through the same router with their own immutable window definitions.
13. Frozen `SESSION_FLOW_V1` and SSPF v1.3 golden outputs reproduce unchanged.

## Golden decision trace schema

Store structured fields, then render them. Do not store free-form model reasoning as
the decision source.

```text
contract: {id, version, hash}
reference: {leg, start, end, expected_bars, observed_bars, valid}
box: {open, high, low, close, midpoint, range}
regime_evidence: {directional_displacement, path_length, er, threshold,
                  open_vs_midpoint, close_vs_midpoint}
regime: TREND | RANGE
bias_evidence: {source, value, resolved_at} | null
sweep_evidence: {evaluated, qualified, side, extreme, reclaim_price, signal_time}
range_evidence: {evaluated, qualified, boundary, signal_price, signal_time}
routing: {setup: ENTRY_1 | ENTRY_2 | ENTRY_3 | NONE, direction, reason_code}
risk: {one_r, stop, partial_target, partial_size, final_target, runner_size}
validation: {passed, reason_codes, order_authorized}
execution: {status: NOT_REQUESTED | ANALYSIS_ONLY | PENDING | FILLED, fill_source}
```

## Minimum decisions required before Phase B

1. Sign the complete Entry 1 contract: causal bias source, resolution time, exact
   trigger, signal/entry price, order type/fill semantics, pre-fill invalidation,
   observation window, and management.
2. Reconcile and sign Entry 2: one authoritative Sweep definition/version, threshold
   parameters, dual-boundary behavior, signal/entry price, M1 fill semantics,
   structural-stop evidence and failure code, observation window, and one-trade rule.
3. State whether the 25%/4R/5R/no-breakeven common framework applies identically to
   E1 and E2; record any setup-specific exception explicitly.
4. Define the V2 executable position-sizing policy, or explicitly keep all V2 output
   `ANALYSIS_ONLY`. Distinguish price-risk distance (`0.25 × range`) from account-risk
   fraction.
5. Identify and pin the actual `SSPF_V1_3_BASELINE_FROZEN` reproduction package.
6. Bind V2 verification to an audited dataset fingerprint and exact runtime.

## Final report

```text
REPOSITORY
branch: master
HEAD: 2b58c4f011de45bd6d15fca72a091ad72aa99958
working tree: DIRTY before audit; 6 tracked modifications plus numerous untracked files

CURRENT ARCHITECTURE
strategy engines: ASIAN_SESSION_V1 monolith; SESSION_FLOW_V1 scripts; multiple source,
                  flowchart, backtest, and Sweep experiment engines; no V2 router
agent skills: 7 general research-method skills plus conceptual capabilities spread
              across ordinary Python modules
execution components: read-only MT5 gateway, M15 historical simulators, renderers;
                      no authoritative V2 M1 execution adapter

DUPLICATE AUTHORITIES
count: 14 decision categories
details: session timing, ER formula/threshold, midpoint rule, bias, Sweep, Range,
         precedence, entries, risk/management, sizing, authorization, and fills

CONTRACT GAPS
count: 6 minimum decision groups
details: complete E1; reconciled E2; common E1/E2 risk/management; executable sizing
         policy; exact SSPF v1.3 frozen package; V2 data/runtime binding

SKILLS
keep: session-leg contract, renderers, ledger, general research-method skills
simplify: session geometry, ER evidence, risk math, sizing math, ticket formatting
merge: duplicate midpoint/ER/risk calculations only inside a new versioned V2 path
legacy-only: current engine, V1/source engines, flowchart and historical simulators
deprecate: use of large experimental engines as foundations for new V2 development
missing: V2 bias, E1, reconciled E2, V2 validator, M1 execution/fill adapter

TARGET ENGINE
one reusable session router: Trend -> E1; Range + Sweep -> E2;
Range + no Sweep + rejection -> E3; then common risk and deterministic validation

BASELINE IMPACT
SSPF v1.3: unchanged; exact frozen reproduction package still needs identification
SESSION_FLOW_V1: unchanged; rejected ledger identity and historical path preserved

TESTS
passed: 14 focused tests (V2 session contract and read-only safety boundary)
failed: 0
skipped: V2 engine/skill implementation tests deferred because CONTRACT_READY = NO

READINESS
ARCHITECTURE_READY: YES
CONTRACT_READY: NO
REFACTOR_READY: NO

FILES CHANGED
STRATEGY_ENGINE_SKILL_AUDIT.md

NEXT RECOMMENDED ACTION
Sign one consolidated Entry 1 and Entry 2 closure addendum for SESSION_FLOW_V2,
including the common risk/management statement, then request Phase B explicitly.
```

# Known test failures

Formal classification of every test allowed to stay red in the global suite (`pytest tests/`).
Anything not listed here failing is a regression and must be fixed before merge — see
`tests/execution/` / execution-specific suites below for the hard release gate.

**Global suite as of 2026-08-25: 241 passed, 4 failed. All 4 are listed here.**

| Test | Reason | Execution-affecting? | Expected remediation |
|---|---|---|---|
| `tests/test_engine.py::EngineTests::test_governance_approves_stage_2_baseline_and_locks_optimization` | **Intentional.** `config/strategy.yaml` was corrected 2026-08-25 (`account_guard.required_server`/`fallback_account_suffix` fixed to match the real demo account), which legitimately changed the config's computed hash away from the one recorded in `governance.parameter_signoff.config_hash` at the 2026-08-22 approval. The test correctly detects this drift. | No — this is a signoff/governance gate, not an execution-path bug. | **Trader re-signoff of the current config**, then update `parameter_signoff.config_hash` to the new live hash and this test passes again. Do not "fix" the test itself — that would hide a real unresolved approval gap. |
| `tests/test_golden_fixtures.py::GoldenFixtureTests::test_versioned_golden_cases` | Classifier now returns `UNCERTAIN` where a golden case expects `RANGE`. Predates this session's work (present before 2026-08-25 execution-layer changes). | Possibly — affects session classification, which the executor consumes via `analyze()`. Not caused by anything in `session_strategy/execution/`. | Needs its own investigation into the classifier/golden-case mismatch; out of scope for the execution-hardening work. |
| `tests/test_safety.py::SafetyTests::test_no_forbidden_mt5_call_appears_anywhere_in_the_package` | Fails because `mt5_gateway.py` legitimately contains `order_send`/`order_check` — added 2026-08-22 for the execution layer. This test asserted the pre-execution-layer "no order-mutating call anywhere" boundary and was never updated for the intentional `MT5ReadOnlyGateway`/`MT5ExecutionGateway` split. | Yes, directly — this is the test that used to prove the read-only boundary claims made elsewhere in the docs (`README.md`). | Rewrite the test to assert the boundary correctly: `order_send`/`order_check` must appear **only** on `MT5ExecutionGateway`, never on `MT5ReadOnlyGateway` or anywhere else in the package. Not yet done. |
| `tests/test_source_v1.py::test_literal_midpoint_trend_entry_and_stop` | Legacy `source_v1.py` module — `detect()` returns `None` where a trend entry is expected. Predates this session's work. | No — `source_v1.py` is a retired/legacy module (see `STATUS.md` §5 "Unverified source transcripts"), not part of the live `ASIAN_SESSION_V1` execution path. | Low priority; the module it tests is already superseded lineage. |

## Execution release gate

Per the phased execution-hardening plan (`STATUS.md`), the following must be **100% pass, zero
exceptions**, independent of the four failures above, before any real `order_send` is trusted:

```
pytest tests/test_execute_session_signal.py
pytest tests/test_execution_gates.py
```

(No separate `tests/execution/` directory exists yet in this repo — these two files are
currently the full execution-specific suite. If new execution test files are added, list them
here too.)

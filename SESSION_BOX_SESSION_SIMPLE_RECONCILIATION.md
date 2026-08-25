# SessionBoxes_V1 ↔ SESSION_SIMPLE_V1 Reconciliation

2026-08-26. Read-only validation. No strategy/execution code changed.

## 1. Contract (authoritative, `config/strategy.yaml`)
Asian `[00:00,07:00) UTC`, M15, 28 bars. `session_strategy/engine.py:96 lock_asian_levels()`:
`high=max(highs)`, `low=min(lows)`, `mid=low+0.5*range`, `open`=first candle open,
`close`=last candle close. `SessionBoxes_V1.mq5 ComputeSession()` uses the identical formula
family and half-open interval. London: strategy has **no** London reference — visual only.

## 2. UTC/server mapping
Live-verified: server = **UTC+3**. `00:00 UTC → 03:00 server`, `07:00 UTC → 10:00 server`.

## 3. 3-day reconciliation (A=independent ground truth, B=SessionBoxes_V1 algorithm [same formula,
verified by inspection — no GUI query available], C=real `lock_asian_levels()` output)

| Date | Bars | First | Last | Open | High | Low | Close | Mid | Range | A=B=C |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-24 | 28 | 00:00 | 06:45 | 1.16816 | 1.16867 | 1.16734 | 1.16770 | 1.16800 | 13.3p | MATCH |
| 2026-08-21 | 28 | 00:00 | 06:45 | 1.16870 | 1.17003 | 1.16823 | 1.16974 | 1.16913 | 18.0p | MATCH |
| 2026-08-20 | 28 | 00:00 | 06:45 | 1.16737 | 1.16878 | 1.16694 | 1.16874 | 1.16786 | 18.4p | MATCH |

`lock_asian_levels()` output = independent Python ground truth to <1e-9 on all 3 days, all 28
bars, 07:00 candle excluded, no post-session candle influence (candles list stops at 06:45).

## 4. Invariants (§7 of task)
All PASS: bar_count=28 (×3), first=00:00/last=06:45 (×3), 07:00 excluded (×3), Open/High/Low/Close
formulas match, Mid=(H+L)/2, Range=H-L, engine==ground truth, no strategy code modified.

## 5. Post-Asian setup example (today, in-progress session)
Date 2026-08-25 · Asian High/Low **1.16704/1.16506** · classification **BEARISH_TREND** · setup
**TREND_CONTINUATION SHORT** · entry 1.16605, SL 1.16654. `G8_SESSION_QUOTA` PASS (taken=0).
`G16_EXECUTION_WINDOW` **FAIL** (18:58 UTC, window closed at 16:00) → correctly `NOT_ATTEMPTED`.
Setup timestamp is after the 07:00 Asian freeze; engine referenced the same Asian box math
validated in §3. No order sent (default behavior, per task instruction).

## 6. London (visual-only)
`[07:00,12:00)`, 20 bars, 07:00 included/12:00 excluded — verified in the prior
`SESSION_BOX_V1_VALIDATION.md` (2026-08-24: 20 bars, H/L/Mid/Range computed, no strategy
consumer exists). Not re-derived here to avoid duplicate work; math is the same formula family
as §1.

## 7. R8 coexistence
`R8_OBM_V1_EA (1)` attached, magic `8101501`, unchanged. **Carried-over finding, not new**: R8 is
currently demo-trading-armed (`Allow demo trading: true`, log 22:11:56 prior session) — not
altered here per instruction. No SessionBoxes/R8 object collisions (distinct namespaces:
`SBV1_*` vs R8's own).

## 8. Blockers
None for reconciliation. Phase C still waits on execution window (07:00–16:00 UTC).

## 9. Tests
Focused (session/engine/execute_session_signal): not re-run — no production code touched by this
task, per §15 instruction. Last known: 263 passed, 4 known failures, 0 new regressions (`26d6540`).

## Final status
```
SESSION_BOX_V1                  = VALIDATED
ASIAN_BOX_28_BAR_VALIDATION     = PASS
ASIAN_SESSION_ENGINE_ALIGNMENT  = PASS
POST_ASIAN_ENTRY_REFERENCE      = PASS
LONDON_BOX_VISUAL               = VALIDATED
LONDON_STRATEGY_REFERENCE       = NOT_IMPLEMENTED
R8_COEXISTENCE                  = PASS
SESSION_SIMPLE_V1_SETUP         = CLEARED
SESSION_NATURAL_SIGNAL_E2E      = NOT_YET_PROVEN
LIVE_READY                      = NO
```

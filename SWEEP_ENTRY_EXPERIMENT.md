# Sweep-entry experiment 0.2.0

This research variant implements the explicit recommendations from the shared
“Explain Session Range Reversal” discussion without altering `SESSION_FLOW_V1`.

## Frozen inputs

- EURUSD M15 development data only; `data/sealed/` is forbidden.
- UTC reference window `00:00 <= t < 08:00`, exactly 32 bars.
- Execution observation window `08:00 <= t < 16:00`.
- Range/Trend remains a frozen experimental assumption. Bias is explicitly
  deferred because Claude SSOT blocker B1 is unresolved; LONG and SHORT
  geometry are reported separately and cannot yet become executable tickets.

## Proposed rules under test

1. Print the raw/source sweep time and normalized UTC entry time separately.
2. Require a range-normalized reclaim clearance of 2.5%.
3. Validate the fixed 25%-range stop against the sweep extreme known at entry.
4. Reject rather than widen an invalid stop.
5. Compare entry at the reclaim close with entry at the next directional confirmation close.
6. Separate detected setups from risk-eligible entries.
7. Report required structural risk as a fraction of the reference range.
8. Print broker UTC+3 and normalized UTC event times separately for this dataset.

Each record carries the canonical timestamp schema: source timestamp/timezone/
offset, broker and UTC reference boundaries, and UTC attack, extreme, reclaim,
confirmation, signal, order, and fill times. Reference end timestamps are
exclusive (`08:00 UTC`, equivalent to `11:00` broker for this dataset).

The experiment uses an explicitly labelled `IDEALIZED_SIGNAL_BAR_CLOSE` fill.
It does not claim that a signal learned at a bar close can always be filled at
that exact historical close. A next-bar-open fill model is a separate future
experiment.

These are experiments, not corrections to the baseline. Oct 3–21 results cannot
promote a rule because the same sample motivated the hypotheses.

```powershell
python scripts/sweep_entry_experiment.py --json outputs/sweep_entry_experiment_2022-10.json
python -m pytest tests/test_sweep_entry_experiment.py -q
```

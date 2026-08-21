# Image-analysis protocol — adoption record

Adopted 2026-08-17 from the supplied agent prompt, with three distinct statuses.
**Do not treat these as equally final.**

| § | Item | Status |
|---|---|---|
| 4 | Asian reference window | **LOCKED — replaced** |
| — | Half-open boundary | **LOCKED** |
| 7 | Decision-tree shape | **ADOPT** |
| 10 | RANGE entry: BUY→bottom, SELL→top | **ADOPT** |
| 11 | TREND entry: midpoint | **ADOPT** |
| 12–14 | Risk mathematics | **ADOPT** |
| 16 | No look-ahead + outcome isolation | **ADOPT, strengthened** |
| 20 | Source precedence | **ADOPT** |
| 8 | Open/close same-side classifier | **PROVISIONAL — 3 of 4** |
| 9 | Sweep side from which side was swept | **RULE CORRECT · ENGINE NON-CONFORMANT** |
| 5.5 | Oct 4 range discrepancy | **OPEN — do not force** |

---

## LOCKED · §4 — the Asian reference window

The prompt specified `22:00 → 07:00 UTC, 36 M15 candles`. **Replaced.**

```
Asian reference session
  Start : 00:00 UTC   INCLUSIVE
  End   : 07:00 UTC   EXCLUSIVE
  M15, expected 28 candles
  Included : 00:00, 00:15, ... 06:45
  Excluded : 07:00 and later
```

The half-open form is the operative part — it removes the boundary ambiguity that
neither backtest nor automation can otherwise resolve consistently.

Superseded under the prompt's own §20 precedence (locked spec > timestamps > video
rectangle) and its own §4 escape clause. Evidence: Oct 6 annotates `A = 33.3`;
`00:00–07:00` reconstructs **33.3p exactly**, `22:00–07:00` gives **44.6p**.

## LOCKED · §16 — outcome isolation, made machine-checkable

```
Outcome MAY be used for: historical chart identification only.

Outcome MUST NEVER be an input to:
  session classification · setup classification · direction
  entry validation · SL/TP generation
```

Adopted verbatim. This converts a judgement call into a testable property and pairs
with `AGENT_SKILLS.md` B12 (truncation invariance), which enforces the same thing at
the engine level.

---

## PROVISIONAL · §8 — the same-side classifier

```
Open and Close on the same side of the midpoint      -> candidate RANGE
Open and Close on opposite sides                     -> candidate TREND

Status     : PROVISIONAL
Validation : 3 of 4 trader-confirmed classifications
Failure    : Oct 4 (open 0.98334 below mid, close 0.98704 above -> says TREND,
             trader says RANGE)
```

**Not promoted.** The efficiency ratio scores identically — 3 of 4 — and **fails on
the same session**. Two independent statistics failing on one case points upstream of
both, not at either.

Do not promote until Oct 4 resolves or a deterministic exception is defined.

---

## ENGINE DEFECT · §9 — sweep side, elevated above §8 calibration

The prompt states the correct logic. **The engine does the reverse.**

```
INTENDED                          ENGINE (session_flow.py:80)
  observe which boundary            determine bias
  was swept                              |
      |                             select expected side
  derive direction                       |
      |                             search for a sweep THERE
  classify
```

The second form is confirmation bias in code — it looks for the sweep it already
expects. Required shape:

```
high_swept = price trades beyond reference_session_high
low_swept  = price trades beyond reference_session_low

high only -> bearish candidate      both     -> ambiguous, declare handling
low  only -> bullish candidate      neither  -> no sweep -> RANGE SETUP
```

Bias applies only **after** neutral detection. This is `ENGINE_FIX_SPEC.md` FIX 1 and
it now takes priority over any §8 threshold work — §8 cannot be calibrated against a
classifier whose sweep branch is selected by the answer.

---

## OPEN · §5.5 — the Oct 4 range discrepancy

```
annotated              43.2p
00:00-07:00            66.0p     no match
22:00-07:00            66.0p     no match
```

**Exhaustive search run 2026-08-17.** Every start hour from 20:00 (prior day) to
03:00, every end hour from 04:00 to 10:00, wick-range and body-range — 112
combinations scored against all four annotated dates at 1.0 pip tolerance:

```
 hits   start    end   mode    Oct3   Oct4   Oct5   Oct6
                     target    50.2   43.2   31.1   33.3
    3   22:00   06:00   wick    50.1   43.0   31.2   44.6
    3   00:00   06:00   wick    50.1   43.0   31.2   23.4
    2   00:00   07:00   wick    50.1   66.0   35.7   33.3   <- locked window
```

**No combination reproduces all four. Best is 3 of 4.**

And the misses split cleanly:

- a **06:00** end fits Oct 3, 4, 5 — and breaks Oct 6 badly (23.4 or 44.6 vs 33.3)
- a **07:00** end fits Oct 3 and Oct 6 **exactly** — and breaks Oct 4 and Oct 5
- Oct 3 fits either

So the two hypotheses fit **different subsets**, and neither dominates. The cause is
therefore **not** session start, session end, or wick-versus-body — those are now
exhausted.

Remaining candidates, in the reviewer's order:

1. boundary-candle inclusion — *tested, does not explain it*
2. broker timezone / candle alignment differences between his feed and the fixture
3. wick vs body — *tested, does not explain it*
4. chart feed differences (his charts appear EIGHTCAP; fixture is VT Markets)
5. hidden or manually anchored box, drawn by eye rather than to session time
6. alternate session end — *tested, does not explain it*

**Three of six are eliminated.** Feed difference and manual anchoring are the live
candidates, and both are per-chart rather than systematic — consistent with the
subsets not lining up.

> **Do not move the locked window to make Oct 4 fit.** A 3-of-4 window that breaks an
> exactly-matching date is not an improvement; it is a different error.

---

## Next, in order

1. **FIX 1** — neutral two-sided sweep detection. Elevated above §8.
2. Re-run the four-date golden set under FIX 1.
3. Only then revisit §8, once the sweep branch is no longer selected by bias.
4. §5.5 stays open pending a feed-level explanation.

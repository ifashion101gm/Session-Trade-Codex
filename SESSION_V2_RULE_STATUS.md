# SESSION V2 Rule Status

Date: 2026-08-23
Contract: `SESSION_STRATEGY_V2_RESEARCH` v2.0-research

| Rule | Status | Evidence / authority |
| --- | --- | --- |
| Completed immutable reference box | `CONTRACT_LOCKED` | Attached owner ruling; pure box freezer |
| Asian reference timing | `CONTRACT_LOCKED` | `00:00-07:00 UTC`, 28 M15 bars |
| London reference timing | `CONTRACT_LOCKED` | `07:00-12:00 UTC`, 20 M15 bars where supported |
| Regime is Trend or Range | `CONTRACT_LOCKED` | Attached owner ruling |
| ER 0.40 classifier | `REJECTED_AS_AUTHORITATIVE` / `RESEARCH` | Existing 90-box V2 study only; not the new regime authority |
| Open/close midpoint-side classifier | `REJECTED_AS_AUTHORITATIVE` / `RESEARCH` | Attached owner ruling |
| Final Trend/Range classifier | `RESEARCH` | No validated candidate currently signed |
| Trend Bias V1 | `RESEARCH` | Structural evidence model; no outcome inputs |
| Trend entry at midpoint | `CONTRACT_LOCKED` | Attached owner ruling and benchmark geometry |
| Strict established-level Sweep | `RESEARCH_VALIDATION_REQUIRED` | New pure evidence module; October reconciliation pending |
| Range fallback | `CONTRACT_LOCKED / IMPLEMENTATION_PENDING` | Boundary rejection contract; direction remains explicit |
| Risk distance | `CONTRACT_LOCKED` | `1R = 25%` of frozen range |
| Targets | `CONTRACT_LOCKED` | 75% at 4R, remainder at 5R |
| Breakeven or trailing | `RESEARCH_ONLY` | Not in the clean canonical baseline |
| M15 signal versus fill | `CONTRACT_LOCKED` | Signal and fill are separate |
| M1 authoritative fill | `REQUIRED / UNAVAILABLE` | No M1 Bid/Ask files found |
| Broker-realistic results | `UNAVAILABLE` | Missing authoritative M1 and complete cost inputs |
| Live/demo order placement | `DISABLED` | Existing read-only safety boundary preserved |

## Explicit version boundaries

The existing `SESSION_FLOW_V2_SIMPLE` implementation remains a historical, validated
ER-only comparator. Its 90-box counts must not be reported as the attached prompt's
30-case reconstruction. `COWORK_SWEEP_V2` remains retired audit history.

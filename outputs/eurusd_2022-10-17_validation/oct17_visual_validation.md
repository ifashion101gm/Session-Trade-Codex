# October 17 Visual Validation

The chart is rendered directly from VT Markets EUR/USD M15 bars normalized to
UTC. It separates the three session boxes from the trade risk/reward overlays.

| Element | Source screenshot | Rendered MT5 validation |
| --- | --- | --- |
| Asian | Narrow horizontal balance | 00:00–07:00, 25.3 pips |
| London | Low extension followed by recovery | 07:00–12:00, 50.6 pips |
| New York | Large bullish expansion | 12:00–18:00, 122.6 pips |
| London entry | Long after Asian-low reclaim | Long Sweep, 0.97338 |
| New York entry | Long continuation | Long Range, 0.97707 |

## Validated results

- Asian → London: TP5 hit, +3.894R gross, +3.780R after friction.
- London → New York: TP5 hit, +4.250R gross, +4.183R after friction.
- Combined: +8.144R gross and +7.962R after friction.

The screenshot and MT5 rendering agree on the overall three-session price
sequence. Exact outcome claims come from chronological M15 simulation, not from
the size of the manually drawn position rectangles in the screenshot.

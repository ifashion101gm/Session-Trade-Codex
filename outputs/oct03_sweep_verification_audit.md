# October 3 Asian-to-London Sweep Verification

## Flowchart decision

| Decision | Result |
| --- | --- |
| Bias | Bearish |
| Is Range Session? | Yes |
| Sweep During Session? | Yes |
| Selected source setup | Short Sweep Setup |

## Reference geometry

| Parameter | Value |
| --- | ---: |
| Asian high | 0.98344 |
| Asian low | 0.97843 |
| Asian range | 50.1 pips |
| Risk distance (25%) | 12.525 pips |

## Sweep-candle verification

The 15:00 UTC expansion candle pierces the high but has an upper-wick ratio of
only 0.112, so it is not accepted as the source rejection candle. The 15:15 UTC
candle has OHLC `0.98341 / 0.98447 / 0.98313 / 0.98342`; it pierces the Asian
high, closes back inside, and has an upper-wick ratio of approximately 0.784.
It therefore passes the required `>0.35` short-sweep wick test.

| Order parameter | Value | Source rule |
| --- | ---: | --- |
| Entry | 0.98342 | Outer edge of sweep candle body |
| Stop | 0.9846725 | Entry + 25% of Asian range |
| Leg A | 0.97843 | Opposite Asian boundary |
| TP5 | 0.9771575 | Entry − 5R |

The Sweep detector now derives this selection directly from candle structure;
it no longer depends on the post-loss cooldown accidentally suppressing the
preceding expansion candle.

## Remaining workflow distinction

The source-chart entry is unequivocally the 15:15 Sweep Setup. The causal engine
also generates an earlier 09:30 Range trade because, at 09:30, the later sweep
does not yet exist. Removing that earlier trade would require either an added
source rule that delays Range entries or retrospective knowledge of the later
sweep. It is therefore reported separately and is not treated as the pictured
source entry.

# Entry Database Schema

`entry_database.csv` is the canonical flat database of source, chart-validated,
and engine-validated entries.

- `evidence_status`: strength and origin of validation.
- `contract_version`: strategy contract used to generate the stored geometry.
- `active_contract_status`: `CURRENT` only after replay under the active contract;
  `REPLAY_REQUIRED` rows remain historical evidence but cannot validate the active engine.
- `source_outcome`: outcome established by the user/source; `UNCONFIRMED` when
  the image establishes geometry but not a reproducible result.
- `feed_outcome`: deterministic result from the connected MT5 bars.
- `flowchart_path`: Bias → Range? → Sweep? → selected Setup.
- `entry_rule`, `stop_rule`, `target_rule`, and `management_rule`: the source
  workflow basis displayed beside each stored result.
- All session windows and timestamps are UTC.
- Price geometry must satisfy risk = 25% of reference range and TP = 5R.
- Source/feed disagreement must be retained, never overwritten.
- The active v3.0 contract uses Asian 22:00–07:00 and the net-move/range classifier.
  Existing v2.23 rows use Asian 00:00–07:00 and are marked `REPLAY_REQUIRED`.

Allowed evidence statuses:

- `USER_CONFIRMED_TRUTH`
- `SOURCE_CHART_VALIDATED`
- `IMAGE_GEOMETRY_VALIDATED`
- `ENGINE_ONLY`

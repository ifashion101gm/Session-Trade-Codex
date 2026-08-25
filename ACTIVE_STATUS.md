# MT5 Active Status Report

*This is an auto-generated account snapshot, not a project status document. For project status,
open contracts, test results, and known issues, see [`STATUS.md`](STATUS.md).*

*Last successful read: 2026-08-25 (this session, via `mt5_status_check.py`).*
*A follow-up live re-check the same day failed with `MT5 initialization failed: (-10005, 'IPC
timeout')` — if this recurs, restart the MT5 terminal and re-run `mt5_status_check.py`.*

## Account overview

- **Login:** \*\*\*746 (masked) · **Type:** demo · **Server:** VTMarkets-Demo
- **Balance:** 1,000.00 USD
- **Equity:** 1,000.00 USD
- **Floating P/L:** 0.00 USD

## Positions and orders

- **Open positions:** 0
- **Pending orders:** 0

## Active strategies

No process was connected and trading at the time of this snapshot. The only strategy currently
authorized for demo execution is `ASIAN_SESSION_V1` (`config/strategy.yaml`); nothing is scheduled
to run it unattended. See `STATUS.md` for the full picture, including the blocked `SESSION_V2`
research track and the untracked `mt5_range_bar_live.py` experiment.

"""Independent two-stage release gate for SSPF.

Stage 1 checks that an analysis artifact and ticket faithfully represent the
configured deterministic rules. Stage 2 verifies a positive edge using only
completed, compliant, non-synthetic out-of-sample or forward-demo trades.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import math
import random

from .config import load_config
from .render import DISCLAIMER


@dataclass(frozen=True)
class StageResult:
    stage: str
    passed: bool
    status: str
    failures: list[str]
    metrics: dict

    def to_dict(self) -> dict:
        return asdict(self)


def load_lifecycle_config(path: str | Path | None = None) -> dict:
    source = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "lifecycle.json"
    return json.loads(source.read_text(encoding="utf-8"))


def assess_analysis(analysis_path: str | Path, ticket_path: str | Path,
                    strategy_config_path: str | Path | None = None,
                    lifecycle_config: dict | None = None) -> StageResult:
    cfg = lifecycle_config or load_lifecycle_config()
    strategy = load_config(strategy_config_path)
    data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    ticket = Path(ticket_path).read_text(encoding="utf-8")
    failures: list[str] = []
    acfg = cfg["analysis"]
    gates = data.get("gates", [])
    all_passed = bool(gates) and all(g.get("passed") is True for g in gates)

    if acfg["require_demo_account"] and data.get("account", {}).get("account_type") != "demo":
        failures.append("analysis was not produced from a demo account")
    if acfg["require_exact_config_hash"] and data.get("config_hash") != strategy.hash:
        failures.append("analysis config hash does not match the active strategy config")
    snapshot = data.get("config_snapshot")
    if acfg.get("require_config_snapshot"):
        if not isinstance(snapshot, dict) or not snapshot:
            failures.append("analysis has no embedded configuration snapshot")
        else:
            encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
            snapshot_hash = sha256(encoded).hexdigest()[:16]
            if snapshot_hash != data.get("config_hash"):
                failures.append("embedded configuration snapshot does not match config hash")
    if int(data.get("schema_version", 0)) < int(acfg.get("minimum_schema_version", 1)):
        failures.append("analysis schema version is unsupported")
    if data.get("strategy_id") != cfg["strategy_id"]:
        failures.append(f"analysis strategy_id is not {cfg['strategy_id']}")
    if data.get("contract_version") != cfg["contract_version"]:
        failures.append(f"analysis contract_version is not {cfg['contract_version']}")
    # A signal is accepted only when every gate passed AND a tradeable plan exists.
    expected_accepted = all_passed and data.get("entry") is not None
    if data.get("accepted") != expected_accepted:
        failures.append("accepted flag does not equal the recorded gate results")
    expected_status = "SIGNAL_ACCEPTED" if expected_accepted else "NO_TRADE"
    if data.get("status") != expected_status:
        failures.append("status does not match gate results")
    if acfg.get("require_reason_codes") and not data.get("reason_codes"):
        failures.append("analysis records no reason codes")
    if data.get("analysis_id") not in ticket:
        failures.append("ticket does not contain the analysis ID")
    if data.get("status") not in ticket:
        failures.append("ticket does not contain the canonical status")
    if acfg["require_disclaimer"] and DISCLAIMER not in ticket:
        failures.append("ticket is missing the fixed manual-execution disclaimer")
    if acfg["require_all_gates_in_ticket"]:
        missing = [g.get("name", "<unnamed>") for g in gates if g.get("name") not in ticket]
        if missing:
            failures.append("ticket is missing gates: " + ", ".join(missing))
    if acfg.get("require_plan_values_in_ticket") and data.get("status") == "SIGNAL_ACCEPTED":
        plan_fragments = {
            "entry": f"- Entry: {data.get('entry')}",
            "stop_loss": f"- Stop loss: {data.get('stop_loss')}",
            "tp1_4r": f": {data.get('tp1_4r')} (4R)",
            "tp2_5r": f"- TP2 (runner): {data.get('tp2_5r')} (5R)",
            "volume": f"- Volume: {data.get('volume')} lots",
        }
        missing_values = [name for name, fragment in plan_fragments.items()
                          if data.get(name) is None or fragment not in ticket]
        if missing_values:
            failures.append("ticket is missing or disagrees with plan values: "
                            + ", ".join(missing_values))

    return StageResult(
        stage="STAGE_1_ANALYSIS_CONFORMANCE",
        passed=not failures,
        status="ANALYSIS_CONFORMANT" if not failures else "ANALYSIS_NOT_CONFORMANT",
        failures=failures,
        metrics={"analysis_id": data.get("analysis_id"), "status": data.get("status"),
                 "gate_count": len(gates), "config_hash": data.get("config_hash")},
    )


def _max_drawdown(values: list[float]) -> float:
    equity = peak = drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _bootstrap(values: list[float], resamples: int, seed: int = 42) -> float:
    if not values:
        return 0.0
    rng = random.Random(seed)
    n = len(values)
    return sum(sum(values[rng.randrange(n)] for _ in range(n)) / n > 0
               for _ in range(resamples)) / resamples


def assess_profitability(trade_log_path: str | Path,
                         lifecycle_config: dict | None = None) -> StageResult:
    cfg = lifecycle_config or load_lifecycle_config()
    pcfg = cfg["profitability"]
    records = json.loads(Path(trade_log_path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("trade log must be a JSON array")
    eligible, rejected = [], 0
    for record in records:
        valid = (
            record.get("strategy_id") == cfg["strategy_id"]
            and record.get("contract_version") == cfg["contract_version"]
            and record.get("rule_compliant") is True
            and record.get("sample") in pcfg["accepted_samples"]
            and not record.get("synthetic", False)
            and "SYNTHETIC" not in str(record.get("note", "")).upper()
            and isinstance(record.get("r_multiple"), (int, float))
        )
        if valid:
            eligible.append(record)
        else:
            rejected += 1
    values = [float(r["r_multiple"]) for r in eligible]
    wins, losses = [v for v in values if v > 0], [v for v in values if v <= 0]
    gross_loss = abs(sum(losses))
    profit_factor = sum(wins) / gross_loss if gross_loss else math.inf
    expectancy = sum(values) / len(values) if values else 0.0
    drawdown = _max_drawdown(values)
    confidence = _bootstrap(values, pcfg["bootstrap_resamples"])
    failures: list[str] = []
    if len(records) < pcfg["minimum_total_trades"]:
        failures.append(f"need {pcfg['minimum_total_trades']} total recorded trades; found {len(records)}")
    if len(eligible) < pcfg["minimum_out_of_sample_trades"]:
        failures.append(f"need {pcfg['minimum_out_of_sample_trades']} compliant out-of-sample trades; found {len(eligible)}")
    if expectancy < pcfg["minimum_expectancy_r"]:
        failures.append("expectancy threshold not met")
    if profit_factor < pcfg["minimum_profit_factor"]:
        failures.append("profit-factor threshold not met")
    if confidence < pcfg["minimum_bootstrap_confidence"]:
        failures.append("bootstrap-confidence threshold not met")
    if drawdown > pcfg["maximum_drawdown_r"]:
        failures.append("maximum-drawdown threshold exceeded")
    if not math.isfinite(profit_factor):
        failures.append("profit factor is infinite; sample has no recorded losses and needs review")

    return StageResult(
        stage="STAGE_2_PROFITABILITY_VERIFICATION",
        passed=not failures,
        status="PROFITABILITY_VERIFIED" if not failures else "PROFITABILITY_NOT_VERIFIED",
        failures=failures,
        metrics={"total_records": len(records), "eligible_oos": len(eligible),
                 "rejected_records": rejected, "expectancy_r": expectancy,
                 "profit_factor": profit_factor, "max_drawdown_r": drawdown,
                 "bootstrap_confidence": confidence},
    )

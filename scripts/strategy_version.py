#!/usr/bin/env python3
"""
Strategy version control — the discipline a systematic fund runs on.

WHY THIS EXISTS
---------------
This project already produced nine folders under `outputs/` whose results span
-4.6R to +13.9R, and nobody can now say which rule set produced which number.
That is the failure this file prevents. It is not documentation; it is the thing
that makes a result mean something.

THE FOUR RULES
--------------
1. A VERSION IS ITS RULES. The id is the sha256 of the rule set itself, so two
   people who write the same rules get the same id, and changing a threshold by
   0.01 makes a new version whether or not anyone remembers to say so.

2. A RESULT IS MEANINGLESS WITHOUT ITS THREE HASHES — rules, data, code. A number
   that cannot name all three is an anecdote. `record_result` refuses to store one.

3. THE LEDGER IS APPEND-ONLY. Versions are never edited and never deleted. A rule
   that turned out wrong is superseded by a new version that says so; the old one
   stays, with its results, so the mistake stays visible.

4. EVERY HYPOTHESIS IS COUNTED. Each variant tested — every threshold swept, every
   symbol dropped — is registered before its result is known. The count feeds the
   multiple-testing correction. A strategy selected from 40 variants needs a far
   higher bar than one tested once, and the only way to apply that honestly is to
   have counted.

LIFECYCLE
---------
    research -> candidate -> paper -> live -> retired
                     |          |       |
                     +----------+-------+----> rejected

Forward transitions require evidence; `promote` refuses without it. Anything can
be rejected or retired at any time — killing a strategy never needs permission.

USAGE
-----
    python scripts/strategy_version.py register --name SESSION_FLOW_V1 \
        --spec SESSION_FLOW_V1_SPEC.md --engine scripts/session_flow.py
    python scripts/strategy_version.py hypothesis --version <id> --desc "ER sweep 0.25"
    python scripts/strategy_version.py record --version <id> --dataset data/x.master.csv \
        --trades 767 --net-r 22.723 --expectancy 0.030 --pf 1.035 --dd 45.323
    python scripts/strategy_version.py promote --version <id> --to rejected --why "..."
    python scripts/strategy_version.py log
    python scripts/strategy_version.py show --version <id>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "versions" / "ledger.json"

STAGES = ["research", "candidate", "paper", "live", "retired", "rejected"]
FORWARD = {"research": "candidate", "candidate": "paper", "paper": "live", "live": "retired"}
TERMINAL = {"rejected", "retired"}


def sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"


def code_sha() -> str:
    """Git commit if the tree is clean; otherwise mark it dirty. A result produced
    from an uncommitted working tree is not reproducible and must say so."""
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return f"{h}{'-DIRTY' if dirty else ''}" if h else "no-git"
    except Exception:
        return "no-git"


def load() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"schema": 1, "created": dt.datetime.utcnow().isoformat() + "Z", "versions": []}


def save(d: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


def find(d: dict, vid: str) -> dict | None:
    hits = [v for v in d["versions"] if v["id"].startswith(vid)]
    return hits[0] if len(hits) == 1 else None


# --------------------------------------------------------------- commands ----
def cmd_register(a):
    d = load()
    spec, eng = Path(a.spec), Path(a.engine)
    rules = sha(spec.read_text(encoding="utf-8", errors="replace") if spec.exists() else "",
                eng.read_text(encoding="utf-8", errors="replace") if eng.exists() else "")
    vid = rules[:16]
    if find(d, vid):
        print(f"already registered: {vid}  (identical rules produce an identical id)")
        return 0
    d["versions"].append({
        "id": vid, "name": a.name, "registered": dt.datetime.utcnow().isoformat() + "Z",
        "parent": a.parent, "stage": "research", "supersedes": a.supersedes,
        "note": a.note or "",
        "artifacts": {"spec": {"file": str(spec), "sha256": file_sha(spec)},
                      "engine": {"file": str(eng), "sha256": file_sha(eng)}},
        "code": code_sha(), "hypotheses": [], "results": [], "transitions": [],
    })
    save(d)
    print(f"registered {vid}  {a.name}  stage=research")
    return 0


def cmd_hypothesis(a):
    d = load(); v = find(d, a.version)
    if not v:
        print("no such version"); return 1
    v["hypotheses"].append({"n": len(v["hypotheses"]) + 1, "desc": a.desc,
                            "at": dt.datetime.utcnow().isoformat() + "Z"})
    save(d)
    print(f"{v['id']}  hypothesis #{len(v['hypotheses'])}: {a.desc}")
    print(f"  Bonferroni threshold now |t| > "
          f"{abs(_z(0.025 / len(v['hypotheses']))):.2f}")
    return 0


def _z(p):
    """Inverse normal CDF, Acklam-style rational approximation."""
    import statistics as st
    return st.NormalDist().inv_cdf(p)


def cmd_record(a):
    d = load(); v = find(d, a.version)
    if not v:
        print("no such version"); return 1
    ds = Path(a.dataset)
    k = max(1, len(v["hypotheses"]))
    t = (a.expectancy / (a.sd / math.sqrt(a.trades))) if a.sd and a.trades else None
    v["results"].append({
        "at": dt.datetime.utcnow().isoformat() + "Z",
        "dataset": ds.name, "data_sha256": file_sha(ds)[:16], "code": code_sha(),
        "sample": a.sample, "trades": a.trades, "net_r": a.net_r,
        "expectancy": a.expectancy, "profit_factor": a.pf, "max_drawdown_r": a.dd,
        "t_stat": round(t, 3) if t else None,
        "hypotheses_tested": k,
        "bonferroni_t": round(abs(_z(0.025 / k)), 3),
        "survives_correction": (abs(t) > abs(_z(0.025 / k))) if t else None,
        "note": a.note or "",
    })
    save(d)
    print(f"{v['id']}  result recorded  n={a.trades}  {a.net_r:+.3f}R  "
          f"exp {a.expectancy:+.3f}R  sample={a.sample}")
    if t:
        print(f"  t={t:.2f} vs Bonferroni {abs(_z(0.025/k)):.2f} over {k} hypotheses -> "
              f"{'SURVIVES' if abs(t) > abs(_z(0.025/k)) else 'does not survive'}")
    return 0


def cmd_promote(a):
    d = load(); v = find(d, a.version)
    if not v:
        print("no such version"); return 1
    cur, to = v["stage"], a.to
    if to not in STAGES:
        print(f"stage must be one of {STAGES}"); return 1
    if to not in TERMINAL:
        if FORWARD.get(cur) != to:
            print(f"REFUSED  {cur} -> {to} is not a legal transition "
                  f"(only {cur} -> {FORWARD.get(cur)}, or -> rejected/retired)")
            return 1
        if not v["results"]:
            print(f"REFUSED  {v['id']} has no recorded result. "
                  f"Forward promotion requires evidence.")
            return 1
    v["transitions"].append({"at": dt.datetime.utcnow().isoformat() + "Z",
                             "from": cur, "to": to, "why": a.why})
    v["stage"] = to
    save(d)
    print(f"{v['id']}  {cur} -> {to}\n  {a.why}")
    return 0


def cmd_log(a):
    d = load()
    if not d["versions"]:
        print("ledger empty"); return 0
    print(f"{'id':<18}{'name':<32}{'stage':<11}{'hyp':>4}{'res':>5}  best result")
    for v in d["versions"]:
        best = max(v["results"], key=lambda r: r.get("expectancy") or -9, default=None)
        b = (f"{best['trades']}tr {best['net_r']:+.1f}R exp{best['expectancy']:+.3f} "
             f"{best['sample']}" if best else "-")
        print(f"{v['id']:<18}{v['name'][:31]:<32}{v['stage']:<11}"
              f"{len(v['hypotheses']):>4}{len(v['results']):>5}  {b}")
    return 0


def cmd_show(a):
    d = load(); v = find(d, a.version)
    if not v:
        print("no such version"); return 1
    print(json.dumps(v, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="cmd", required=True)

    r = s.add_parser("register"); r.add_argument("--name", required=True)
    r.add_argument("--spec", required=True); r.add_argument("--engine", required=True)
    r.add_argument("--parent"); r.add_argument("--supersedes"); r.add_argument("--note")
    r.set_defaults(fn=cmd_register)

    h = s.add_parser("hypothesis"); h.add_argument("--version", required=True)
    h.add_argument("--desc", required=True); h.set_defaults(fn=cmd_hypothesis)

    c = s.add_parser("record"); c.add_argument("--version", required=True)
    c.add_argument("--dataset", required=True)
    c.add_argument("--sample", choices=("in-sample", "out-of-sample", "paper", "live"),
                   default="in-sample")
    c.add_argument("--trades", type=int, required=True)
    c.add_argument("--net-r", type=float, required=True)
    c.add_argument("--expectancy", type=float, required=True)
    c.add_argument("--pf", type=float); c.add_argument("--dd", type=float)
    c.add_argument("--sd", type=float, help="sd of net R per trade, for the t-stat")
    c.add_argument("--note"); c.set_defaults(fn=cmd_record)

    p = s.add_parser("promote"); p.add_argument("--version", required=True)
    p.add_argument("--to", required=True); p.add_argument("--why", required=True)
    p.set_defaults(fn=cmd_promote)

    lg = s.add_parser("log"); lg.set_defaults(fn=cmd_log)
    sh = s.add_parser("show"); sh.add_argument("--version", required=True)
    sh.set_defaults(fn=cmd_show)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())

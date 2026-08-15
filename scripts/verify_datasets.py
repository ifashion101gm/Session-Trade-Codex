#!/usr/bin/env python3
"""
Verify every dataset in data/ against its manifest.

Discovers all *.manifest.json under data/ and checks the recorded sha256 of the
master and each generated view. Exits non-zero if anything drifted, so it can be
used as a pre-commit hook or a CI step.

    python scripts/verify_datasets.py
    python scripts/verify_datasets.py --data-dir data
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(manifest: Path) -> tuple[int, int]:
    m = json.loads(manifest.read_text(encoding="utf-8"))
    d = manifest.parent
    checked = failed = 0

    entries = [("master", m["master"]["file"], m["master"]["sha256"])]
    entries += [("view", name, v["sha256"]) for name, v in m.get("views", {}).items()]

    print(f"\n{manifest.name}")
    print(f"  source {m.get('source_file','?')}  offset UTC+{m.get('server_offset_hours','?')}  "
          f"rows {m.get('rows','?')}  {m.get('utc_start','?')} .. {m.get('utc_end','?')}")

    for kind, name, want in entries:
        p = d / name
        checked += 1
        if not p.exists():
            failed += 1
            print(f"  FAIL  {kind:<6} {name}  MISSING")
            continue
        got = sha256(p)
        if got == want:
            print(f"  OK    {kind:<6} {name}  {got[:16]}")
        else:
            failed += 1
            print(f"  FAIL  {kind:<6} {name}  {got[:16]} != {want[:16]}")
            print(f"        drifted from master — rebuild with build_dataset.py, do not hand-edit")
    return checked, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    a = ap.parse_args()

    d = Path(a.data_dir)
    if not d.is_dir():
        print(f"no data directory at {d}")
        return 0

    manifests = sorted(d.glob("*.manifest.json"))
    if not manifests:
        print(f"no manifests under {d} — nothing to verify")
        return 0

    total = bad = 0
    for mf in manifests:
        c, f = verify(mf)
        total += c
        bad += f

    print(f"\n{len(manifests)} dataset(s), {total} artifact(s) checked, {bad} drifted")
    if bad:
        print("DATASET VERIFICATION FAILED")
        return 1
    print("all datasets consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run timestamp-preserving CICIoT2023 replay and matched shuffled-order controls."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xai_surfacebench.temporal_replay import shuffled_slots, simulate_trace_policy

POLICIES = ["never_explain","always_explain","threshold_explain","budget_only_bexgov","xai_gate","resource_aware_offload_adapted"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["quick","full"], nargs="?", default="full")
    parser.add_argument("--trace-dir", type=Path, default=ROOT / "data" / "ciciot2023_temporal" / "replay")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "temporal_replay" / "runs.csv")
    args = parser.parse_args()
    files = sorted(args.trace_dir.glob("*_slots.csv"))
    if args.mode == "quick": files = files[:2]
    rows = []
    for path in files:
        frame = pd.read_csv(path)
        for policy in POLICIES:
            rows.append(simulate_trace_policy(frame, policy=policy, session_id=path.stem, condition="chronological"))
            rows.append(simulate_trace_policy(shuffled_slots(frame, 2026), policy=policy, session_id=path.stem, condition="shuffled"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"runs={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

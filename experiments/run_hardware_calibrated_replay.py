#!/usr/bin/env python3
"""Replay temporal traces with compute profiles derived from measured action latency."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xai_surfacebench.hardware_benchmark import capacity_overlay
from xai_surfacebench.temporal_replay import simulate_trace_policy

ACTIONS = {"none":"none","delay":"delay","offload":"offload","audit":"audit","coarse":"coarse","redact":"redact","full_lime":"full","full_kernelshap":"full"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing-summary", type=Path, default=ROOT / "results" / "hardware_validation" / "timing_summary.csv")
    parser.add_argument("--trace-dir", type=Path, default=ROOT / "data" / "ciciot2023_temporal" / "replay")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "hardware_validation" / "replay_summary.csv")
    args = parser.parse_args()
    timing = pd.read_csv(args.timing_summary)
    rows = []
    for condition, group in timing.groupby("condition"):
        for explainer in ["full_lime","full_kernelshap"]:
            selected = group[group.action.isin(["none","delay","offload","audit","coarse","redact",explainer])]
            if selected.empty or explainer not in set(selected.action):
                continue
            med = {ACTIONS[row.action]: float(row.median_ms) for row in selected.itertuples()}
            p95 = {ACTIONS[row.action]: float(row.p95_ms) for row in selected.itertuples()}
            full = max(med["full"], 1e-9)
            overrides = {action:{"compute":value/full} for action, value in med.items()}
            for trace_path in sorted(args.trace_dir.glob("*_slots.csv")):
                trace = pd.read_csv(trace_path)
                for policy in ["always_explain","threshold_explain","budget_only_bexgov","xai_gate"]:
                    result = simulate_trace_policy(trace, policy=policy, session_id=trace_path.stem, condition=str(condition), action_profile_overrides=overrides, collect_action_trace=True)
                    overlay = capacity_overlay(result.pop("_action_trace"), p95)
                    result.update({f"hardware_{key}": value for key, value in overlay.items()})
                    result["explainer"] = explainer
                    rows.append(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else []
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"runs={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

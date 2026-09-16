#!/usr/bin/env python3
"""Run controller-estimate mismatch experiments with a fixed realization profile."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.estimation import assignment_disagreement, simulate_estimator_variant


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["quick","full"], nargs="?", default="full")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "estimator_mismatch")
    args = parser.parse_args()
    config_path = ROOT / "configs" / "estimator_mismatch.json"
    config = json.loads(config_path.read_text())
    variants = config["variants"]
    seeds = config["seeds"]
    regimes = config["regimes"]
    if args.mode == "quick":
        quick = config["quick_check"]
        seeds = quick["seeds"]
        regimes = quick["regimes"]
        allowed = set(quick["variants"])
        variants = [variant for variant in variants if variant["name"] in allowed]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in seeds:
        for regime in regimes:
            traces = {}
            run_rows = {}
            for variant in variants:
                row, trace = simulate_estimator_variant(config, config_dir=config_path.parent, seed=int(seed), regime=str(regime), variant=variant)
                traces[variant["name"]] = trace
                run_rows[variant["name"]] = row
            nominal = traces["nominal"]
            for variant in variants:
                name = variant["name"]
                row = run_rows[name]
                row["action_assignment_disagreement_rate"] = assignment_disagreement(nominal, traces[name])
                rows.append(row)
    path = args.output_dir / f"{args.mode}_synthetic_runs.csv"
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"runs={len(rows)}")
    print(f"output={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

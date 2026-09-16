#!/usr/bin/env python3
"""Summarize estimator-mismatch robustness results."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT / "results" / "estimator_mismatch" / "full_synthetic_runs.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "estimator_mismatch" / "summary.csv")
    args = parser.parse_args()
    frame = pd.read_csv(args.runs)
    metrics = ["high_risk_explanation_coverage","mean_explanation_debt","exposure_use","estimated_exposure_use","exposure_budget_violation_rate","action_assignment_disagreement_rate"]
    summary = frame.groupby(["regime","variant"], as_index=False)[metrics].mean()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Select exposure-feasible operating points for the literature-grounded comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/literature_comparison_selected.csv"))
    args = parser.parse_args()
    frame = pd.read_csv(args.summary_csv)
    coverage = "mean_high_risk_explanation_coverage"
    violation = "mean_exposure_budget_violation_rate"
    selected = []
    for policy, group in frame.groupby("policy"):
        feasible = group[group[violation].abs() <= 1e-12]
        pool = feasible if not feasible.empty else group.loc[group[violation] == group[violation].min()]
        selected.append(pool.sort_values([coverage, violation], ascending=[False, True]).iloc[0])
    out = pd.DataFrame(selected)
    args.output.parent.mkdir(parents=True, exist_ok=True); out.to_csv(args.output, index=False); print(out.to_string(index=False)); return 0


if __name__ == "__main__": raise SystemExit(main())

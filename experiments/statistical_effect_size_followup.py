#!/usr/bin/env python3
"""Paired seed-level effect sizes, bootstrap intervals, and exact sign tests."""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
import pandas as pd


def sign_test_p(values: list[float]) -> float:
    nonzero = [value for value in values if abs(value) > 1e-15]
    n = len(nonzero)
    if n == 0: return 1.0
    positives = sum(value > 0 for value in nonzero)
    k = min(positives, n - positives)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def bootstrap_ci(values: list[float], seed: int = 2026, draws: int = 10000) -> tuple[float, float]:
    if not values: return (float("nan"), float("nan"))
    rng = random.Random(seed); n = len(values); means = []
    for _ in range(draws): means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort(); return means[int(0.025 * draws)], means[min(draws - 1, int(0.975 * draws))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--reference", default="xai_gate")
    parser.add_argument("--metric", default="high_risk_explanation_coverage")
    parser.add_argument("--output", type=Path, default=Path("results/paired_effects.csv"))
    args = parser.parse_args()
    frame = pd.read_csv(args.runs)
    rows = []
    for (regime, variant), group in frame.groupby(["regime","variant"]):
        ref = group[group.policy == args.reference].set_index("seed")
        for policy in sorted(set(group.policy) - {args.reference}):
            other = group[group.policy == policy].set_index("seed")
            common = sorted(set(ref.index) & set(other.index)); diffs = [float(ref.loc[seed, args.metric]) - float(other.loc[seed, args.metric]) for seed in common]
            if not diffs: continue
            low, high = bootstrap_ci(diffs)
            rows.append({"regime":regime,"variant":variant,"reference":args.reference,"comparator":policy,"metric":args.metric,"seeds":len(diffs),"mean_difference":sum(diffs)/len(diffs),"bootstrap_ci_low":low,"bootstrap_ci_high":high,"sign_test_p":sign_test_p(diffs)})
    args.output.parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(args.output, index=False); print(pd.DataFrame(rows).to_string(index=False)); return 0


if __name__ == "__main__": raise SystemExit(main())

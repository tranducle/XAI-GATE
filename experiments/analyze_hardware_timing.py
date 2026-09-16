#!/usr/bin/env python3
"""Aggregate explanation-service timing measurements by resource condition and action."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "results" / "hardware_validation" / "measurements"
files = sorted(base.glob("*.csv"))
if not files:
    raise SystemExit(f"no timing files under {base}")
frame = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
summary = frame.groupby(["condition","action"])["latency_ms"].agg(
    observations="count",
    median_ms="median",
    mean_ms="mean",
    p95_ms=lambda values: values.quantile(0.95),
    max_ms="max",
).reset_index()
out = base.parent / "timing_summary.csv"
out.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(out, index=False)
print(summary.to_string(index=False))
print(f"output={out}")

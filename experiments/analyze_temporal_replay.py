#!/usr/bin/env python3
"""Summarize chronological versus shuffled temporal replay outcomes."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "results" / "temporal_replay" / "runs.csv"
frame = pd.read_csv(path)
metrics = ["packet_drop_rate","high_risk_explanation_coverage","mean_explanation_debt","exposure_use","exposure_budget_violation_rate"]
pivot = frame.pivot_table(index=["session_id","policy"], columns="condition", values=metrics)
print(pivot.to_string())

#!/usr/bin/env python3
"""Build the KDDCup99 no-training calibration anchor used as a legacy reference."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.datasets import fetch_kddcup99

from xai_surfacebench.calibration import write_score_stream, write_summary

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    bunch = fetch_kddcup99(subset="SA", shuffle=True, random_state=2026, percent10=True)
    labels = np.array([0 if value.decode(errors="ignore").strip(".") == "normal" else 1 for value in bunch.target], dtype=int)
    raw = pd.DataFrame(bunch.data)
    numeric = raw.apply(lambda column: pd.to_numeric(column, errors="coerce")).fillna(0.0)
    activity = np.log1p(numeric.abs().sum(axis=1).to_numpy(dtype=float)); activity = (activity - activity.min()) / max(activity.max() - activity.min(), 1e-12)
    scores = 0.15 + 0.70 * activity
    data = ROOT / "data" / "kddcup99"
    write_score_stream(data / "kddcup99_score_stream.csv", scores, labels)
    metrics = {"rows":int(len(labels)),"positive_rate":float(labels.mean()),"mean_score":float(scores.mean())}
    write_summary(data / "kddcup99_calibration_summary.json", "KDDCup99", metrics, notes="Legacy no-training traffic/activity proxy used only as a calibration anchor.")
    print(metrics); return 0


if __name__ == "__main__": raise SystemExit(main())

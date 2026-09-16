#!/usr/bin/env python3
"""Prepare one-second CICIoT2023 replay traces and a fixed score model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["flow_duration","Header_Length","Protocol Type","Duration","Rate","Srate","Drate","fin_flag_number","syn_flag_number","rst_flag_number"]


def label_vector(frame: pd.DataFrame) -> np.ndarray:
    for name in ["label","Label","binary_label"]:
        if name in frame.columns:
            values = frame[name]
            if np.issubdtype(values.dtype, np.number):
                return (values.to_numpy(dtype=float) >= 0.5).astype(int)
            return (~values.astype(str).str.lower().isin(["benign","normal","0","false"])).astype(int).to_numpy()
    for name in ["Attack_type","attack_type"]:
        if name in frame.columns:
            return (~frame[name].astype(str).str.lower().isin(["benign","normal"])).astype(int).to_numpy()
    raise ValueError("no supported label column")


def timestamp_series(frame: pd.DataFrame) -> pd.Series:
    for name in ["timestamp","Timestamp","flow_start","time","ts"]:
        if name in frame.columns:
            raw = frame[name]
            if np.issubdtype(raw.dtype, np.number):
                return pd.to_datetime(raw, unit="s", errors="coerce", utc=True)
            return pd.to_datetime(raw, errors="coerce", utc=True)
    raise ValueError("timestamp-preserving replay requires a timestamp column")


def score_bucket(score: float) -> str:
    if score >= 0.86: return "critical"
    if score >= 0.68: return "high"
    if score >= 0.42: return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "ciciot2023_temporal" / "raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "ciciot2023_temporal")
    args = parser.parse_args()
    files = sorted(args.raw_dir.glob("*.parquet"))
    if len(files) < 2:
        raise SystemExit("at least two parquet files are required")
    for path in files:
        sample = pd.read_parquet(path, columns=None)
        missing = [name for name in FEATURES if name not in sample.columns]
        if missing:
            raise ValueError(f"{path.name}: missing predictor columns {missing}")
    training_files = [path for path in files if "Benign" not in path.name][: max(1, min(12, len(files)-1))]
    replay_files = [path for path in files if path not in training_files]
    train = pd.concat([pd.read_parquet(path) for path in training_files], ignore_index=True)
    model = make_pipeline(StandardScaler(), SGDClassifier(loss="log_loss", class_weight="balanced", random_state=2026, max_iter=2000, tol=1e-4))
    model.fit(train[FEATURES].fillna(0.0), label_vector(train))
    model_dir = args.output_dir / "model"; model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "temporal_score_model.joblib")
    replay_dir = args.output_dir / "replay"; replay_dir.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in replay_files:
        frame = pd.read_parquet(path)
        scores = model.predict_proba(frame[FEATURES].fillna(0.0))[:, 1]
        times = timestamp_series(frame)
        tmp = pd.DataFrame({"timestamp": times, "score": scores}).dropna(subset=["timestamp"])
        tmp["second"] = tmp["timestamp"].dt.floor("s")
        tmp["bucket"] = [score_bucket(value) for value in tmp["score"]]
        grouped = tmp.groupby("second")
        rows = grouped.size().rename("packet_arrivals").to_frame()
        for bucket in ["low","medium","high","critical"]:
            rows[f"{bucket}_count"] = grouped["bucket"].apply(lambda x, b=bucket: int((x == b).sum()))
        full_index = pd.date_range(rows.index.min(), rows.index.max(), freq="1s", tz="UTC")
        rows = rows.reindex(full_index, fill_value=0).reset_index(names="second")
        out = replay_dir / (path.stem + "_slots.csv")
        rows.to_csv(out, index=False)
        sessions.append({"source_file": path.name, "trace_file": out.name, "slots": len(rows), "flows": len(frame)})
    manifest = {"features": FEATURES, "training_files": [p.name for p in training_files], "sessions": sessions}
    (args.output_dir / "preprocessing_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Measure explanation-service action latency on a fixed record set.

CPU and memory limits are applied by the host or container runtime. The `condition`
argument is descriptive provenance only and does not alter resource limits itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["flow_duration","Header_Length","Protocol Type","Duration","Rate","Srate","Drate","fin_flag_number","syn_flag_number","rst_flag_number"]


def _action(action: str, row: np.ndarray, model, background: np.ndarray) -> None:
    if action in {"none","delay"}:
        return
    if action == "offload":
        json.dumps(row.tolist(), separators=(",", ":")).encode("utf-8")
        return
    if action == "audit":
        hashlib.sha256(row.tobytes()).digest()
        return
    if action == "coarse":
        np.argsort(np.abs(row))[-3:]
        return
    if action == "redact":
        copy = row.copy(); copy[np.argsort(np.abs(copy))[-3:]] = 0.0
        return
    if action == "full_lime":
        from lime.lime_tabular import LimeTabularExplainer
        explainer = LimeTabularExplainer(background, feature_names=FEATURES, mode="classification", discretize_continuous=False, random_state=2026)
        explainer.explain_instance(row, model.predict_proba, num_features=len(FEATURES), num_samples=512)
        return
    if action == "full_kernelshap":
        import shap
        explainer = shap.KernelExplainer(model.predict_proba, background)
        explainer.shap_values(row.reshape(1, -1), nsamples=256, silent=True)
        return
    raise ValueError(f"unknown action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", required=True, choices=["physical_m2","arm64_2cpu_4gib","arm64_1cpu_2gib","arm64_0_5cpu_1gib"])
    parser.add_argument("--action", required=True, choices=["none","delay","offload","audit","coarse","redact","full_lime","full_kernelshap"])
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--samples", type=Path, default=ROOT / "data" / "hardware_validation" / "replay_samples.parquet")
    parser.add_argument("--background", type=Path, default=ROOT / "data" / "hardware_validation" / "calibration_background.parquet")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "ciciot2023_temporal" / "model" / "temporal_score_model.joblib")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "hardware_validation" / "measurements")
    args = parser.parse_args()
    samples = pd.read_parquet(args.samples)
    background = pd.read_parquet(args.background)[FEATURES].to_numpy(dtype=float)
    model = joblib.load(args.model)
    records = []
    for index, row in samples[FEATURES].iterrows():
        vector = row.to_numpy(dtype=float)
        start = time.perf_counter_ns()
        _action(args.action, vector, model, background)
        latency_ms = (time.perf_counter_ns() - start) / 1e6
        records.append({"condition":args.condition,"action":args.action,"repeat":args.repeat,"record_index":int(index),"latency_ms":latency_ms})
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.condition}__{args.action}__repeat{args.repeat}.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"rows={len(records)} output={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

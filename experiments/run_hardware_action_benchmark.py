#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.hardware_benchmark import (  # noqa: E402
    FEATURES,
    build_offload_payload,
    redact_vector,
)

ACTIONS = ("none", "coarse", "full_lime", "full_kernelshap", "offload", "audit", "redact", "delay")
SEED = 20260914


def percentile(values: list[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q, method="linear"))


def peak_rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return value / (1024.0 * 1024.0)
    return value / 1024.0


def read_cgroup() -> dict[str, Any]:
    root = Path("/sys/fs/cgroup")
    if not (root / "cgroup.controllers").exists():
        return {"available": False}
    result: dict[str, Any] = {"available": True}
    for name in ["cpu.max", "memory.max", "memory.peak", "memory.current", "cpu.stat", "memory.events"]:
        path = root / name
        if path.exists():
            result[name] = path.read_text().strip()
    return result


def top_indices(model: Any, row: np.ndarray, k: int = 6) -> list[int]:
    scaler = model.named_steps["scale"]
    clf = model.named_steps["classifier"]
    transformed = scaler.transform(row.reshape(1, -1))[0]
    coef = np.asarray(clf.coef_[0], dtype=float)
    contrib = np.abs(transformed * coef)
    return np.argsort(-contrib, kind="stable")[: min(k, len(contrib))].astype(int).tolist()


def initialize_action(action: str, model: Any, calibration: pd.DataFrame, manifest: dict[str, Any], repeat: int) -> Callable[[np.ndarray, float], Any]:
    np.random.seed(SEED + repeat)

    if action == "none":
        return lambda row, score: 0
    if action == "delay":
        return lambda row, score: 1
    if action == "coarse":
        return lambda row, score: top_indices(model, row, 6)
    if action == "redact":
        return lambda row, score: redact_vector(row.tolist(), top_indices(model, row, 3))
    if action == "offload":
        return lambda row, score: len(build_offload_payload(row.tolist(), score=score))
    if action == "audit":
        def audit(row: np.ndarray, score: float) -> str:
            payload = json.dumps(
                {
                    "score": round(float(score), 6),
                    "top_features": top_indices(model, row, 6),
                    "action": "audit",
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            return hashlib.sha256(payload).hexdigest()
        return audit

    background = calibration[list(FEATURES)].to_numpy(dtype=float)
    if action == "full_lime":
        from lime.lime_tabular import LimeTabularExplainer

        explainer = LimeTabularExplainer(
            training_data=background,
            feature_names=list(FEATURES),
            class_names=["benign", "attack"],
            mode="classification",
            discretize_continuous=False,
            random_state=SEED + repeat,
        )

        def lime_call(row: np.ndarray, score: float) -> Any:
            return explainer.explain_instance(
                row,
                model.predict_proba,
                num_features=len(FEATURES),
                num_samples=512,
            ).as_list(label=1)
        return lime_call

    if action == "full_kernelshap":
        import shap

        shap_ids = set(manifest["shap_background_record_ids"])
        shap_background = calibration[calibration["record_id"].isin(shap_ids)][list(FEATURES)].to_numpy(dtype=float)
        if len(shap_background) != 32:
            raise RuntimeError(f"expected 32 SHAP background records, found {len(shap_background)}")

        def positive_probability(values: np.ndarray) -> np.ndarray:
            return model.predict_proba(np.asarray(values, dtype=float))[:, 1]

        explainer = shap.KernelExplainer(positive_probability, shap_background)

        def shap_call(row: np.ndarray, score: float) -> Any:
            np.random.seed(SEED + repeat)
            return explainer.shap_values(row.reshape(1, -1), nsamples=256, silent=True)
        return shap_call

    raise ValueError(action)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--action", choices=ACTIONS, required=True)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    data = root / "data" / "hardware_validation"
    manifest = json.loads((data / "hardware_input_manifest.json").read_text())
    replay = pd.read_parquet(data / "hardware_replay_samples.parquet").head(args.limit).copy()
    calibration = pd.read_parquet(data / "hardware_calibration_background.parquet")
    model = joblib.load(root / manifest["artifacts"]["model"]["path"])

    if tuple(manifest["feature_order"]) != FEATURES:
        raise RuntimeError("feature order differs from the documented evaluation predictor contract")

    x = replay[list(FEATURES)].to_numpy(dtype=float)
    scores = model.predict_proba(x)[:, 1]
    fn = initialize_action(args.action, model, calibration, manifest, args.repeat)

    for i in range(min(args.warmup, len(replay))):
        fn(x[i], float(scores[i]))

    rows: list[dict[str, Any]] = []
    checksum = 0
    for i, (_, record) in enumerate(replay.iterrows()):
        row = x[i]
        score = float(scores[i])
        start_ns = time.perf_counter_ns()
        try:
            value = fn(row, score)
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            success = True
            error = ""
            checksum ^= hash(str(value)) & 0xFFFFFFFF
        except Exception as exc:  # preserve per-record failures for gate inspection
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            success = False
            error = f"{type(exc).__name__}: {exc}"[:500]
        rows.append(
            {
                "condition": args.condition,
                "action": args.action,
                "repeat": args.repeat,
                "record_id": record["record_id"],
                "source_file": record["source_file"],
                "latency_ms": elapsed_ms,
                "success": int(success),
                "error": error,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.condition}__{args.action}__r{args.repeat}"
    raw_path = args.out_dir / f"{stem}.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    success_latencies = [float(row["latency_ms"]) for row in rows if int(row["success"]) == 1]
    summary = {
        "condition": args.condition,
        "action": args.action,
        "repeat": args.repeat,
        "records": len(rows),
        "successful": len(success_latencies),
        "success_rate": len(success_latencies) / max(len(rows), 1),
        "median_ms": statistics.median(success_latencies) if success_latencies else None,
        "p95_ms": percentile(success_latencies, 0.95) if success_latencies else None,
        "p99_ms": percentile(success_latencies, 0.99) if success_latencies else None,
        "q25_ms": percentile(success_latencies, 0.25) if success_latencies else None,
        "q75_ms": percentile(success_latencies, 0.75) if success_latencies else None,
        "peak_rss_mb": peak_rss_mb(),
        "checksum": int(checksum),
        "machine": platform.machine(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "thread_env": {name: os.environ.get(name, "") for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]},
        "cgroup": read_cgroup(),
    }
    summary_path = args.out_dir / f"{stem}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if len(success_latencies) == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())

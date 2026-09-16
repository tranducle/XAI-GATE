#!/usr/bin/env python3
"""Prepare capture-disjoint CICIoT2023 risk scores and 1-second replay slots.

This is preprocessing for timestamp-preserving temporal replay study. It fits a lightweight CPU-only
score model on the selected calibration captures, never on the five replay
captures. It then scores and temporally bins the replay captures without running
any XAI-Gate policy.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from xai_surfacebench.temporal_replay import build_slot_table  # noqa: E402

RANDOM_STATE = 20260914
FEATURES = [
    "protocol",
    "src_port",
    "dst_port",
    "packets",
    "packets_rev",
    "bytes",
    "bytes_rev",
    "tcp_flags",
    "tcp_flags_rev",
    "duration",
]
EXCLUDED_PREDICTOR_FIELDS = [
    "ts_start",
    "ts_end",
    "source_file",
    "label_class",
    "source_dataset",
    "src_mac",
    "dst_mac",
    "src_ip",
    "dst_ip",
    "ppisizes",
    "ppitimes",
    "ppiflags",
    "ppidirs",
]
CALIBRATION_FILES = [
    "Benign_Final__BenignTraffic.parquet",
    "BrowserHijacking__BrowserHijacking.parquet",
    "CommandInjection__CommandInjection.parquet",
    "DDoS-UDP_Fragmentation__DDoS-UDP_Fragmentation9.parquet",
    "DNS_Spoofing__DNS_Spoofing.parquet",
    "DictionaryBruteForce__DictionaryBruteForce.parquet",
    "DoS-TCP_Flood__DoS-TCP_Flood10.parquet",
    "MITM-ArpSpoofing__MITM-ArpSpoofing1.parquet",
    "Mirai-greeth_flood__Mirai-greeth_flood24.parquet",
    "SqlInjection__SqlInjection.parquet",
    "Uploading_Attack__Uploading_Attack.parquet",
    "XSS__XSS.parquet",
]
REPLAY_FILES = [
    "Benign_Final__BenignTraffic3.parquet",
    "Recon-PingSweep__Recon-PingSweep.parquet",
    "Recon-PortScan__Recon-PortScan.parquet",
    "DDoS-SynonymousIP_Flood__DDoS-SynonymousIP_Flood13.parquet",
    "Backdoor_Malware__Backdoor_Malware.parquet",
]


def target_from_label(series: pd.Series) -> np.ndarray:
    return (series.astype(str) != "Benign_Final").astype(np.int8).to_numpy()


def sanitize_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[FEATURES].copy()
    for column in FEATURES:
        out[column] = pd.to_numeric(out[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if out[column].isna().any():
            median = float(out[column].median()) if out[column].notna().any() else 0.0
            out[column] = out[column].fillna(median)
    return out.astype(np.float64)


def score_to_bucket(score: float) -> str:
    if score >= 0.86:
        return "critical"
    if score >= 0.68:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def reference_scale(benign_path: Path) -> dict[str, float]:
    frame = pd.read_parquet(benign_path, columns=["ts_start"])
    ts = pd.to_numeric(frame["ts_start"], errors="coerce").dropna().to_numpy(dtype=float)
    if ts.size == 0:
        raise RuntimeError("Benign calibration capture has no valid ts_start values")
    slot = np.floor(ts - float(ts.min())).astype(np.int64)
    _, counts = np.unique(slot, return_counts=True)
    median_nonzero = float(np.median(counts))
    if median_nonzero <= 0:
        raise RuntimeError("Invalid benign median nonzero 1-second flow-start count")
    scale = 45.0 / median_nonzero
    return {
        "benign_median_nonzero_flow_starts_per_second": median_nonzero,
        "benchmark_reference_arrival_units_per_second": 45.0,
        "flow_to_service_unit_scale": scale,
    }


def temporal_stats(arrivals: np.ndarray, width: int) -> dict[str, float]:
    if width > 1:
        padding = (-len(arrivals)) % width
        if padding:
            arrivals = np.pad(arrivals, (0, padding), constant_values=0.0)
        arrivals = arrivals.reshape(-1, width).sum(axis=1)
    if arrivals.size == 0:
        return {"bins": 0, "mean": 0.0, "variance": 0.0, "fano": 0.0, "cv": 0.0, "p95": 0.0, "max": 0.0}
    mean = float(arrivals.mean())
    variance = float(arrivals.var())
    sd = math.sqrt(max(variance, 0.0))
    return {
        "bins": int(arrivals.size),
        "mean": mean,
        "variance": variance,
        "fano": variance / mean if mean > 0 else 0.0,
        "cv": sd / mean if mean > 0 else 0.0,
        "p95": float(np.quantile(arrivals, 0.95)),
        "max": float(arrivals.max()),
    }


def build_slots(frame: pd.DataFrame, scale: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    ordered = frame.sort_values("ts_start", kind="mergesort").reset_index(drop=True)
    start = float(ordered["ts_start"].min())
    reference_nonzero_median = 45.0 / float(scale)
    slots = build_slot_table(
        ordered[["ts_start", "score", "true_label"]],
        reference_nonzero_median=reference_nonzero_median,
        alert_threshold=0.50,
        reference_arrival_rate=45.0,
    )

    arrivals = slots["flow_starts"].to_numpy(dtype=float)
    stats = {
        "session_start_epoch": start,
        "slots": int(len(slots)),
        "total_flow_starts": int(slots["flow_starts"].sum()),
        "total_alerts": int(slots["alert_count"].sum()),
        "temporal_1s": temporal_stats(arrivals, 1),
        "temporal_10s": temporal_stats(arrivals, 10),
        "temporal_60s": temporal_stats(arrivals, 60),
    }
    return slots, stats


def main() -> int:
    root = ROOT
    data_root = root / "data" / "ciciot2023_temporal"
    calibration_dir = data_root / "calibration"
    replay_dir = data_root / "replay"
    scored_dir = data_root / "scored_replay"
    slot_dir = data_root / "slot_traces"
    model_dir = data_root / "model"
    for directory in [scored_dir, slot_dir, model_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    calibration_frames = []
    calibration_sources: set[str] = set()
    for filename in CALIBRATION_FILES:
        path = calibration_dir / filename
        frame = pd.read_parquet(path, columns=FEATURES + ["label_class", "source_file"])
        calibration_frames.append(frame)
        calibration_sources.update(str(x) for x in frame["source_file"].dropna().unique())
    train = pd.concat(calibration_frames, ignore_index=True)
    x_train = sanitize_features(train)
    y_train = target_from_label(train["label_class"])

    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    penalty="elasticnet",
                    alpha=1e-5,
                    l1_ratio=0.05,
                    class_weight="balanced",
                    max_iter=1000,
                    tol=1e-4,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    model_path = model_dir / "temporal_score_model.joblib"
    joblib.dump(model, model_path)

    scale_info = reference_scale(calibration_dir / "Benign_Final__BenignTraffic.parquet")
    scale = float(scale_info["flow_to_service_unit_scale"])

    replay_sources: set[str] = set()
    pooled_y: list[int] = []
    pooled_scores: list[float] = []
    sessions: list[dict[str, Any]] = []

    for filename in REPLAY_FILES:
        path = replay_dir / filename
        needed = FEATURES + ["ts_start", "ts_end", "source_file", "label_class"]
        frame = pd.read_parquet(path, columns=needed)
        replay_sources.update(str(x) for x in frame["source_file"].dropna().unique())
        x = sanitize_features(frame)
        scores = model.predict_proba(x)[:, 1]
        y = target_from_label(frame["label_class"])
        pooled_y.extend(int(v) for v in y)
        pooled_scores.extend(float(v) for v in scores)

        scored = frame[["ts_start", "ts_end", "source_file", "label_class"]].copy()
        scored["true_label"] = y.astype(np.int8)
        scored["score"] = scores.astype(float)
        scored["alert"] = scored["score"] >= 0.50
        scored["bucket"] = [score_to_bucket(float(v)) for v in scored["score"]]
        scored = scored.sort_values("ts_start", kind="mergesort").reset_index(drop=True)

        scored_path = scored_dir / filename
        scored.to_parquet(scored_path, index=False)
        slots, stats = build_slots(scored, scale)
        slot_path = slot_dir / filename.replace(".parquet", "_slots.csv")
        slots.to_csv(slot_path, index=False)

        stats.update(
            {
                "filename": filename,
                "source_file": str(scored["source_file"].iloc[0]),
                "label_class": str(scored["label_class"].iloc[0]),
                "rows": int(len(scored)),
                "score_min": float(scored["score"].min()),
                "score_max": float(scored["score"].max()),
                "score_mean": float(scored["score"].mean()),
                "score_std": float(scored["score"].std(ddof=0)),
                "alert_rate": float(scored["alert"].mean()),
                "scored_path": str(scored_path.relative_to(root)),
                "slot_path": str(slot_path.relative_to(root)),
            }
        )
        sessions.append(stats)
        print(
            f"{filename:78s} rows={len(scored):8d} slots={len(slots):7d} "
            f"score_mean={stats['score_mean']:.4f} alert_rate={stats['alert_rate']:.4f}"
        )

    pooled_y_arr = np.asarray(pooled_y, dtype=np.int8)
    pooled_scores_arr = np.asarray(pooled_scores, dtype=float)
    pooled_pred = (pooled_scores_arr >= 0.50).astype(np.int8)
    replay_metrics = {
        "rows": int(len(pooled_y_arr)),
        "positive_rate": float(pooled_y_arr.mean()),
        "roc_auc": float(roc_auc_score(pooled_y_arr, pooled_scores_arr)),
        "average_precision": float(average_precision_score(pooled_y_arr, pooled_scores_arr)),
        "brier_score": float(brier_score_loss(pooled_y_arr, pooled_scores_arr)),
        "f1_at_0_5": float(f1_score(pooled_y_arr, pooled_pred, zero_division=0)),
        "score_min": float(pooled_scores_arr.min()),
        "score_max": float(pooled_scores_arr.max()),
        "score_mean": float(pooled_scores_arr.mean()),
        "score_std": float(pooled_scores_arr.std()),
        "score_quantiles": {str(q): float(np.quantile(pooled_scores_arr, q)) for q in [0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99]},
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_state": RANDOM_STATE,
        "model_role": "held-out score calibration metadata only, not a detector contribution",
        "features": FEATURES,
        "excluded_predictor_fields": EXCLUDED_PREDICTOR_FIELDS,
        "calibration_files": CALIBRATION_FILES,
        "replay_files": REPLAY_FILES,
        "calibration_source_files": sorted(calibration_sources),
        "replay_source_files": sorted(replay_sources),
        "source_file_overlap": sorted(calibration_sources & replay_sources),
        "training_rows": int(len(train)),
        "training_class_counts": {"benign": int((y_train == 0).sum()), "attack": int((y_train == 1).sum())},
        "scale": scale_info,
        "replay_score_metrics": replay_metrics,
        "sessions": sessions,
        "model_path": str(model_path.relative_to(root)),
    }
    manifest_path = data_root / "temporal_preprocessing_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest={manifest_path}")
    print(f"source_overlap={len(calibration_sources & replay_sources)}")
    print(f"replay_auc={replay_metrics['roc_auc']:.6f}")
    print(f"replay_score_std={replay_metrics['score_std']:.6f}")
    print(f"flow_to_service_scale={scale:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

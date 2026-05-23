#!/usr/bin/env python3
"""Create a TON_IoT calibrated score-stream anchor for XAI-SurfaceBench.

TON_IoT is used here as a third public real-dataset anchor. The calibration
classifier is not a detector contribution; it only produces reproducible risk
scores and labels for explanation-surface stress testing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.request import Request, urlopen


DATA_URL = "https://huggingface.co/datasets/codymlewis/TON_IoT_network/resolve/main/train_test_network.csv"
SOURCE_DATASET_CARD = "https://huggingface.co/datasets/codymlewis/TON_IoT_network"
OFFICIAL_DATASET_DOI = "10.1109/ACCESS.2020.3022862"

HIGH_CARDINALITY_DROP = {
    "src_ip",
    "dst_ip",
    "dns_query",
    "ssl_subject",
    "ssl_issuer",
    "http_uri",
    "http_user_agent",
    "weird_addl",
}

BUCKETS = [
    ("low", 0.0, 0.42),
    ("medium", 0.42, 0.68),
    ("high", 0.68, 0.86),
    ("critical", 0.86, 1.01),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(path: Path, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    request = Request(DATA_URL, headers={"User-Agent": "xai-surfacebench-toniot/1.0"})
    with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent)) as tmp:
        tmp_path = Path(tmp.name)
        with urlopen(request, timeout=180) as response:
            shutil.copyfileobj(response, tmp)
    tmp_path.replace(path)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def bucket_name(score: float) -> str:
    for name, low, high in BUCKETS:
        if low <= score < high:
            return name
    return "critical"


def stable_hashes(frame: Any, columns: List[str]) -> List[str]:
    hashes: List[str] = []
    for row in frame[columns].itertuples(index=False, name=None):
        normalized = "\x1f".join("<NA>" if value != value else str(value) for value in row)
        hashes.append(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return hashes


def load_and_prepare_raw(path: Path) -> Any:
    import pandas as pd

    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.columns = [str(column).strip().lstrip("\ufeff") for column in frame.columns]
    if "label" not in frame.columns or "type" not in frame.columns:
        raise ValueError("TON_IoT CSV must contain 'label' and 'type' columns.")
    frame = frame.dropna(subset=["label"]).copy()
    frame["label"] = frame["label"].astype(int)
    frame["type"] = frame["type"].fillna("unknown").astype(str)
    return frame


def deduplicate_frame(frame: Any) -> tuple[Any, Dict[str, Any]]:
    feature_columns = [column for column in frame.columns if column not in {"label", "type"}]
    hashes = stable_hashes(frame, feature_columns)
    seen: set[str] = set()
    keep: List[bool] = []
    for row_hash in hashes:
        should_keep = row_hash not in seen
        keep.append(should_keep)
        seen.add(row_hash)
    out = frame.loc[keep].reset_index(drop=True)
    return out, {
        "deduplication_key": "all columns excluding label and type",
        "rows_before": int(len(frame)),
        "rows_after": int(len(out)),
        "duplicate_feature_rows_removed": int(len(frame) - len(out)),
        "unique_feature_hashes": int(len(seen)),
    }


def split_frame(frame: Any, seed: int) -> tuple[Any, Any, Dict[str, Any]]:
    from sklearn.model_selection import train_test_split

    stratify = frame["label"] if frame["label"].nunique() > 1 else None
    train_frame, test_frame = train_test_split(
        frame,
        test_size=0.30,
        random_state=seed,
        shuffle=True,
        stratify=stratify,
    )
    train_frame = train_frame.reset_index(drop=True)
    test_frame = test_frame.reset_index(drop=True)
    feature_columns = [column for column in frame.columns if column not in {"label", "type"}]
    overlap = len(set(stable_hashes(train_frame, feature_columns)) & set(stable_hashes(test_frame, feature_columns)))
    return train_frame, test_frame, {
        "split_method": "stratified random split after feature deduplication",
        "seed": seed,
        "train_rows": int(len(train_frame)),
        "test_rows": int(len(test_frame)),
        "train_positive_rate": float(train_frame["label"].mean()),
        "test_positive_rate": float(test_frame["label"].mean()),
        "train_test_feature_hash_overlap": int(overlap),
    }


def prepare_frame(frame: Any) -> tuple[Any, Any, Any, List[str], List[str]]:
    import numpy as np
    import pandas as pd

    labels = frame["label"].astype(int)
    attack_family = frame["type"].astype(str)
    drop_cols = [column for column in ["label", "type"] if column in frame.columns]
    drop_cols.extend(column for column in HIGH_CARDINALITY_DROP if column in frame.columns)
    features = frame.drop(columns=drop_cols).copy()

    categorical: List[str] = []
    numeric: List[str] = []
    for column in features.columns:
        if pd.api.types.is_numeric_dtype(features[column]):
            numeric.append(column)
            values = pd.to_numeric(features[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
            features[column] = values.fillna(values.median() if values.notna().any() else 0.0)
        else:
            categorical.append(column)
            features[column] = features[column].fillna("unknown").astype(str).replace({"-": "unknown", "": "unknown"})
    return features, labels, attack_family, numeric, categorical


def train_score_model(train_frame: Any, test_frame: Any, seed: int, max_iter: int) -> Dict[str, Any]:
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        brier_score_loss,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    x_train, y_train, _, numeric, categorical = prepare_frame(train_frame)
    x_test, y_test, attack_family, _, _ = prepare_frame(test_frame)
    transformers = []
    if numeric:
        transformers.append(("num", StandardScaler(), numeric))
    if categorical:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=True), categorical))
    if not transformers:
        raise ValueError("No usable TON_IoT feature columns found.")

    pipeline = Pipeline(
        [
            ("preprocess", ColumnTransformer(transformers=transformers)),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    penalty="elasticnet",
                    alpha=1e-5,
                    l1_ratio=0.05,
                    class_weight="balanced",
                    max_iter=max_iter,
                    tol=1e-4,
                    random_state=seed,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    scores = pipeline.predict_proba(x_test)[:, 1]
    predictions = (scores >= 0.5).astype(int)
    y_test_np = np.asarray(y_test, dtype=int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_test_np, scores)),
        "average_precision": float(average_precision_score(y_test_np, scores)),
        "brier_score": float(brier_score_loss(y_test_np, scores)),
        "accuracy_at_0_5": float(accuracy_score(y_test_np, predictions)),
        "precision_at_0_5": float(precision_score(y_test_np, predictions, zero_division=0)),
        "recall_at_0_5": float(recall_score(y_test_np, predictions, zero_division=0)),
        "f1_at_0_5": float(f1_score(y_test_np, predictions, zero_division=0)),
    }
    return {
        "scores": scores,
        "labels": y_test_np,
        "attack_family": list(attack_family.astype(str)),
        "metrics": metrics,
        "numeric_features": numeric,
        "categorical_features": categorical,
        "dropped_high_cardinality_features": sorted(HIGH_CARDINALITY_DROP),
    }


def make_cost_proxy(frame: Any, scores: Iterable[float]) -> List[float]:
    import numpy as np
    import pandas as pd

    score_values = list(scores)

    def robust01(column: str) -> Any:
        if column not in frame.columns:
            return pd.Series([0.0] * len(frame))
        values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        q05 = float(values.quantile(0.05))
        q95 = float(values.quantile(0.95))
        if not math.isfinite(q05) or not math.isfinite(q95) or q95 <= q05:
            return values * 0.0
        return ((values - q05) / (q95 - q05)).clip(0.0, 1.0)

    duration = robust01("duration")
    bytes_total = robust01("src_bytes") * 0.5 + robust01("dst_bytes") * 0.5
    pkts_total = robust01("src_pkts") * 0.5 + robust01("dst_pkts") * 0.5
    return [
        clamp(0.20 + 0.50 * float(score) + 0.10 * float(duration.iloc[idx]) + 0.10 * float(bytes_total.iloc[idx]) + 0.10 * float(pkts_total.iloc[idx]))
        for idx, score in enumerate(score_values)
    ]


def build_rows(test_frame: Any, model_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    costs = make_cost_proxy(test_frame, model_payload["scores"])
    rows = []
    for score, label, attack, cost in zip(
        model_payload["scores"],
        model_payload["labels"],
        model_payload["attack_family"],
        costs,
    ):
        rows.append(
            {
                "score": f"{float(score):.6f}",
                "true_label": int(label),
                "attack_family": str(attack),
                "cost_proxy": f"{float(cost):.6f}",
                "score_source": "toniot_sgd_logistic_calibration",
                "split": "test",
            }
        )
    return rows


def summarize_rows(
    rows: List[Dict[str, Any]],
    model_payload: Dict[str, Any],
    raw_file: Dict[str, Any],
    deduplication: Dict[str, Any],
    split: Dict[str, Any],
) -> Dict[str, Any]:
    labels = [int(row["true_label"]) for row in rows]
    scores = [float(row["score"]) for row in rows]
    by_bucket = {name: {"rows": 0.0, "positives": 0.0, "score_sum": 0.0} for name, _, _ in BUCKETS}
    attack_counts: Dict[str, int] = {}
    for row in rows:
        bucket = bucket_name(float(row["score"]))
        by_bucket[bucket]["rows"] += 1.0
        by_bucket[bucket]["positives"] += float(row["true_label"])
        by_bucket[bucket]["score_sum"] += float(row["score"])
        attack = str(row["attack_family"])
        attack_counts[attack] = attack_counts.get(attack, 0) + 1
    bucket_summary = {}
    for name, stats in by_bucket.items():
        count = max(stats["rows"], 1.0)
        bucket_summary[name] = {
            "rows": int(stats["rows"]),
            "share": stats["rows"] / max(len(rows), 1),
            "attack_rate": stats["positives"] / count,
            "mean_score": stats["score_sum"] / count,
        }
    return {
        "dataset": "TON_IoT Network",
        "source_dataset_card": SOURCE_DATASET_CARD,
        "download_url": DATA_URL,
        "citation_doi": OFFICIAL_DATASET_DOI,
        "raw_file": raw_file,
        "deduplication": deduplication,
        "split": split,
        "score_stream_rows": len(rows),
        "positive_rate": sum(labels) / max(len(labels), 1),
        "mean_score": sum(scores) / max(len(scores), 1),
        "score_generation": "SGD logistic classifier trained on a stratified train split after feature deduplication; test probabilities are calibration metadata only.",
        "model_metadata": {
            **model_payload["metrics"],
            "numeric_feature_count": len(model_payload["numeric_features"]),
            "categorical_features": model_payload["categorical_features"],
            "dropped_high_cardinality_features": model_payload["dropped_high_cardinality_features"],
        },
        "bucket_summary": bucket_summary,
        "attack_family_counts": dict(sorted(attack_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "not_claimed": [
            "The calibrated model is not a detector contribution.",
            "Detector accuracy is calibration metadata only.",
            "This third anchor strengthens score-stream realism but does not establish deployment readiness or operator effectiveness.",
        ],
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["score", "true_label", "attack_family", "cost_proxy", "score_source", "split"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_config(path: Path) -> None:
    config = {
        "name": "toniot_calibrated_anchor",
        "experiment_type": "standard",
        "slots": 5000,
        "seeds": list(range(1, 21)),
        "policies": [
            "never_explain",
            "always_explain",
            "threshold_explain",
            "rate_limited",
            "fifo_explanation",
            "static_coarse_full",
            "static_offload",
            "budget_only_bexgov",
            "xai_gate",
        ],
        "regimes": [
            "adversarial_explanation_flood",
            "transient_overload",
            "non_markovian",
            "rtt_uncertainty",
        ],
        "base": {
            "packet_arrival_rate": 45.0,
            "packet_service_rate": 52.0,
            "packet_buffer_capacity": 240.0,
            "alert_probability": 0.15,
            "local_explanation_budget": 18.0,
            "exposure_budget_total": 18000.0,
            "threshold": 0.72,
        },
        "calibration": {
            "score_stream_path": "../data/toniot/toniot_score_stream.csv",
            "training_summary_path": "../data/toniot/toniot_calibration_summary.json",
        },
    }
    write_json(path, config)


def markdown_table(rows: List[str]) -> str:
    return "\n".join(rows)


def write_report(root: Path, summary: Dict[str, Any], score_path: Path, config_path: Path) -> None:
    bucket_lines = ["| Bucket | Rows | Share | Attack rate | Mean score |", "|---|---:|---:|---:|---:|"]
    for name, stats in summary["bucket_summary"].items():
        bucket_lines.append(
            f"| {name} | {stats['rows']} | {stats['share']:.3f} | {stats['attack_rate']:.3f} | {stats['mean_score']:.3f} |"
        )
    attack_lines = ["| Attack family | Rows |", "|---|---:|"]
    for attack, count in list(summary["attack_family_counts"].items())[:12]:
        attack_lines.append(f"| {attack} | {count} |")
    model = summary["model_metadata"]
    split = summary["split"]
    dedup = summary["deduplication"]
    report = f"""# TON_IoT Calibration Anchor

This artifact adds a third public real-dataset anchor for XAI-SurfaceBench.
TON_IoT is used as an IoT/IIoT network-flow score-stream source. The calibration
classifier is not a detector contribution.

## Files

- Score stream: `{score_path.relative_to(root)}`
- Benchmark config: `{config_path.relative_to(root)}`
- Summary JSON: `data/toniot/toniot_calibration_summary.json`
- Raw CSV: `data/toniot/raw/train_test_network.csv`

## Source And Provenance

- Dataset card used for automation: {summary['source_dataset_card']}
- Dataset paper DOI: `{summary['citation_doi']}`
- Raw SHA-256: `{summary['raw_file']['sha256']}`
- Rows before/after feature deduplication: {dedup['rows_before']} / {dedup['rows_after']}
- Stratified train/test rows: {split['train_rows']} / {split['test_rows']}
- Train/test feature-hash overlap after deduplication and split: {split['train_test_feature_hash_overlap']}
- Test positive-label rate: {summary['positive_rate']:.3f}

## Calibration Model Metadata

- Model role: calibration metadata only
- Model family: linear SGD logistic classifier with balanced class weights
- ROC AUC: {model['roc_auc']:.3f}
- Average precision: {model['average_precision']:.3f}
- Brier score: {model['brier_score']:.3f}
- F1 at threshold 0.5: {model['f1_at_0_5']:.3f}
- Numeric features: {model['numeric_feature_count']}
- Categorical features: {', '.join(model['categorical_features']) or 'none'}
- Dropped high-cardinality fields: {', '.join(model['dropped_high_cardinality_features'])}

## Score Bucket Summary

{markdown_table(bucket_lines)}

## Attack Family Preview

{markdown_table(attack_lines)}

## Claim Boundary

The TON_IoT anchor strengthens public-data score-stream breadth beyond KDDCup99
and UNSW-NB15. It remains a calibration anchor and does not support claims about
new detector accuracy, hardware deployment readiness, or SME/operator benefit.
"""
    (root / "TONIOT_CALIBRATION_ANCHOR_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    raw_path = root / "data" / "toniot" / "raw" / "train_test_network.csv"
    download(raw_path, force=args.force_download)
    raw_frame = load_and_prepare_raw(raw_path)
    dedup_frame, deduplication = deduplicate_frame(raw_frame)
    train_frame, test_frame, split = split_frame(dedup_frame, args.seed)
    model_payload = train_score_model(train_frame, test_frame, args.seed, args.max_iter)
    rows = build_rows(test_frame, model_payload)
    raw_file = {
        "url": DATA_URL,
        "path": str(raw_path.relative_to(root)),
        "bytes": raw_path.stat().st_size,
        "sha256": sha256_file(raw_path),
    }
    summary = summarize_rows(rows, model_payload, raw_file, deduplication, split)

    score_path = root / "data" / "toniot" / "toniot_score_stream.csv"
    summary_path = root / "data" / "toniot" / "toniot_calibration_summary.json"
    config_path = root / "configs" / "toniot_calibrated_anchor.json"
    write_csv(score_path, rows)
    write_json(summary_path, summary)
    write_config(config_path)
    write_report(root, summary, score_path, config_path)
    print(f"raw_rows={len(raw_frame)}")
    print(f"dedup_rows={len(dedup_frame)}")
    print(f"score_rows={len(rows)}")
    print(f"score_stream={score_path}")
    print(f"summary={summary_path}")
    print(f"config={config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

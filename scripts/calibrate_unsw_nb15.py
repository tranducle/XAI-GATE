#!/usr/bin/env python3
"""Create a real-dataset calibrated anchor from UNSW-NB15.

The generated score stream is calibration metadata for XAI-SurfaceBench, not a
detector contribution. A transparent linear logistic model is trained only to
obtain reproducible alert-risk probabilities from the public UNSW-NB15 train/test
CSV splits; XAI-Gate is still evaluated as an explanation-service controller.
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
from typing import Any, Dict, Iterable, List, Tuple
from urllib.request import Request, urlopen


SOURCE_URL = "https://research.unsw.edu.au/projects/unsw-nb15-dataset"
MIRROR_DATASET_CARD = "https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15"
DATA_URLS = {
    "train": "https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/main/train.csv",
    "test": "https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/main/test.csv",
}
UNSW_PAPER_DOI = "10.1109/MilCIS.2015.7348942"

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


def download(url: str, path: Path, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    request = Request(url, headers={"User-Agent": "xai-surfacebench-calibration/1.0"})
    with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent)) as tmp:
        tmp_path = Path(tmp.name)
        with urlopen(request, timeout=120) as response:
            shutil.copyfileobj(response, tmp)
    tmp_path.replace(path)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def bucket_name(score: float) -> str:
    for name, low, high in BUCKETS:
        if low <= score < high:
            return name
    return "critical"


def prepare_frame(frame: Any) -> Tuple[Any, Any, Any, List[str], List[str]]:
    import numpy as np
    import pandas as pd

    if "label" not in frame.columns:
        raise ValueError("UNSW-NB15 frame does not contain a binary 'label' column.")

    labels = frame["label"].astype(int)
    attack_family = frame["attack_cat"].astype(str) if "attack_cat" in frame.columns else labels.map(str)
    drop_cols = [column for column in ["id", "label", "attack_cat"] if column in frame.columns]
    features = frame.drop(columns=drop_cols).copy()

    categorical: List[str] = []
    numeric: List[str] = []
    for column in features.columns:
        if pd.api.types.is_numeric_dtype(features[column]):
            numeric.append(column)
            values = pd.to_numeric(features[column], errors="coerce")
            values = values.replace([np.inf, -np.inf], np.nan)
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
        raise ValueError("No usable UNSW-NB15 feature columns found.")

    preprocessor = ColumnTransformer(transformers=transformers)
    classifier = SGDClassifier(
        loss="log_loss",
        penalty="elasticnet",
        alpha=1e-5,
        l1_ratio=0.05,
        class_weight="balanced",
        max_iter=max_iter,
        tol=1e-4,
        random_state=seed,
    )
    pipeline = Pipeline([("preprocess", preprocessor), ("classifier", classifier)])
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

    duration = robust01("dur")
    rate = robust01("rate")
    bytes_total = None
    if "sbytes" in frame.columns and "dbytes" in frame.columns:
        bytes_total = robust01("sbytes") * 0.5 + robust01("dbytes") * 0.5
    else:
        bytes_total = robust01("sbytes") if "sbytes" in frame.columns else robust01("dbytes")

    proxies = []
    for idx, score in enumerate(score_values):
        value = 0.20 + 0.50 * float(score) + 0.15 * float(duration.iloc[idx]) + 0.10 * float(bytes_total.iloc[idx]) + 0.05 * float(rate.iloc[idx])
        proxies.append(clamp(value))
    return proxies


def summarize_rows(rows: List[Dict[str, Any]], model_payload: Dict[str, Any], train_rows: int, test_rows: int, raw_files: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    labels = [int(row["true_label"]) for row in rows]
    scores = [float(row["score"]) for row in rows]
    by_bucket: Dict[str, Dict[str, float]] = {
        name: {"rows": 0.0, "positives": 0.0, "score_sum": 0.0} for name, _, _ in BUCKETS
    }
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
        "dataset": "UNSW-NB15",
        "official_source": SOURCE_URL,
        "download_mirror": MIRROR_DATASET_CARD,
        "citation_doi": UNSW_PAPER_DOI,
        "raw_files": raw_files,
        "train_rows": train_rows,
        "test_rows": test_rows,
        "score_stream_rows": len(rows),
        "positive_rate": sum(labels) / max(len(labels), 1),
        "mean_score": sum(scores) / max(len(scores), 1),
        "score_generation": "SGD logistic classifier trained on public UNSW-NB15 train split; predictions on held-out public test split are used only as calibration metadata.",
        "model_metadata": {
            **model_payload["metrics"],
            "numeric_feature_count": len(model_payload["numeric_features"]),
            "categorical_features": model_payload["categorical_features"],
        },
        "bucket_summary": bucket_summary,
        "attack_family_counts": dict(sorted(attack_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "not_claimed": [
            "The calibrated model is not a detector contribution.",
            "Detector accuracy is reported only to document score-stream quality.",
            "XAI-Gate is evaluated as an explanation-service controller, not as an intrusion detector.",
            "This single real dataset does not establish deployment readiness or operator effectiveness.",
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
        "name": "unsw_nb15_calibrated_anchor",
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
            "score_stream_path": "../data/unsw_nb15/unsw_nb15_score_stream.csv",
            "training_summary_path": "../data/unsw_nb15/unsw_nb15_calibration_summary.json",
        },
    }
    write_json(path, config)


def markdown_table(rows: List[str]) -> str:
    return "\n".join(rows)


def write_reports(root: Path, summary: Dict[str, Any], score_path: Path, config_path: Path) -> None:
    bucket_lines = ["| Bucket | Rows | Share | Attack rate | Mean score |", "|---|---:|---:|---:|---:|"]
    for name, stats in summary["bucket_summary"].items():
        bucket_lines.append(
            f"| {name} | {stats['rows']} | {stats['share']:.3f} | {stats['attack_rate']:.3f} | {stats['mean_score']:.3f} |"
        )
    attack_lines = ["| Attack family | Rows |", "|---|---:|"]
    for attack, count in list(summary["attack_family_counts"].items())[:12]:
        attack_lines.append(f"| {attack} | {count} |")

    model = summary["model_metadata"]
    report = f"""# UNSW-NB15 Real-Dataset Calibration Anchor

This artifact adds a modern public real-dataset anchor for XAI-SurfaceBench.
UNSW-NB15 is used because it is a widely cited intrusion-detection dataset with
public train/test flow records. The downloaded CSV files come from the Hugging Face
mirror documented as UNSW-NB15 train/test CSVs, while the original dataset source
and citation remain the UNSW project page and the MilCIS dataset paper.

## Files

- Score stream: `{score_path.relative_to(root)}`
- Benchmark config: `{config_path.relative_to(root)}`
- Summary JSON: `data/unsw_nb15/unsw_nb15_calibration_summary.json`
- Raw train/test CSVs: `data/unsw_nb15/raw/`

## Source And Provenance

- Official dataset page: {summary['official_source']}
- Download mirror used for automation: {summary['download_mirror']}
- Dataset paper DOI: `{summary['citation_doi']}`
- Train rows: {summary['train_rows']}
- Test rows / score stream rows: {summary['score_stream_rows']}
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

## Score Bucket Summary

{markdown_table(bucket_lines)}

## Attack Family Preview

{markdown_table(attack_lines)}

## Claim Boundary

This run addresses the evaluation risk that XAI-SurfaceBench had only synthetic or
legacy calibration. It does not claim new detector accuracy, hardware timing,
operator validation, or deployment readiness. Detector metrics are calibration
metadata for the score stream; the paper's contribution remains explanation-surface
governance under finite service capacity and exposure constraints.
"""
    (root / "UNSW_NB15_CALIBRATION_ANCHOR_REPORT.md").write_text(report, encoding="utf-8")


def write_dataset_workflow_docs(root: Path, summary: Dict[str, Any]) -> None:
    docs_dir = root / "docs" / "generated"
    docs_dir.mkdir(parents=True, exist_ok=True)
    selected = f"""# Selected Dataset: UNSW-NB15

UNSW-NB15 is used as a public calibrated score-stream anchor for XAI-SurfaceBench.
It is not used to introduce a new intrusion detector.

## Provenance

- Official project page: {summary['official_source']}
- Download mirror used by script: {summary['download_mirror']}
- Dataset paper DOI: `{summary['citation_doi']}`
- Train rows used: {summary['train_rows']}
- Held-out score-stream rows: {summary['score_stream_rows']}
- Raw file hashes are stored in `data/unsw_nb15/unsw_nb15_calibration_summary.json`.

## Boundary

The calibration model supplies score-stream metadata only; detector novelty is not claimed.
"""
    (docs_dir / "unsw_nb15_calibration.md").write_text(selected, encoding="utf-8")

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
                "score_source": "unsw_nb15_sgd_logistic_calibration",
                "split": "test",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    import pandas as pd

    root = args.root.resolve()
    raw_dir = root / "data" / "unsw_nb15" / "raw"
    train_path = raw_dir / "train.csv"
    test_path = raw_dir / "test.csv"
    download(DATA_URLS["train"], train_path, force=args.force_download)
    download(DATA_URLS["test"], test_path, force=args.force_download)

    train_frame = pd.read_csv(train_path)
    test_frame = pd.read_csv(test_path)
    model_payload = train_score_model(train_frame, test_frame, args.seed, args.max_iter)
    rows = build_rows(test_frame, model_payload)

    raw_files = {
        "train": {
            "url": DATA_URLS["train"],
            "path": str(train_path.relative_to(root)),
            "bytes": train_path.stat().st_size,
            "sha256": sha256_file(train_path),
        },
        "test": {
            "url": DATA_URLS["test"],
            "path": str(test_path.relative_to(root)),
            "bytes": test_path.stat().st_size,
            "sha256": sha256_file(test_path),
        },
    }
    summary = summarize_rows(rows, model_payload, len(train_frame), len(test_frame), raw_files)

    score_path = root / "data" / "unsw_nb15" / "unsw_nb15_score_stream.csv"
    summary_path = root / "data" / "unsw_nb15" / "unsw_nb15_calibration_summary.json"
    config_path = root / "configs" / "unsw_nb15_anchor.json"
    write_csv(score_path, rows)
    write_json(summary_path, summary)
    write_config(config_path)
    write_reports(root, summary, score_path, config_path)
    write_dataset_workflow_docs(root, summary)

    print(f"train_rows={len(train_frame)}")
    print(f"test_rows={len(test_frame)}")
    print(f"score_stream={score_path}")
    print(f"summary={summary_path}")
    print(f"config={config_path}")
    print(f"report={root / 'UNSW_NB15_CALIBRATION_ANCHOR_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

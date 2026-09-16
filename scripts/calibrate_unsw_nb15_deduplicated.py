#!/usr/bin/env python3
"""Create a de-duplicated UNSW-NB15 calibration anchor for XAI-SurfaceBench.

This variant keeps the original UNSW-NB15 anchor intact and writes a separate
score stream/config after removing feature-duplicate rows and train-test feature
overlap. The generated model remains calibration infrastructure only; no IDS
detector novelty is claimed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List
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
    request = Request(url, headers={"User-Agent": "xai-surfacebench-unsw-dedup/1.0"})
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


def stable_hashes(frame: Any, columns: List[str]) -> List[str]:
    """Return stable row hashes for selected columns without pandas hash salt."""
    hashes: List[str] = []
    for row in frame[columns].itertuples(index=False, name=None):
        normalized = "\x1f".join("<NA>" if value != value else str(value) for value in row)
        hashes.append(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return hashes


def prepare_frame(frame: Any) -> tuple[Any, Any, Any, List[str], List[str]]:
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
    return {
        "scores": scores,
        "labels": y_test_np,
        "attack_family": list(attack_family.astype(str)),
        "metrics": {
            "roc_auc": float(roc_auc_score(y_test_np, scores)),
            "average_precision": float(average_precision_score(y_test_np, scores)),
            "brier_score": float(brier_score_loss(y_test_np, scores)),
            "accuracy_at_0_5": float(accuracy_score(y_test_np, predictions)),
            "precision_at_0_5": float(precision_score(y_test_np, predictions, zero_division=0)),
            "recall_at_0_5": float(recall_score(y_test_np, predictions, zero_division=0)),
            "f1_at_0_5": float(f1_score(y_test_np, predictions, zero_division=0)),
        },
        "numeric_features": numeric,
        "categorical_features": categorical,
    }


def deduplicate_train_test(train_frame: Any, test_frame: Any) -> tuple[Any, Any, Dict[str, Any]]:
    feature_columns = [column for column in train_frame.columns if column not in {"id", "label", "attack_cat"}]
    no_id_columns = [column for column in train_frame.columns if column != "id"]

    train_feature_hash = stable_hashes(train_frame, feature_columns)
    test_feature_hash = stable_hashes(test_frame, feature_columns)
    train_exact_hash = stable_hashes(train_frame, no_id_columns)
    test_exact_hash = stable_hashes(test_frame, no_id_columns)

    train_feature_seen: set[str] = set()
    train_keep: List[bool] = []
    for row_hash in train_feature_hash:
        keep = row_hash not in train_feature_seen
        train_keep.append(keep)
        train_feature_seen.add(row_hash)

    test_feature_seen: set[str] = set()
    test_keep_internal: List[bool] = []
    for row_hash in test_feature_hash:
        keep = row_hash not in test_feature_seen
        test_keep_internal.append(keep)
        test_feature_seen.add(row_hash)

    dedup_train_hashes = {row_hash for row_hash, keep in zip(train_feature_hash, train_keep) if keep}
    test_keep_no_overlap = [keep and row_hash not in dedup_train_hashes for keep, row_hash in zip(test_keep_internal, test_feature_hash)]

    train_out = train_frame.loc[train_keep].reset_index(drop=True)
    test_out = test_frame.loc[test_keep_no_overlap].reset_index(drop=True)

    audit = {
        "deduplication_key": "all feature columns excluding id, label, and attack_cat",
        "exact_overlap_key": "all columns excluding id",
        "train_rows_before": int(len(train_frame)),
        "test_rows_before": int(len(test_frame)),
        "train_rows_after": int(len(train_out)),
        "test_rows_after": int(len(test_out)),
        "train_feature_duplicate_rows_removed": int(len(train_frame) - sum(train_keep)),
        "test_feature_duplicate_rows_removed": int(len(test_frame) - sum(test_keep_internal)),
        "test_rows_removed_due_train_feature_overlap_after_internal_dedup": int(sum(test_keep_internal) - sum(test_keep_no_overlap)),
        "feature_hash_train_test_overlap_before": int(len(set(train_feature_hash) & set(test_feature_hash))),
        "feature_hash_train_test_overlap_after": int(
            len(
                {row_hash for row_hash, keep in zip(stable_hashes(train_out, feature_columns), [True] * len(train_out)) if keep}
                & set(stable_hashes(test_out, feature_columns))
            )
        ),
        "exact_hash_train_test_overlap_before": int(len(set(train_exact_hash) & set(test_exact_hash))),
        "exact_hash_train_test_overlap_after": int(
            len(set(stable_hashes(train_out, no_id_columns)) & set(stable_hashes(test_out, no_id_columns)))
        ),
        "policy": [
            "Keep first training row per feature hash.",
            "Keep first test row per feature hash.",
            "Remove any remaining test row whose feature hash appears in the de-duplicated training split.",
        ],
    }
    return train_out, test_out, audit


def make_cost_proxy(frame: Any, scores: Iterable[float]) -> List[float]:
    import math
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
    if "sbytes" in frame.columns and "dbytes" in frame.columns:
        bytes_total = robust01("sbytes") * 0.5 + robust01("dbytes") * 0.5
    else:
        bytes_total = robust01("sbytes") if "sbytes" in frame.columns else robust01("dbytes")

    return [
        clamp(0.20 + 0.50 * float(score) + 0.15 * float(duration.iloc[idx]) + 0.10 * float(bytes_total.iloc[idx]) + 0.05 * float(rate.iloc[idx]))
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
                "score_source": "unsw_nb15_deduplicated_sgd_logistic_calibration",
                "split": "test_deduplicated",
            }
        )
    return rows


def summarize_rows(
    rows: List[Dict[str, Any]],
    model_payload: Dict[str, Any],
    train_rows: int,
    test_rows: int,
    raw_files: Dict[str, Dict[str, Any]],
    deduplication: Dict[str, Any],
) -> Dict[str, Any]:
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
        "variant": "deduplicated_feature_overlap_removed",
        "official_source": SOURCE_URL,
        "download_mirror": MIRROR_DATASET_CARD,
        "citation_doi": UNSW_PAPER_DOI,
        "raw_files": raw_files,
        "train_rows": train_rows,
        "test_rows": test_rows,
        "score_stream_rows": len(rows),
        "positive_rate": sum(labels) / max(len(labels), 1),
        "mean_score": sum(scores) / max(len(scores), 1),
        "score_generation": "SGD logistic classifier trained on de-duplicated public UNSW-NB15 train rows; predictions on de-duplicated, train-overlap-removed public test rows are used only as calibration metadata.",
        "deduplication": deduplication,
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
            "This de-duplicated single-dataset anchor does not establish deployment readiness or operator effectiveness.",
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
        "name": "unsw_nb15_deduplicated_anchor",
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
            "score_stream_path": "../data/unsw_nb15_dedup/unsw_nb15_dedup_score_stream.csv",
            "training_summary_path": "../data/unsw_nb15_dedup/unsw_nb15_dedup_calibration_summary.json",
        },
    }
    write_json(path, config)


def markdown_table(rows: List[str]) -> str:
    return "\n".join(rows)


def write_report(root: Path, summary: Dict[str, Any], score_path: Path, config_path: Path) -> None:
    dedup = summary["deduplication"]
    bucket_lines = ["| Bucket | Rows | Share | Attack rate | Mean score |", "|---|---:|---:|---:|---:|"]
    for name, stats in summary["bucket_summary"].items():
        bucket_lines.append(
            f"| {name} | {stats['rows']} | {stats['share']:.3f} | {stats['attack_rate']:.3f} | {stats['mean_score']:.3f} |"
        )
    attack_lines = ["| Attack family | Rows |", "|---|---:|"]
    for attack, count in list(summary["attack_family_counts"].items())[:12]:
        attack_lines.append(f"| {attack} | {count} |")

    model = summary["model_metadata"]
    report = f"""# UNSW-NB15 De-duplicated Calibration Anchor

This artifact reruns the modern UNSW-NB15 calibrated anchor after removing
feature-duplicate rows and train-test feature overlap. It is a provenance and
robustness check for XAI-SurfaceBench, not a new detector contribution.

## Files

- Score stream: `{score_path.relative_to(root)}`
- Benchmark config: `{config_path.relative_to(root)}`
- Summary JSON: `data/unsw_nb15_dedup/unsw_nb15_dedup_calibration_summary.json`
- Raw train/test CSVs: `data/unsw_nb15/raw/`

## Deduplication Audit

- Train rows before/after: {dedup['train_rows_before']} / {dedup['train_rows_after']}
- Test rows before/after: {dedup['test_rows_before']} / {dedup['test_rows_after']}
- Train feature-duplicate rows removed: {dedup['train_feature_duplicate_rows_removed']}
- Test feature-duplicate rows removed: {dedup['test_feature_duplicate_rows_removed']}
- Remaining test rows removed due to train feature overlap: {dedup['test_rows_removed_due_train_feature_overlap_after_internal_dedup']}
- Feature train-test overlap before/after: {dedup['feature_hash_train_test_overlap_before']} / {dedup['feature_hash_train_test_overlap_after']}
- Exact train-test overlap before/after: {dedup['exact_hash_train_test_overlap_before']} / {dedup['exact_hash_train_test_overlap_after']}

## Source And Provenance

- Official dataset page: {summary['official_source']}
- Download mirror used for automation: {summary['download_mirror']}
- Dataset paper DOI: `{summary['citation_doi']}`
- De-duplicated train rows used: {summary['train_rows']}
- De-duplicated test / score-stream rows: {summary['score_stream_rows']}
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

The de-duplicated UNSW run addresses the evaluation concern that train-test
duplicate/overlap artifacts may inflate the calibration anchor. It does not
claim detector novelty, hardware timing, operator validation, or deployment
readiness.
"""
    (root / "UNSW_NB15_DEDUP_CALIBRATION_ANCHOR_REPORT.md").write_text(report, encoding="utf-8")


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
    train_dedup, test_dedup, deduplication = deduplicate_train_test(train_frame, test_frame)

    model_payload = train_score_model(train_dedup, test_dedup, args.seed, args.max_iter)
    rows = build_rows(test_dedup, model_payload)

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
    summary = summarize_rows(rows, model_payload, len(train_dedup), len(test_dedup), raw_files, deduplication)

    out_dir = root / "data" / "unsw_nb15_dedup"
    score_path = out_dir / "unsw_nb15_dedup_score_stream.csv"
    summary_path = out_dir / "unsw_nb15_dedup_calibration_summary.json"
    audit_path = out_dir / "unsw_nb15_dedup_audit.json"
    config_path = root / "configs" / "unsw_nb15_deduplicated_anchor.json"
    write_csv(score_path, rows)
    write_json(summary_path, summary)
    write_json(audit_path, deduplication)
    write_config(config_path)
    write_report(root, summary, score_path, config_path)

    print(f"train_rows_before={len(train_frame)}")
    print(f"test_rows_before={len(test_frame)}")
    print(f"train_rows_after={len(train_dedup)}")
    print(f"test_rows_after={len(test_dedup)}")
    print(f"score_stream={score_path}")
    print(f"summary={summary_path}")
    print(f"audit={audit_path}")
    print(f"config={config_path}")
    print(f"report={root / 'UNSW_NB15_DEDUP_CALIBRATION_ANCHOR_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

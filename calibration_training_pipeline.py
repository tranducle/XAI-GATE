#!/usr/bin/env python3
"""Optional detector calibration pipeline for XAI-Gate.

This script trains standard detectors only to instantiate alert-score streams and
confusion matrices. It is not intended to support a SOTA detector claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def require_dependencies():
    try:
        import pandas as pd  # type: ignore
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier  # type: ignore
        from sklearn.impute import SimpleImputer  # type: ignore
        from sklearn.linear_model import LogisticRegression  # type: ignore
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score  # type: ignore
        from sklearn.model_selection import train_test_split  # type: ignore
        from sklearn.pipeline import Pipeline  # type: ignore
        from sklearn.preprocessing import StandardScaler  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Missing optional calibration dependencies. Install pandas and scikit-learn "
            "before running calibration training."
        ) from exc
    return {
        "pd": pd,
        "GradientBoostingClassifier": GradientBoostingClassifier,
        "RandomForestClassifier": RandomForestClassifier,
        "SimpleImputer": SimpleImputer,
        "LogisticRegression": LogisticRegression,
        "accuracy_score": accuracy_score,
        "confusion_matrix": confusion_matrix,
        "f1_score": f1_score,
        "precision_score": precision_score,
        "recall_score": recall_score,
        "train_test_split": train_test_split,
        "Pipeline": Pipeline,
        "StandardScaler": StandardScaler,
    }


def load_dataset(path: Path, label_column: str, deps):
    pd = deps["pd"]
    df = pd.read_csv(path)
    if label_column not in df.columns:
        raise SystemExit(f"Label column '{label_column}' not found in {path}")

    y_raw = df[label_column]
    x = df.drop(columns=[label_column])
    x = x.select_dtypes(include=["number", "bool"]).copy()
    if x.empty:
        raise SystemExit("No numeric feature columns found after dropping label column.")

    # Binary mapping is intentionally conservative: the most frequent label is normal/negative.
    counts = y_raw.value_counts()
    normal_label = counts.index[0]
    y = (y_raw != normal_label).astype(int)
    return x, y, str(normal_label)


def build_models(deps) -> Dict[str, object]:
    Pipeline = deps["Pipeline"]
    SimpleImputer = deps["SimpleImputer"]
    StandardScaler = deps["StandardScaler"]
    LogisticRegression = deps["LogisticRegression"]
    RandomForestClassifier = deps["RandomForestClassifier"]
    GradientBoostingClassifier = deps["GradientBoostingClassifier"]

    return {
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, n_jobs=None)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestClassifier(n_estimators=120, random_state=7, n_jobs=-1)),
            ]
        ),
        "gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingClassifier(random_state=7)),
            ]
        ),
    }


def score_model(model, x_test):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x_test)[:, 1]
    decision = model.decision_function(x_test)
    lo, hi = decision.min(), decision.max()
    if hi == lo:
        return decision * 0.0
    return (decision - lo) / (hi - lo)


def run_training(csv_path: Path, label_column: str, out_dir: Path) -> None:
    deps = require_dependencies()
    train_test_split = deps["train_test_split"]
    accuracy_score = deps["accuracy_score"]
    precision_score = deps["precision_score"]
    recall_score = deps["recall_score"]
    f1_score = deps["f1_score"]
    confusion_matrix = deps["confusion_matrix"]
    pd = deps["pd"]

    x, y, normal_label = load_dataset(csv_path, label_column, deps)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.30, random_state=7, stratify=y if y.nunique() == 2 else None
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    summary: List[Dict[str, object]] = []
    score_frames = []

    for name, model in build_models(deps).items():
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        scores = score_model(model, x_test)
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
        metrics = {
            "model": name,
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "confusion_matrix_labels": ["normal_or_majority", "attack_or_nonmajority"],
            "confusion_matrix": cm,
        }
        summary.append(metrics)
        frame = pd.DataFrame(
            {
                "model": name,
                "score": scores,
                "true_label": y_test.to_numpy(),
                "predicted_label": y_pred,
            }
        )
        score_frames.append(frame)

    (out_dir / "calibration_training_summary.json").write_text(json.dumps(summary, indent=2))
    pd.concat(score_frames, ignore_index=True).to_csv(out_dir / "calibrated_score_stream.csv", index=False)

    readme = [
        "# Calibration Training Output",
        "",
        f"Dataset: `{csv_path}`",
        f"Label column: `{label_column}`",
        f"Majority label treated as normal/negative: `{normal_label}`",
        "",
        "These outputs calibrate XAI-Gate simulations. They are not SOTA detector claims.",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(readme))
    print(f"Wrote calibration outputs to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train standard detectors for XAI-Gate calibration only.")
    parser.add_argument("--csv", type=Path, required=True, help="Input public IDS dataset CSV.")
    parser.add_argument("--label-column", required=True, help="Dataset label column.")
    parser.add_argument("--output-dir", type=Path, default=Path("calibration_outputs"))
    args = parser.parse_args()
    run_training(args.csv, args.label_column, args.output_dir)


if __name__ == "__main__":
    main()


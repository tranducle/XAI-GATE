"""Shared public-dataset calibration helpers for XAI-SurfaceBench."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def feature_hashes(frame: pd.DataFrame, feature_columns: Sequence[str]) -> pd.Series:
    return frame[list(feature_columns)].astype(str).agg("\x1f".join, axis=1).map(lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())


def fit_score_model(train: pd.DataFrame, test: pd.DataFrame, *, label_column: str, excluded_columns: Iterable[str] = (), seed: int = 2026) -> tuple[np.ndarray, dict]:
    excluded = set(excluded_columns) | {label_column}
    feature_columns = [column for column in train.columns if column not in excluded and column in test.columns]
    if not feature_columns:
        raise ValueError("no shared feature columns")
    numeric = [column for column in feature_columns if pd.api.types.is_numeric_dtype(train[column])]
    categorical = [column for column in feature_columns if column not in numeric]
    transformers = []
    if numeric: transformers.append(("num", StandardScaler(), numeric))
    if categorical: transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), categorical))
    model = Pipeline([
        ("preprocess", ColumnTransformer(transformers)),
        ("classifier", SGDClassifier(loss="log_loss", class_weight="balanced", random_state=seed, max_iter=2000, tol=1e-4)),
    ])
    x_train = train[feature_columns].copy(); x_test = test[feature_columns].copy()
    for column in numeric:
        x_train[column] = pd.to_numeric(x_train[column], errors="coerce").replace([np.inf,-np.inf], np.nan).fillna(0.0)
        x_test[column] = pd.to_numeric(x_test[column], errors="coerce").replace([np.inf,-np.inf], np.nan).fillna(0.0)
    for column in categorical:
        x_train[column] = x_train[column].fillna("unknown").astype(str)
        x_test[column] = x_test[column].fillna("unknown").astype(str)
    y_train = train[label_column].astype(int).to_numpy(); y_test = test[label_column].astype(int).to_numpy()
    model.fit(x_train, y_train); scores = model.predict_proba(x_test)[:,1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, scores)),
        "average_precision": float(average_precision_score(y_test, scores)),
        "brier_score": float(brier_score_loss(y_test, scores)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "numeric_features": numeric,
        "categorical_features": categorical,
        "feature_columns": feature_columns,
    }
    return scores, metrics


def write_score_stream(path: Path, scores: Sequence[float], labels: Sequence[int], attack_family: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame({"score": np.asarray(scores, dtype=float), "true_label": np.asarray(labels, dtype=int)})
    if attack_family is not None: frame["attack_family"] = list(map(str, attack_family))
    frame["cost_proxy"] = 0.2 + 0.8 * frame["score"]
    frame.to_csv(path, index=False)


def write_summary(path: Path, dataset: str, metrics: dict, *, notes: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dataset":dataset,"metrics":metrics,"role":"score-stream calibration metadata for explanation-service evaluation","notes":notes}, indent=2) + "\n")

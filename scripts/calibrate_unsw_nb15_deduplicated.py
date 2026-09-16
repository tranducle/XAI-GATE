#!/usr/bin/env python3
"""Build a de-duplicated UNSW-NB15 score-stream anchor with zero feature-hash overlap."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from xai_surfacebench.calibration import feature_hashes, fit_score_model, write_score_stream, write_summary

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    data = ROOT / "data" / "unsw_nb15"; raw = data / "raw"
    train_path, test_path = raw / "train.csv", raw / "test.csv"
    if not train_path.exists() or not test_path.exists():
        raise SystemExit("run scripts/calibrate_unsw_nb15.py first")
    train, test = pd.read_csv(train_path), pd.read_csv(test_path)
    excluded = {"id","label","attack_cat"}; features = [column for column in train.columns if column not in excluded and column in test.columns]
    train = train.drop_duplicates(subset=features).reset_index(drop=True)
    test = test.drop_duplicates(subset=features).reset_index(drop=True)
    train_hash = feature_hashes(train, features); test_hash = feature_hashes(test, features)
    train_set = set(train_hash); keep = ~test_hash.isin(train_set); test = test.loc[keep].reset_index(drop=True)
    if set(feature_hashes(test, features)) & train_set: raise AssertionError("feature-hash overlap remains")
    scores, metrics = fit_score_model(train, test, label_column="label", excluded_columns=["id","attack_cat"])
    metrics["feature_hash_overlap"] = 0
    attack = test["attack_cat"].astype(str) if "attack_cat" in test else None
    write_score_stream(data / "unsw_nb15_deduplicated_score_stream.csv", scores, test["label"].astype(int), attack)
    write_summary(data / "unsw_nb15_deduplicated_calibration_summary.json", "UNSW-NB15 de-duplicated", metrics, notes="Feature duplicates are removed within splits and held-out feature hashes overlapping training are removed.")
    print(metrics); return 0


if __name__ == "__main__": raise SystemExit(main())

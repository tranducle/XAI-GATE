#!/usr/bin/env python3
"""Build a de-duplicated held-out TON_IoT network-flow score-stream anchor."""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

from xai_surfacebench.calibration import fit_score_model, write_score_stream, write_summary

ROOT = Path(__file__).resolve().parents[1]


def normalize_label(frame: pd.DataFrame) -> tuple[pd.DataFrame, str, str | None]:
    for label in ["label","Label"]:
        if label in frame.columns:
            frame = frame.copy(); frame[label] = frame[label].astype(int); attack = "type" if "type" in frame.columns else ("attack" if "attack" in frame.columns else None); return frame, label, attack
    raise ValueError("TON_IoT CSV must contain label or Label")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, nargs="?", default=ROOT / "data" / "toniot" / "network.csv")
    args = parser.parse_args()
    if not args.input_csv.exists(): raise SystemExit(f"provide the public TON_IoT network-flow CSV at {args.input_csv}")
    frame, label, attack = normalize_label(pd.read_csv(args.input_csv))
    excluded = {label};
    if attack: excluded.add(attack)
    features = [column for column in frame.columns if column not in excluded]
    frame = frame.drop_duplicates(subset=features).reset_index(drop=True)
    train, test = train_test_split(frame, test_size=0.30, random_state=2026, stratify=frame[label])
    scores, metrics = fit_score_model(train.reset_index(drop=True), test.reset_index(drop=True), label_column=label, excluded_columns=[attack] if attack else [])
    data = ROOT / "data" / "toniot"; families = test[attack].astype(str) if attack else None
    write_score_stream(data / "toniot_score_stream.csv", scores, test[label].astype(int), families)
    write_summary(data / "toniot_calibration_summary.json", "TON_IoT", metrics, notes="De-duplicated stratified held-out public network-flow calibration anchor.")
    print(metrics); return 0


if __name__ == "__main__": raise SystemExit(main())

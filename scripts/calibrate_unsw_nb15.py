#!/usr/bin/env python3
"""Build the public UNSW-NB15 held-out score-stream calibration anchor."""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path
import pandas as pd

from xai_surfacebench.calibration import fit_score_model, write_score_stream, write_summary

ROOT = Path(__file__).resolve().parents[1]
URLS = {
    "train": "https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/main/train.csv",
    "test": "https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/main/test.csv",
}


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists(): urllib.request.urlretrieve(url, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--force-download", action="store_true"); args = parser.parse_args()
    data = ROOT / "data" / "unsw_nb15"; raw = data / "raw"
    train_path, test_path = raw / "train.csv", raw / "test.csv"
    if args.force_download:
        train_path.unlink(missing_ok=True); test_path.unlink(missing_ok=True)
    download(URLS["train"], train_path); download(URLS["test"], test_path)
    train, test = pd.read_csv(train_path), pd.read_csv(test_path)
    scores, metrics = fit_score_model(train, test, label_column="label", excluded_columns=["id","attack_cat"])
    attack = test["attack_cat"].astype(str) if "attack_cat" in test else None
    write_score_stream(data / "unsw_nb15_score_stream.csv", scores, test["label"].astype(int), attack)
    write_summary(data / "unsw_nb15_calibration_summary.json", "UNSW-NB15", metrics, notes="Public train/test split; calibration model is not a detector contribution.")
    print(metrics); return 0


if __name__ == "__main__": raise SystemExit(main())

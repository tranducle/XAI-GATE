#!/usr/bin/env python3
"""Audit exact feature-hash overlap between de-duplicated UNSW-NB15 splits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import pandas as pd


def row_hashes(frame: pd.DataFrame, excluded: set[str]) -> set[str]:
    features = [column for column in frame.columns if column not in excluded]
    out = set()
    for values in frame[features].astype(str).itertuples(index=False, name=None):
        out.add(hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("test", type=Path)
    args = parser.parse_args()
    train = pd.read_csv(args.train); test = pd.read_csv(args.test)
    excluded = {"label","Label","attack_cat","id"}
    overlap = row_hashes(train, excluded) & row_hashes(test, excluded)
    print(f"train_rows={len(train)} test_rows={len(test)} feature_hash_overlap={len(overlap)}")
    return 1 if overlap else 0


if __name__ == "__main__": raise SystemExit(main())

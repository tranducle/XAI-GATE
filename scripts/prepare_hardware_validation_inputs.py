#!/usr/bin/env python3
"""Select deterministic CICIoT2023 records for explanation-service timing."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xai_surfacebench.hardware_benchmark import FEATURES, select_deterministic_rows


def main() -> int:
    replay_dir = ROOT / "data" / "ciciot2023_temporal" / "raw"
    out = ROOT / "data" / "hardware_validation"; out.mkdir(parents=True, exist_ok=True)
    parts = []
    for path in sorted(replay_dir.glob("*.parquet"))[:5]:
        frame = pd.read_parquet(path)
        parts.append(select_deterministic_rows(frame, source_file=path.name, count=20))
    samples = pd.concat(parts, ignore_index=True)
    samples.to_parquet(out / "replay_samples.parquet", index=False)
    background = samples.head(32).copy()
    background.to_parquet(out / "calibration_background.parquet", index=False)
    manifest = {"features": FEATURES, "replay_records": len(samples), "background_records": len(background), "selection_rule": "smallest SHA-256 identifiers over source_file and row_index"}
    (out / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

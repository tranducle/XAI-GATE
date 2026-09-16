#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.hardware_benchmark import FEATURES, select_deterministic_rows  # noqa: E402

DATA_ROOT = ROOT / "data" / "ciciot2023_temporal"
OUT = ROOT / "data" / "hardware_validation"
REPLAY_COUNT_PER_CAPTURE = 20
CALIBRATION_COUNT_PER_CAPTURE = 8
SHAP_BACKGROUND_COUNT = 32


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prep_manifest_path = DATA_ROOT / "temporal_preprocessing_manifest.json"
    prep = json.loads(prep_manifest_path.read_text(encoding="utf-8"))

    replay_parts = []
    replay_sources = []
    session_by_file = {session["filename"]: session for session in prep["sessions"]}
    for filename in prep["replay_files"]:
        path = DATA_ROOT / "replay" / filename
        session = session_by_file[filename]
        frame = pd.read_parquet(path)
        selected = select_deterministic_rows(
            frame,
            source_file=session["source_file"],
            count=REPLAY_COUNT_PER_CAPTURE,
        )
        replay_parts.append(selected)
        replay_sources.append(
            {
                "filename": filename,
                "source_file": session["source_file"],
                "rows_available": int(len(frame)),
                "rows_selected": int(len(selected)),
                "sha256": sha256_file(path),
            }
        )

    replay = pd.concat(replay_parts, ignore_index=True)
    replay_path = OUT / "hardware_replay_samples.parquet"
    replay.to_parquet(replay_path, index=False)

    calibration_parts = []
    calibration_sources = []
    for filename, source_file in zip(prep["calibration_files"], prep["calibration_source_files"], strict=True):
        path = DATA_ROOT / "calibration" / filename
        frame = pd.read_parquet(path)
        selected = select_deterministic_rows(
            frame,
            source_file=source_file,
            count=CALIBRATION_COUNT_PER_CAPTURE,
        )
        calibration_parts.append(selected)
        calibration_sources.append(
            {
                "filename": filename,
                "source_file": source_file,
                "rows_available": int(len(frame)),
                "rows_selected": int(len(selected)),
                "sha256": sha256_file(path),
            }
        )

    calibration = pd.concat(calibration_parts, ignore_index=True).sort_values("record_id", kind="mergesort")
    calibration = calibration.reset_index(drop=True)
    calibration_path = OUT / "hardware_calibration_background.parquet"
    calibration.to_parquet(calibration_path, index=False)
    shap_background_ids = calibration.head(SHAP_BACKGROUND_COUNT)["record_id"].tolist()

    model_path = DATA_ROOT / "model" / "temporal_score_model.joblib"
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_order": list(FEATURES),
        "replay_records": int(len(replay)),
        "replay_count_per_capture": REPLAY_COUNT_PER_CAPTURE,
        "calibration_records": int(len(calibration)),
        "calibration_count_per_capture": CALIBRATION_COUNT_PER_CAPTURE,
        "shap_background_count": SHAP_BACKGROUND_COUNT,
        "shap_background_record_ids": shap_background_ids,
        "replay_record_ids": replay["record_id"].tolist(),
        "calibration_record_ids": calibration["record_id"].tolist(),
        "replay_sources": replay_sources,
        "calibration_sources": calibration_sources,
        "artifacts": {
            "replay_samples": {
                "path": str(replay_path.relative_to(ROOT)),
                "sha256": sha256_file(replay_path),
            },
            "calibration_background": {
                "path": str(calibration_path.relative_to(ROOT)),
                "sha256": sha256_file(calibration_path),
            },
            "model": {
                "path": str(model_path.relative_to(ROOT)),
                "sha256": sha256_file(model_path),
            },
            "temporal_preprocessing_manifest": {
                "path": str(prep_manifest_path.relative_to(ROOT)),
                "sha256": sha256_file(prep_manifest_path),
            },
        },
        "selection_rule": "smallest SHA-256 record IDs over (source_file, zero-based row_index)",
        "input_contract": "only documented evaluation predictor features are persisted; labels and timestamps are excluded",
    }
    manifest_path = OUT / "hardware_input_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"replay_records={len(replay)}")
    print(f"calibration_records={len(calibration)}")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

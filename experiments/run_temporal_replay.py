#!/usr/bin/env python3
"""Run quick or full CICIoT2023 temporal replay for timestamp-preserving temporal replay study."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.temporal_replay import shuffle_slot_order, simulate_trace_policy  # noqa: E402

POLICIES = [
    "always_explain",
    "threshold_explain",
    "budget_only_bexgov",
    "selective_explanations_adapted",
    "resource_aware_offload_adapted",
    "xai_gate",
]
SMOKE_FILES = [
    "Benign_Final__BenignTraffic3.parquet",
    "DDoS-SynonymousIP_Flood__DDoS-SynonymousIP_Flood13.parquet",
]
SHUFFLE_SEED = 20260914


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataframe_digest(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def marginal_digest(frame: pd.DataFrame) -> str:
    columns = [column for column in frame.columns if column != "slot"]
    canonical = frame[columns].sort_values(columns, kind="mergesort").reset_index(drop=True)
    return dataframe_digest(canonical)


def load_sessions() -> list[dict[str, Any]]:
    manifest_path = ROOT / "data" / "ciciot2023_temporal" / "temporal_preprocessing_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return list(payload["sessions"])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(mode: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if mode not in {"quick", "full"}:
        raise ValueError("mode must be quick or full")
    sessions = load_sessions()
    if mode == "quick":
        sessions = [session for session in sessions if session["filename"] in SMOKE_FILES]
    expected_count = 2 if mode == "quick" else 5
    if len(sessions) != expected_count:
        raise RuntimeError(f"Expected {expected_count} replay sessions for mode {mode}, found {len(sessions)}")

    rows: list[dict[str, Any]] = []
    trace_inventory: list[dict[str, Any]] = []
    for session in sessions:
        slot_path = ROOT / session["slot_path"]
        chronological = pd.read_csv(slot_path)
        shuffled = shuffle_slot_order(chronological, seed=SHUFFLE_SEED)
        chronological_digest = dataframe_digest(chronological)
        shuffled_digest = dataframe_digest(shuffled)
        chronological_marginal = marginal_digest(chronological)
        shuffled_marginal = marginal_digest(shuffled)
        if chronological_marginal != shuffled_marginal:
            raise AssertionError(f"Shuffled marginal mismatch for {session['filename']}")

        trace_inventory.append(
            {
                "filename": session["filename"],
                "source_file": session["source_file"],
                "slot_file": str(slot_path.relative_to(ROOT)),
                "slot_file_sha256": sha256_file(slot_path),
                "slots": int(len(chronological)),
                "chronological_sequence_sha256": chronological_digest,
                "shuffled_sequence_sha256": shuffled_digest,
                "marginal_sha256": chronological_marginal,
                "shuffle_seed": SHUFFLE_SEED,
            }
        )

        for condition, trace, sequence_digest in [
            ("chronological", chronological, chronological_digest),
            ("shuffled", shuffled, shuffled_digest),
        ]:
            for policy in POLICIES:
                result = simulate_trace_policy(
                    trace,
                    policy=policy,
                    session_id=session["filename"],
                    condition=condition,
                )
                result.update(
                    {
                        "source_file": session["source_file"],
                        "slot_file_sha256": sha256_file(slot_path),
                        "trace_sequence_sha256": sequence_digest,
                        "trace_marginal_sha256": chronological_marginal,
                        "shuffle_seed": SHUFFLE_SEED if condition == "shuffled" else "",
                    }
                )
                rows.append(result)
                print(
                    f"{mode:8s} {session['filename']:72s} {condition:13s} {policy:36s} "
                    f"cov={result['high_risk_explanation_coverage']:.4f} "
                    f"debt={result['mean_explanation_debt']:.2f} "
                    f"exp={result['exposure_use']:.4f}"
                )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "policies": POLICIES,
        "session_count": len(sessions),
        "condition_count": 2,
        "expected_run_count": len(sessions) * 2 * len(POLICIES),
        "actual_run_count": len(rows),
        "shuffle_seed": SHUFFLE_SEED,
        "trace_inventory": trace_inventory,
    }
    return rows, metadata


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_temporal_replay.py quick|full")
    mode = sys.argv[1]
    rows, metadata = run(mode)
    out_dir = ROOT / "results" / "temporal_replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{mode}_runs.csv"
    json_path = out_dir / f"{mode}_metadata.json"
    write_csv(csv_path, rows)
    json_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"runs={len(rows)}")
    print(f"runs_csv={csv_path}")
    print(f"metadata_json={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

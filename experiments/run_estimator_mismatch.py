#!/usr/bin/env python3
"""Run evaluation estimator-mismatch robustness on synthetic and temporal workloads."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.core import CalibrationProfile, load_json, simulate_run  # noqa: E402
from xai_surfacebench.temporal_replay import simulate_trace_policy  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "estimator_mismatch.json"
MANIFEST_PATH = ROOT / "data" / "ciciot2023_temporal" / "temporal_preprocessing_manifest.json"
OUTPUT_DIR = ROOT / "results" / "estimator_mismatch"


ACTIONS = ["none", "coarse", "full", "offload", "audit", "redact", "delay"]
BUCKETS = ["low", "medium", "high", "critical"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def action_assignment_disagreement(
    nominal_trace: list[dict[str, dict[str, float]]],
    variant_trace: list[dict[str, dict[str, float]]],
) -> float:
    """Return fraction of alert units reassigned to a different action vs nominal."""

    if len(nominal_trace) != len(variant_trace):
        raise AssertionError("Action traces have different slot counts")
    total = 0.0
    disagreement = 0.0
    for nominal_slot, variant_slot in zip(nominal_trace, variant_trace, strict=True):
        for bucket in BUCKETS:
            nominal_actions = nominal_slot.get(bucket, {})
            variant_actions = variant_slot.get(bucket, {})
            nominal_total = sum(float(v) for v in nominal_actions.values())
            variant_total = sum(float(v) for v in variant_actions.values())
            if not math.isclose(nominal_total, variant_total, rel_tol=0.0, abs_tol=1e-8):
                raise AssertionError(
                    f"Bucket workload differs for {bucket}: {nominal_total} vs {variant_total}"
                )
            matched = sum(
                min(float(nominal_actions.get(action, 0.0)), float(variant_actions.get(action, 0.0)))
                for action in ACTIONS
            )
            total += nominal_total
            disagreement += max(0.0, nominal_total - matched)
    return disagreement / max(total, 1.0)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key.startswith("_"):
                continue
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def variant_map(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    variants = {str(v["name"]): dict(v) for v in config["variants"]}
    if "nominal" not in variants:
        raise RuntimeError("estimator-mismatch config must include nominal variant")
    return variants


def selected_design(config: Mapping[str, Any], mode: str) -> tuple[list[int], list[str], list[str], list[str], list[str]]:
    if mode == "full":
        return (
            [int(x) for x in config["seeds"]],
            [str(x) for x in config["regimes"]],
            [str(v["name"]) for v in config["variants"]],
            [str(x) for x in config["temporal_sessions"]],
            [str(v["name"]) for v in config["variants"]],
        )
    if mode == "quick":
        quick_check = config["quick_check"]
        return (
            [int(x) for x in quick_check["seeds"]],
            [str(x) for x in quick_check["regimes"]],
            [str(x) for x in quick_check["variants"]],
            [str(x) for x in quick_check["temporal_sessions"]],
            [str(x) for x in quick_check["temporal_variants"]],
        )
    raise ValueError("mode must be quick or full")


def add_common_diagnostics(row: dict[str, Any], disagreement: float) -> dict[str, Any]:
    row["action_assignment_disagreement_rate"] = float(disagreement)
    row["actual_minus_estimated_exposure_use"] = float(
        row["exposure_use"] - row["estimated_exposure_use"]
    )
    row["realization_profile_fixed"] = True
    row["utility_weights_fixed"] = True
    return row


def run_synthetic(
    config: Mapping[str, Any],
    seeds: list[int],
    regimes: list[str],
    variant_names: list[str],
) -> list[dict[str, Any]]:
    variants = variant_map(config)
    calibration = CalibrationProfile()
    rows: list[dict[str, Any]] = []

    for seed in seeds:
        for regime in regimes:
            nominal_variant = variants["nominal"]
            nominal = simulate_run(
                config,
                seed=seed,
                policy="xai_gate",
                regime=regime,
                variant=nominal_variant,
                calibration=calibration,
                collect_action_trace=True,
            )
            nominal_trace = nominal.pop("_action_trace")
            add_common_diagnostics(nominal, 0.0)
            rows.append(nominal)
            nominal_hash = nominal["workload_hash"]

            for variant_name in variant_names:
                if variant_name == "nominal":
                    continue
                result = simulate_run(
                    config,
                    seed=seed,
                    policy="xai_gate",
                    regime=regime,
                    variant=variants[variant_name],
                    calibration=calibration,
                    collect_action_trace=True,
                )
                trace = result.pop("_action_trace")
                if result["workload_hash"] != nominal_hash:
                    raise AssertionError(
                        f"Common-random-number failure for seed={seed}, regime={regime}, variant={variant_name}"
                    )
                disagreement = action_assignment_disagreement(nominal_trace, trace)
                add_common_diagnostics(result, disagreement)
                rows.append(result)
    return rows


def load_temporal_sessions() -> dict[str, dict[str, Any]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {str(session["filename"]): dict(session) for session in payload["sessions"]}


def run_temporal(
    config: Mapping[str, Any],
    session_names: list[str],
    variant_names: list[str],
) -> list[dict[str, Any]]:
    variants = variant_map(config)
    sessions = load_temporal_sessions()
    rows: list[dict[str, Any]] = []

    for session_name in session_names:
        if session_name not in sessions:
            raise RuntimeError(f"Unknown temporal session {session_name}")
        session = sessions[session_name]
        slot_path = ROOT / str(session["slot_path"])
        slots = pd.read_csv(slot_path)

        nominal_multipliers = variants["nominal"]["estimation_multipliers"]
        nominal = simulate_trace_policy(
            slots,
            policy="xai_gate",
            session_id=session_name,
            condition="chronological",
            estimation_multipliers=nominal_multipliers,
            collect_action_trace=True,
        )
        nominal_trace = nominal.pop("_action_trace")
        nominal["stage"] = "temporal_estimator_mismatch"
        nominal["variant"] = "nominal"
        nominal["source_file"] = session["source_file"]
        nominal["slot_file_sha256"] = sha256_file(slot_path)
        add_common_diagnostics(nominal, 0.0)
        rows.append(nominal)

        for variant_name in variant_names:
            if variant_name == "nominal":
                continue
            result = simulate_trace_policy(
                slots,
                policy="xai_gate",
                session_id=session_name,
                condition="chronological",
                estimation_multipliers=variants[variant_name]["estimation_multipliers"],
                collect_action_trace=True,
            )
            trace = result.pop("_action_trace")
            result["stage"] = "temporal_estimator_mismatch"
            result["variant"] = variant_name
            result["source_file"] = session["source_file"]
            result["slot_file_sha256"] = sha256_file(slot_path)
            disagreement = action_assignment_disagreement(nominal_trace, trace)
            add_common_diagnostics(result, disagreement)
            rows.append(result)
    return rows


def run(mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    config = load_json(CONFIG_PATH)
    seeds, regimes, variant_names, temporal_sessions, temporal_variant_names = selected_design(config, mode)
    synthetic_rows = run_synthetic(config, seeds, regimes, variant_names)
    temporal_rows = run_temporal(config, temporal_sessions, temporal_variant_names)
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "config_sha256": sha256_file(CONFIG_PATH),
        "core_sha256": sha256_file(ROOT / "src" / "xai_surfacebench" / "core.py"),
        "temporal_replay_sha256": sha256_file(ROOT / "src" / "xai_surfacebench" / "temporal_replay.py"),
        "synthetic": {
            "seeds": seeds,
            "regimes": regimes,
            "variants": variant_names,
            "expected_runs": len(seeds) * len(regimes) * len(variant_names),
            "actual_runs": len(synthetic_rows),
        },
        "temporal": {
            "sessions": temporal_sessions,
            "variants": temporal_variant_names,
            "expected_runs": len(temporal_sessions) * len(temporal_variant_names),
            "actual_runs": len(temporal_rows),
        },
    }
    return synthetic_rows, temporal_rows, metadata


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"quick", "full"}:
        raise SystemExit("usage: run_estimator_mismatch.py quick|full")
    mode = sys.argv[1]
    synthetic_rows, temporal_rows, metadata = run(mode)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    synthetic_path = OUTPUT_DIR / f"{mode}_synthetic_runs.csv"
    temporal_path = OUTPUT_DIR / f"{mode}_temporal_runs.csv"
    metadata_path = OUTPUT_DIR / f"{mode}_metadata.json"
    write_csv(synthetic_path, synthetic_rows)
    write_csv(temporal_path, temporal_rows)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"synthetic_runs={len(synthetic_rows)}")
    print(f"temporal_runs={len(temporal_rows)}")
    print(f"synthetic_csv={synthetic_path}")
    print(f"temporal_csv={temporal_path}")
    print(f"metadata_json={metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

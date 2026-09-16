"""Hardware-measurement utilities for explanation-service validation."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

import pandas as pd

FEATURES = [
    "flow_duration",
    "Header_Length",
    "Protocol Type",
    "Duration",
    "Rate",
    "Srate",
    "Drate",
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
]


def validate_feature_contract(frame: pd.DataFrame, features: Sequence[str] = FEATURES) -> None:
    missing = [name for name in features if name not in frame.columns]
    if missing:
        raise ValueError(f"missing required predictor fields: {missing}")


def select_deterministic_rows(frame: pd.DataFrame, *, source_file: str, count: int) -> pd.DataFrame:
    """Select rows by the smallest SHA-256 identifiers over source name and row index."""
    validate_feature_contract(frame)
    ranked = []
    for index in range(len(frame)):
        token = f"{source_file}|{index}".encode("utf-8")
        ranked.append((hashlib.sha256(token).hexdigest(), index))
    selected = [index for _, index in sorted(ranked)[: max(0, int(count))]]
    out = frame.iloc[selected].copy().reset_index(drop=True)
    out.insert(0, "record_id", [hashlib.sha256(f"{source_file}|{index}".encode("utf-8")).hexdigest() for index in selected])
    return out[["record_id", *FEATURES]]


def build_measured_compute_profile(median_ms: Mapping[str, float], *, full_measurement: str) -> dict[str, dict[str, float]]:
    """Normalize measured action latencies into the core compute-profile field."""
    full = max(float(median_ms[full_measurement]), 1e-12)
    mapping = {"none":"none", "coarse":"coarse", "full":full_measurement, "offload":"offload", "audit":"audit", "redact":"redact", "delay":"delay"}
    return {action: {"compute": max(0.0, float(median_ms[source]) / full)} for action, source in mapping.items()}


def capacity_overlay(action_trace: Sequence[Mapping[str, Mapping[str, float]]], p95_ms: Mapping[str, float], *, capacity_ms: float = 1000.0) -> dict[str, Any]:
    """Convert action counts into one-worker service demand and overload statistics."""
    demands = []
    mapping = {"none":"none", "coarse":"coarse", "full":"full", "offload":"offload", "audit":"audit", "redact":"redact", "delay":"delay"}
    for slot in action_trace:
        demand = 0.0
        for counts in slot.values():
            for action, count in counts.items():
                demand += float(count) * float(p95_ms[mapping[action]])
        demands.append(demand)
    overload = [value > float(capacity_ms) for value in demands]
    longest = current = 0
    backlog = max_backlog = 0.0
    for value, is_over in zip(demands, overload):
        current = current + 1 if is_over else 0
        longest = max(longest, current)
        backlog = max(0.0, backlog + value - float(capacity_ms))
        max_backlog = max(max_backlog, backlog)
    return {
        "slots": len(demands),
        "total_demand_ms": sum(demands),
        "mean_demand_ms_per_slot": sum(demands) / max(len(demands), 1),
        "overload_slots": sum(1 for value in overload if value),
        "overload_slot_fraction": sum(1 for value in overload if value) / max(len(demands), 1),
        "max_consecutive_overload_slots": longest,
        "final_work_backlog_ms": backlog,
        "max_work_backlog_ms": max_backlog,
    }

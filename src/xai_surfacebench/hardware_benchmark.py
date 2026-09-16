from __future__ import annotations

import hashlib
from collections.abc import Mapping

import pandas as pd

FEATURES = (
    "protocol",
    "src_port",
    "dst_port",
    "packets",
    "packets_rev",
    "bytes",
    "bytes_rev",
    "tcp_flags",
    "tcp_flags_rev",
    "duration",
)

SIMULATOR_ACTIONS = ("none", "coarse", "full", "offload", "audit", "redact", "delay")


def stable_record_id(source_file: str, row_index: int) -> str:
    payload = f"{source_file}\n{int(row_index)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def select_deterministic_rows(frame: pd.DataFrame, *, source_file: str, count: int) -> pd.DataFrame:
    if count <= 0:
        raise ValueError("count must be positive")
    missing = [name for name in FEATURES if name not in frame.columns]
    if missing:
        raise ValueError(f"missing required predictor fields: {missing}")
    if len(frame) < count:
        raise ValueError(f"requested {count} rows from frame with only {len(frame)} rows")

    candidates = []
    for position in range(len(frame)):
        record_id = stable_record_id(source_file, position)
        candidates.append((record_id, position))
    selected = sorted(candidates, key=lambda item: item[0])[:count]

    rows = []
    for record_id, position in selected:
        source_row = frame.iloc[position]
        row = {
            "record_id": record_id,
            "source_file": source_file,
            "row_index": int(position),
        }
        for feature in FEATURES:
            row[feature] = source_row[feature]
        rows.append(row)
    return pd.DataFrame(rows, columns=["record_id", "source_file", "row_index", *FEATURES])


def build_measured_compute_profile(
    medians_ms: Mapping[str, float], *, full_measurement: str
) -> dict[str, dict[str, float]]:
    if full_measurement not in medians_ms:
        raise ValueError(f"missing full measurement {full_measurement!r}")
    baseline = float(medians_ms[full_measurement])
    if baseline <= 0:
        raise ValueError("full-explainer median must be positive")

    measurement_for_action = {
        "coarse": "coarse",
        "full": full_measurement,
        "offload": "offload",
        "audit": "audit",
        "redact": "redact",
    }
    result: dict[str, dict[str, float]] = {
        "none": {"compute": 0.0},
        "delay": {"compute": 0.0},
    }
    for action, measurement in measurement_for_action.items():
        if measurement not in medians_ms:
            raise ValueError(f"missing measurement {measurement!r}")
        value = float(medians_ms[measurement])
        if value < 0:
            raise ValueError(f"negative median for {measurement!r}")
        result[action] = {"compute": value / baseline}
    return {action: result[action] for action in SIMULATOR_ACTIONS}


def slot_demand_ms(
    action_counts: Mapping[str, float], p95_ms: Mapping[str, float]
) -> float:
    total = 0.0
    for action, count in action_counts.items():
        if action not in p95_ms:
            raise ValueError(f"missing p95 latency for action {action!r}")
        total += float(count) * float(p95_ms[action])
    return total


def redact_vector(values: list[float] | tuple[float, ...], indices: list[int] | tuple[int, ...]) -> list[float]:
    result = [float(value) for value in values]
    for index in indices:
        if index < 0 or index >= len(result):
            raise IndexError(index)
        result[index] = 0.0
    return result


def build_offload_payload(values: list[float] | tuple[float, ...], *, score: float) -> bytes:
    import gzip
    import json

    payload = {
        "score": round(float(score), 6),
        "features": [round(float(value), 5) for value in values],
        "request": "remote_explanation",
        "explainer": "managed_posthoc",
    }
    return gzip.compress(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"), compresslevel=3)


def capacity_overlay(
    action_trace: list[dict[str, dict[str, float]]],
    p95_ms: Mapping[str, float],
    *,
    capacity_ms: float = 1000.0,
) -> dict[str, float | int]:
    if capacity_ms <= 0:
        raise ValueError("capacity_ms must be positive")
    backlog = 0.0
    max_backlog = 0.0
    total_demand = 0.0
    overload_slots = 0
    consecutive = 0
    max_consecutive = 0
    for slot in action_trace:
        counts: dict[str, float] = {}
        for bucket_actions in slot.values():
            for action, count in bucket_actions.items():
                counts[action] = counts.get(action, 0.0) + float(count)
        demand = slot_demand_ms(counts, p95_ms)
        total_demand += demand
        if demand > capacity_ms:
            overload_slots += 1
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0
        backlog = max(0.0, backlog + demand - capacity_ms)
        max_backlog = max(max_backlog, backlog)
    slots = len(action_trace)
    return {
        "slots": slots,
        "total_demand_ms": total_demand,
        "mean_demand_ms_per_slot": total_demand / max(slots, 1),
        "overload_slots": overload_slots,
        "overload_slot_fraction": overload_slots / max(slots, 1),
        "max_consecutive_overload_slots": max_consecutive,
        "final_work_backlog_ms": backlog,
        "max_work_backlog_ms": max_backlog,
    }

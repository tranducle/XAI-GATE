"""Timestamp-preserving replay utilities for XAI-SurfaceBench."""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Mapping, Sequence

import pandas as pd

from . import core
from .extensions import install_policy_extensions


def _first_number(row: Mapping[str, Any], names: Sequence[str], default: float = 0.0) -> float:
    for name in names:
        if name in row and pd.notna(row[name]):
            try:
                return float(row[name])
            except (TypeError, ValueError):
                pass
    return float(default)


def slot_bucket_counts(row: Mapping[str, Any]) -> Dict[str, int]:
    """Read one-second score-bucket counts from common preprocessing schemas."""
    out: Dict[str, int] = {}
    patterns = {
        "low": ["low_count", "alerts_low", "bucket_low", "low"],
        "medium": ["medium_count", "alerts_medium", "bucket_medium", "medium"],
        "high": ["high_count", "alerts_high", "bucket_high", "high"],
        "critical": ["critical_count", "alerts_critical", "bucket_critical", "critical"],
    }
    for bucket, names in patterns.items():
        out[bucket] = max(0, int(round(_first_number(row, names, 0.0))))
    if sum(out.values()) == 0:
        alerts = max(0, int(round(_first_number(row, ["alert_count", "alerts", "n_alerts"], 0.0))))
        score = _first_number(row, ["mean_score", "score", "risk_score"], 0.55)
        out[core.score_to_bucket(score)] = alerts
    return out


def slot_arrivals(row: Mapping[str, Any], bucket_counts: Mapping[str, int]) -> int:
    value = _first_number(row, ["packet_arrivals", "arrivals", "flow_count", "flows", "count", "n_flows"], -1.0)
    if value >= 0:
        return max(0, int(round(value)))
    return max(0, int(sum(bucket_counts.values())))


def shuffled_slots(frame: pd.DataFrame, seed: int = 2026) -> pd.DataFrame:
    """Shuffle complete slot records while preserving the slot multiset."""
    if frame.empty:
        return frame.copy()
    order = list(range(len(frame)))
    random.Random(seed).shuffle(order)
    return frame.iloc[order].reset_index(drop=True)


def simulate_trace_policy(frame: pd.DataFrame, *, policy: str, session_id: str, condition: str = "chronological", base_overrides: Mapping[str, float] | None = None, action_profile_overrides: Mapping[str, Mapping[str, float]] | None = None, collect_action_trace: bool = False) -> Dict[str, Any]:
    """Replay a prepared one-second slot trace through one explanation policy."""
    install_policy_extensions()
    base = core.deep_merge(core.DEFAULT_BASE, dict(base_overrides or {}))
    profiles = {name: dict(values) for name, values in core.ACTION_PROFILES.items()}
    if action_profile_overrides:
        for action, updates in action_profile_overrides.items():
            if action not in profiles:
                raise ValueError(f"unknown action profile: {action}")
            profiles[action].update({key: float(value) for key, value in updates.items()})
    weights = dict(core.DEFAULT_XAI_GATE_WEIGHTS)
    flags = core.ablation_flags("default")
    state = core.SimulationState()
    acc = {key: 0.0 for key in ["arrivals","dropped","served","queue_sum","delay_sum","alerts","high_risk_alerts","explained_units","high_risk_explained_units","explanation_delay_sum","debt_sum","offload_count","audit_count","redaction_count","local_compute_units","budget_violation_slots","exposure_violation_slots","baseline_expected_alerts"]}
    action_trace = []
    slots = max(1, len(frame))
    for _, row_series in frame.iterrows():
        row = row_series.to_dict()
        state.slot_local_load = 0.0
        buckets = slot_bucket_counts(row)
        arrivals = slot_arrivals(row, buckets)
        signals = {
            "suspicion": min(1.0, max(0.0, _first_number(row, ["suspicion", "demand_pressure"], 0.15))),
            "rtt_uncertainty": max(0.0, _first_number(row, ["rtt_uncertainty", "rtt"], 0.08)),
            "high_risk_probs": dict(core.HIGH_RISK_PROBABILITY),
        }
        actions = core.allocate_actions(policy, buckets, state, base, weights, flags, signals, profiles)
        if collect_action_trace:
            action_trace.append({bucket: dict(counts) for bucket, counts in actions.items()})
        for bucket, counts in actions.items():
            for action, count in counts.items():
                core.accumulate_action_metrics(acc, bucket, action, count, state, base, signals["high_risk_probs"], signals, profiles)
        service_rate = max(1.0, float(base["packet_service_rate"]) * float(base["service_capacity_multiplier"]) - float(base["packet_service_interference"]) * state.slot_local_load)
        state.packet_queue += arrivals
        served = min(state.packet_queue, service_rate)
        state.packet_queue -= served
        if state.packet_queue > float(base["packet_buffer_capacity"]):
            acc["dropped"] += state.packet_queue - float(base["packet_buffer_capacity"])
            state.packet_queue = float(base["packet_buffer_capacity"])
        spare = max(0.0, float(base["local_explanation_budget"]) - state.slot_local_load)
        debt_service = min(state.explanation_debt, spare * float(base["debt_service_rate"]) / max(float(base["local_explanation_budget"]), 1e-9))
        state.explanation_debt = max(0.0, state.explanation_debt - debt_service)
        acc["arrivals"] += arrivals
        acc["served"] += served
        acc["queue_sum"] += state.packet_queue
        acc["delay_sum"] += state.packet_queue / max(served, 1.0)
        acc["debt_sum"] += state.explanation_debt
        if state.slot_local_load > float(base["local_explanation_budget"]):
            acc["budget_violation_slots"] += 1.0
        if state.exposure_total > float(base["exposure_budget_total"]):
            acc["exposure_violation_slots"] += 1.0
        acc["baseline_expected_alerts"] += max(1.0, arrivals) * float(base["alert_probability"])
    alerts = max(acc["alerts"], 1.0)
    high = max(acc["high_risk_alerts"], 1.0)
    arrivals_total = max(acc["arrivals"], 1.0)
    exposure_budget = max(float(base["exposure_budget_total"]), 1e-9)
    result = {
        "stage": "temporal_replay",
        "session_id": session_id,
        "condition": condition,
        "policy": policy,
        "slots": len(frame),
        "packet_drop_rate": acc["dropped"] / arrivals_total,
        "mean_packet_delay": acc["delay_sum"] / slots,
        "mean_packet_queue": acc["queue_sum"] / slots,
        "explanation_coverage": acc["explained_units"] / alerts,
        "high_risk_explanation_coverage": acc["high_risk_explained_units"] / high,
        "mean_explanation_delay": acc["explanation_delay_sum"] / alerts,
        "mean_explanation_debt": acc["debt_sum"] / slots,
        "exposure_use": state.exposure_total / exposure_budget,
        "offload_rate": acc["offload_count"] / alerts,
        "audit_rate": acc["audit_count"] / alerts,
        "redaction_rate": acc["redaction_count"] / alerts,
        "local_compute_load": acc["local_compute_units"] / slots,
        "budget_violation_rate": acc["budget_violation_slots"] / slots,
        "exposure_budget_violation_rate": acc["exposure_violation_slots"] / slots,
    }
    for key, value in result.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise AssertionError(f"non-finite trace metric {key}")
    if collect_action_trace:
        result["_action_trace"] = action_trace
    return result

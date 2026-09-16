"""Trace-driven helpers for timestamp-preserving XAI-SurfaceBench replay."""

from __future__ import annotations

import random
import math
from typing import Any, Iterable, Mapping

import pandas as pd

from .core import (
    ACTION_PROFILES,
    DEFAULT_BASE,
    DEFAULT_XAI_GATE_WEIGHTS,
    HIGH_RISK_PROBABILITY,
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    SimulationState,
    ablation_flags,
    action_profiles_for,
    allocate_actions,
    budget_exceeded,
    budget_overshoot,
    deep_merge,
    estimated_action_profiles,
    estimation_multipliers_for,
)


_BUCKET_COLUMNS = {
    "low": "low_count",
    "medium": "medium_count",
    "high": "high_count",
    "critical": "critical_count",
}


def score_bucket(score: float) -> str:
    if score >= 0.86:
        return "critical"
    if score >= 0.68:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def build_slot_table(
    frame: pd.DataFrame,
    reference_nonzero_median: float,
    alert_threshold: float = 0.50,
    reference_arrival_rate: float = 45.0,
) -> pd.DataFrame:
    """Aggregate scored flows into contiguous one-second replay slots."""

    required = {"ts_start", "score", "true_label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required replay columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Replay frame must not be empty")
    if reference_nonzero_median <= 0:
        raise ValueError("reference_nonzero_median must be positive")

    ordered = frame.sort_values("ts_start", kind="mergesort").reset_index(drop=True).copy()
    start = float(ordered["ts_start"].min())
    ordered["slot"] = ((ordered["ts_start"].astype(float) - start) // 1.0).astype(int)
    max_slot = int(ordered["slot"].max())

    slots = pd.DataFrame({"slot": range(max_slot + 1)})
    flow_counts = ordered.groupby("slot", sort=True).size().rename("flow_starts")
    slots = slots.join(flow_counts, on="slot").fillna({"flow_starts": 0})
    slots["flow_starts"] = slots["flow_starts"].astype(int)
    slots["arrival_units"] = (
        slots["flow_starts"].astype(float)
        * float(reference_arrival_rate)
        / float(reference_nonzero_median)
    )

    alerted = ordered.loc[ordered["score"].astype(float) >= float(alert_threshold)].copy()
    alerted["bucket"] = [score_bucket(float(v)) for v in alerted["score"]]
    alert_counts = alerted.groupby("slot", sort=True).size().rename("alert_count")
    slots = slots.join(alert_counts, on="slot").fillna({"alert_count": 0})
    slots["alert_count"] = slots["alert_count"].astype(int)

    for bucket, column in _BUCKET_COLUMNS.items():
        counts = (
            alerted.loc[alerted["bucket"] == bucket]
            .groupby("slot", sort=True)
            .size()
            .rename(column)
        )
        slots = slots.join(counts, on="slot").fillna({column: 0})
        slots[column] = slots[column].astype(int)

        positives = (
            alerted.loc[alerted["bucket"] == bucket]
            .groupby("slot", sort=True)["true_label"]
            .sum()
            .rename(f"{bucket}_positive_count")
        )
        slots = slots.join(positives, on="slot").fillna({f"{bucket}_positive_count": 0.0})
        slots[f"{bucket}_positive_count"] = slots[f"{bucket}_positive_count"].astype(float)

    return slots


def shuffle_slot_order(slots: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Destroy temporal order while preserving the full multiset of slot records."""

    if "slot" not in slots.columns:
        raise ValueError("Slot table must contain a slot column")
    if slots.empty:
        return slots.copy()

    order = list(range(len(slots)))
    random.Random(seed).shuffle(order)
    shuffled = slots.iloc[order].reset_index(drop=True).copy()
    shuffled["slot"] = range(len(shuffled))
    return shuffled


def nonzero_median_flow_starts(timestamps: Iterable[float]) -> float:
    series = pd.Series(list(timestamps), dtype="float64")
    if series.empty:
        raise ValueError("timestamps must not be empty")
    start = float(series.min())
    slot_ids = ((series - start) // 1.0).astype(int)
    counts = slot_ids.value_counts(sort=False)
    nonzero = counts[counts > 0]
    if nonzero.empty:
        raise ValueError("No nonzero one-second slots")
    return float(nonzero.median())


def _accumulate_trace_action_metrics(
    acc: dict[str, float],
    bucket: str,
    action: str,
    count: float,
    state: SimulationState,
    base: Mapping[str, float],
    evaluation_positive_probs: Mapping[str, float],
    debt_risk_probs: Mapping[str, float],
    signals: Mapping[str, Any],
    action_profiles: Mapping[str, Mapping[str, float]],
) -> None:
    """Accumulate replay metrics without feeding ground-truth labels into state.

    True-label prevalence is used only for evaluation counters. Debt dynamics use
    fixed score-bucket risk weights, so changing replay labels cannot alter future
    policy state or action selection.
    """

    if count <= 0:
        return
    profile = action_profiles[action]
    cost_scale = float(base["explanation_cost_scale"])
    evaluation_positive_count = count * float(evaluation_positive_probs[bucket])
    acc["alerts"] += count
    acc["high_risk_alerts"] += evaluation_positive_count
    acc["explained_units"] += count * profile["coverage"]
    acc["high_risk_explained_units"] += evaluation_positive_count * profile["high_risk_coverage"]
    acc["explanation_delay_sum"] += count * profile["delay"]
    if action == "offload":
        acc["explanation_delay_sum"] += count * float(signals["rtt_uncertainty"])

    debt_increment = count * (1.0 - profile["coverage"]) * (
        0.65 + 0.70 * float(debt_risk_probs[bucket])
    )
    if action == "delay":
        debt_increment += 0.35 * count
    debt_increment *= float(base["debt_increment_scale"])
    state.explanation_debt += debt_increment
    state.exposure_total += count * profile["exposure"]
    acc["offload_count"] += count * profile["offload"]
    acc["audit_count"] += count * profile["audit"]
    acc["redaction_count"] += count * profile["redaction"]
    acc["local_compute_units"] += count * profile["compute"] * cost_scale


def simulate_trace_policy(
    slots: pd.DataFrame,
    policy: str,
    session_id: str,
    condition: str,
    base_overrides: Mapping[str, float] | None = None,
    weight_overrides: Mapping[str, float] | None = None,
    action_profile_overrides: Mapping[str, Mapping[str, float]] | None = None,
    suspicion: float = 0.05,
    rtt_uncertainty: float = 0.08,
    estimation_multipliers: Mapping[str, float] | None = None,
    collect_action_trace: bool = False,
) -> dict[str, Any]:
    """Run one policy on a fixed empirical slot sequence.

    The slot table is treated as immutable empirical workload input. No arrival,
    alert, or score-bucket sampling occurs inside this function.
    """

    required = {
        "slot",
        "flow_starts",
        "arrival_units",
        "alert_count",
        "low_count",
        "medium_count",
        "high_count",
        "critical_count",
        "low_positive_count",
        "medium_positive_count",
        "high_positive_count",
        "critical_positive_count",
    }
    missing = required - set(slots.columns)
    if missing:
        raise ValueError(f"Missing required trace-slot columns: {sorted(missing)}")
    if slots.empty:
        raise ValueError("Trace replay slots must not be empty")

    base = dict(DEFAULT_BASE)
    if base_overrides:
        base = deep_merge(base, base_overrides)
    if not base_overrides or "exposure_budget_total" not in base_overrides:
        base["exposure_budget_total"] = 3.6 * float(len(slots))

    weights = dict(DEFAULT_XAI_GATE_WEIGHTS)
    if weight_overrides:
        weights = deep_merge(weights, weight_overrides)
    config_for_profiles: dict[str, Any] = {}
    if action_profile_overrides:
        config_for_profiles["action_profile_overrides"] = action_profile_overrides
    action_profiles = action_profiles_for(config_for_profiles, {})
    estimation_enabled = estimation_multipliers is not None
    parsed_estimation_multipliers = estimation_multipliers_for(
        {"estimation_multipliers": estimation_multipliers or {}}
    )
    decision_action_profiles = (
        estimated_action_profiles(action_profiles, parsed_estimation_multipliers)
        if estimation_enabled
        else action_profiles
    )
    flags = ablation_flags("default")
    state = SimulationState()
    controller_state = SimulationState() if estimation_enabled else state
    action_trace: list[dict[str, dict[str, float]]] = []

    acc: dict[str, float] = {
        "arrivals": 0.0,
        "dropped": 0.0,
        "served": 0.0,
        "queue_sum": 0.0,
        "delay_sum": 0.0,
        "alerts": 0.0,
        "high_risk_alerts": 0.0,
        "explained_units": 0.0,
        "high_risk_explained_units": 0.0,
        "explanation_delay_sum": 0.0,
        "debt_sum": 0.0,
        "offload_count": 0.0,
        "audit_count": 0.0,
        "redaction_count": 0.0,
        "local_compute_units": 0.0,
        "budget_violation_slots": 0.0,
        "exposure_violation_slots": 0.0,
        "baseline_expected_alerts": 0.0,
    }
    action_totals = {name: 0.0 for name in ACTION_PROFILES}
    max_queue = 0.0
    max_debt = 0.0

    bucket_names = ["low", "medium", "high", "critical"]
    for _, row in slots.sort_values("slot", kind="mergesort").iterrows():
        state.slot_local_load = 0.0
        if controller_state is not state:
            controller_state.packet_queue = state.packet_queue
            controller_state.explanation_debt = (
                state.explanation_debt * float(parsed_estimation_multipliers["debt"])
            )
            controller_state.slot_local_load = 0.0
        arrivals = float(row["arrival_units"])
        bucket_counts = {bucket: int(row[f"{bucket}_count"]) for bucket in bucket_names}
        alert_count = int(row["alert_count"])
        if sum(bucket_counts.values()) != alert_count:
            raise ValueError("Trace slot alert_count does not equal bucket-count sum")

        evaluation_positive_probs: dict[str, float] = {}
        for bucket in bucket_names:
            count = bucket_counts[bucket]
            positive = float(row[f"{bucket}_positive_count"])
            if positive < -1e-12 or positive > count + 1e-12:
                raise ValueError(f"Invalid positive count for bucket {bucket}")
            evaluation_positive_probs[bucket] = positive / count if count > 0 else 0.0

        debt_risk_probs = dict(HIGH_RISK_PROBABILITY)

        signals = {
            "suspicion": float(suspicion),
            "rtt_uncertainty": float(rtt_uncertainty),
            "high_risk_probs": debt_risk_probs,
        }
        decision_signals = signals
        if estimation_enabled:
            decision_signals = dict(signals)
            decision_signals["rtt_uncertainty"] = (
                float(signals["rtt_uncertainty"])
                * float(parsed_estimation_multipliers["rtt"])
            )
        action_counts = allocate_actions(
            policy,
            bucket_counts,
            state,
            base,
            weights,
            flags,
            decision_signals,
            action_profiles,
            controller_state=controller_state if estimation_enabled else None,
            controller_action_profiles=decision_action_profiles if estimation_enabled else None,
        )
        if collect_action_trace:
            action_trace.append(
                {
                    bucket: {action: float(count) for action, count in sorted(actions.items())}
                    for bucket, actions in action_counts.items()
                }
            )
        for bucket, actions in action_counts.items():
            for action, count in actions.items():
                action_totals[action] = action_totals.get(action, 0.0) + float(count)
                _accumulate_trace_action_metrics(
                    acc,
                    bucket,
                    action,
                    float(count),
                    state,
                    base,
                    evaluation_positive_probs,
                    debt_risk_probs,
                    signals,
                    action_profiles,
                )

        service_rate = float(base["packet_service_rate"]) * float(base["service_capacity_multiplier"])
        service_rate -= float(base["packet_service_interference"]) * state.slot_local_load
        service_rate = max(1.0, service_rate)

        state.packet_queue += arrivals
        served = min(state.packet_queue, service_rate)
        state.packet_queue -= served
        if state.packet_queue > float(base["packet_buffer_capacity"]):
            overflow = state.packet_queue - float(base["packet_buffer_capacity"])
            acc["dropped"] += overflow
            state.packet_queue = float(base["packet_buffer_capacity"])

        spare_budget = max(0.0, float(base["local_explanation_budget"]) - state.slot_local_load)
        debt_service = min(
            state.explanation_debt,
            spare_budget
            * float(base["debt_service_rate"])
            / max(float(base["local_explanation_budget"]), 1e-9),
        )
        state.explanation_debt = max(0.0, state.explanation_debt - debt_service)

        acc["arrivals"] += arrivals
        acc["served"] += served
        acc["queue_sum"] += state.packet_queue
        acc["delay_sum"] += state.packet_queue / max(served, 1.0)
        acc["debt_sum"] += state.explanation_debt
        if state.slot_local_load > float(base["local_explanation_budget"]):
            acc["budget_violation_slots"] += 1.0
        if budget_exceeded(state.exposure_total, float(base["exposure_budget_total"])):
            acc["exposure_violation_slots"] += 1.0
        acc["baseline_expected_alerts"] += float(alert_count)
        max_queue = max(max_queue, state.packet_queue)
        max_debt = max(max_debt, state.explanation_debt)

        if state.packet_queue < -1e-9 or state.explanation_debt < -1e-9:
            raise AssertionError("Negative queue/debt state detected during trace replay")

    slot_count = int(len(slots))
    alerts_total = max(acc["alerts"], 1.0)
    high_total = max(acc["high_risk_alerts"], 1.0)
    arrivals_total = max(acc["arrivals"], 1.0)
    exposure_budget = max(float(base["exposure_budget_total"]), 1e-9)
    metrics: dict[str, Any] = {
        "stage": "temporal_replay",
        "variant": "default",
        "ablation": "default",
        "policy": policy,
        "regime": "timestamp_preserving_trace",
        "session_id": session_id,
        "condition": condition,
        "slots": slot_count,
        "packet_drop_rate": acc["dropped"] / arrivals_total,
        "mean_packet_delay": acc["delay_sum"] / slot_count,
        "mean_packet_queue": acc["queue_sum"] / slot_count,
        "explanation_coverage": acc["explained_units"] / alerts_total,
        "high_risk_explanation_coverage": acc["high_risk_explained_units"] / high_total,
        "mean_explanation_delay": acc["explanation_delay_sum"] / alerts_total,
        "mean_explanation_debt": acc["debt_sum"] / slot_count,
        "exposure_use": state.exposure_total / exposure_budget,
        "offload_rate": acc["offload_count"] / alerts_total,
        "audit_rate": acc["audit_count"] / alerts_total,
        "redaction_rate": acc["redaction_count"] / alerts_total,
        "local_compute_load": acc["local_compute_units"] / slot_count,
        "attacker_trigger_gain": 0.0,
        "budget_violation_rate": acc["budget_violation_slots"] / slot_count,
        "exposure_budget_violation_rate": acc["exposure_violation_slots"] / slot_count,
        "alerts_per_slot": acc["alerts"] / slot_count,
        "packets_per_slot": acc["arrivals"] / slot_count,
        "calibration_status": "ciciot2023_capture_disjoint_scores",
        "trace_total_flow_starts": float(slots["flow_starts"].sum()),
        "trace_total_alerts": float(slots["alert_count"].sum()),
        "trace_total_arrival_units": float(slots["arrival_units"].sum()),
        "action_count_total": float(sum(action_totals.values())),
        "final_explanation_debt": float(state.explanation_debt),
        "final_exposure": float(state.exposure_total),
        "max_packet_queue": float(max_queue),
        "max_explanation_debt": float(max_debt),
    }
    if estimation_enabled:
        metrics.update(
            {
                "estimate_compute_multiplier": float(parsed_estimation_multipliers["compute"]),
                "estimate_exposure_multiplier": float(parsed_estimation_multipliers["exposure"]),
                "estimate_debt_multiplier": float(parsed_estimation_multipliers["debt"]),
                "estimate_rtt_multiplier": float(parsed_estimation_multipliers["rtt"]),
                "estimated_exposure_use": controller_state.exposure_total / exposure_budget,
                "actual_exposure_overshoot": budget_overshoot(state.exposure_total, exposure_budget),
            }
        )
    if collect_action_trace:
        metrics["_action_trace"] = action_trace
    for action, count in sorted(action_totals.items()):
        metrics[f"action_count_{action}"] = float(count)

    for key in PRIMARY_METRICS + SECONDARY_METRICS + ["alerts_per_slot", "packets_per_slot"]:
        if not math.isfinite(float(metrics[key])):
            raise AssertionError(f"Non-finite trace metric {key} for {policy}/{session_id}/{condition}")
        if key != "attacker_trigger_gain" and float(metrics[key]) < -1e-10:
            raise AssertionError(f"Negative trace metric {key} for {policy}/{session_id}/{condition}")
    return metrics

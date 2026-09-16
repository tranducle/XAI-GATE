"""Public policy extensions for literature-grounded operational comparisons."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from . import core

_ORIGINAL_ALLOCATE_ACTIONS = core.allocate_actions
_INSTALLED = False


def _add(action_counts: Dict[str, Dict[str, float]], bucket: str, action: str, count: float, state: core.SimulationState, base: Mapping[str, float], profiles: Mapping[str, Mapping[str, float]]) -> None:
    if count <= 0:
        return
    action_counts[bucket][action] = action_counts[bucket].get(action, 0.0) + float(count)
    state.slot_local_load += float(count) * float(profiles[action]["compute"]) * float(base["explanation_cost_scale"])


def _selective_explanation(bucket_counts: Mapping[str, int], state: core.SimulationState, base: Mapping[str, float], profiles: Mapping[str, Mapping[str, float]]) -> Dict[str, Dict[str, float]]:
    """Adapt selective explanation as a deterministic service-level comparator.

    A configurable share of explanation-worthy alerts receives a coarse explanation;
    the remainder receives a full explanation. Low-risk alerts below the medium
    threshold are suppressed. This implements the selective-computation principle,
    not an exact reproduction of any cited source algorithm.
    """

    coarse_fraction = min(1.0, max(0.0, float(base.get("selective_coarse_fraction", 0.62))))
    medium_threshold = float(base.get("selective_medium_threshold", 0.42))
    result: Dict[str, Dict[str, float]] = {name: {} for name, _ in core.BUCKETS}
    for bucket, score in reversed(core.BUCKETS):
        count = float(bucket_counts.get(bucket, 0))
        if count <= 0:
            continue
        if score < medium_threshold:
            _add(result, bucket, "none", count, state, base, profiles)
            continue
        coarse = count * coarse_fraction
        _add(result, bucket, "coarse", coarse, state, base, profiles)
        _add(result, bucket, "full", count - coarse, state, base, profiles)
    return result


def _resource_aware(bucket_counts: Mapping[str, int], state: core.SimulationState, base: Mapping[str, float], signals: Mapping[str, Any], profiles: Mapping[str, Mapping[str, float]]) -> Dict[str, Dict[str, float]]:
    """Resource-aware local/offload operational comparator.

    Higher-risk alerts are served locally when projected local pressure is moderate;
    otherwise they are offloaded when RTT uncertainty is acceptable. Medium-risk
    alerts receive coarse explanations and low-risk alerts are suppressed.
    """

    result: Dict[str, Dict[str, float]] = {name: {} for name, _ in core.BUCKETS}
    high_threshold = float(base.get("resource_high_threshold", 0.68))
    medium_threshold = float(base.get("resource_medium_threshold", 0.42))
    pressure_threshold = float(base.get("resource_pressure_threshold", 0.78))
    rtt_threshold = float(base.get("resource_rtt_threshold", 0.50))
    local_budget = max(float(base["local_explanation_budget"]), 1e-9)
    for bucket, score in reversed(core.BUCKETS):
        count = float(bucket_counts.get(bucket, 0))
        if count <= 0:
            continue
        if score < medium_threshold:
            _add(result, bucket, "none", count, state, base, profiles)
            continue
        if score < high_threshold:
            _add(result, bucket, "coarse", count, state, base, profiles)
            continue
        projected = (state.slot_local_load + count * float(profiles["full"]["compute"])) / local_budget
        rtt_uncertainty = float(signals.get("rtt_uncertainty", 0.0))
        action = "offload" if projected > pressure_threshold and rtt_uncertainty <= rtt_threshold else "full"
        _add(result, bucket, action, count, state, base, profiles)
    return result


def extended_allocate_actions(policy: str, bucket_counts: Mapping[str, int], state: core.SimulationState, base: Mapping[str, float], weights: Mapping[str, float], flags: Mapping[str, bool], signals: Mapping[str, Any], action_profiles: Mapping[str, Mapping[str, float]]) -> Dict[str, Dict[str, float]]:
    if policy == "selective_explanations_adapted":
        return _selective_explanation(bucket_counts, state, base, action_profiles)
    if policy == "resource_aware_offload_adapted":
        return _resource_aware(bucket_counts, state, base, signals, action_profiles)
    return _ORIGINAL_ALLOCATE_ACTIONS(policy, bucket_counts, state, base, weights, flags, signals, action_profiles)


def install_policy_extensions() -> None:
    """Install the two public operational comparator policies into the core simulator."""
    global _INSTALLED
    if not _INSTALLED:
        core.allocate_actions = extended_allocate_actions
        _INSTALLED = True

"""Estimator-mismatch experiments with fixed realization profiles."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from . import core
from .extensions import install_policy_extensions


def _scaled_profiles(profiles: Mapping[str, Mapping[str, float]], compute: float, exposure: float) -> Dict[str, Dict[str, float]]:
    out = {action: dict(values) for action, values in profiles.items()}
    for values in out.values():
        values["compute"] = float(values["compute"]) * float(compute)
        values["exposure"] = float(values["exposure"]) * float(exposure)
    return out


def _signature(trace: Sequence[Mapping[str, Mapping[str, float]]]) -> list[dict[str, dict[str, float]]]:
    return [{bucket: {action: float(count) for action, count in counts.items()} for bucket, counts in slot.items()} for slot in trace]


def assignment_disagreement(left: Sequence[Mapping[str, Mapping[str, float]]], right: Sequence[Mapping[str, Mapping[str, float]]]) -> float:
    """Fraction of alert units assigned to different actions across aligned slot traces."""
    changed = total = 0.0
    for a_slot, b_slot in zip(left, right):
        for bucket in {*(a_slot.keys()), *(b_slot.keys())}:
            a = a_slot.get(bucket, {})
            b = b_slot.get(bucket, {})
            actions = set(a) | set(b)
            total += max(sum(float(v) for v in a.values()), sum(float(v) for v in b.values()))
            changed += 0.5 * sum(abs(float(a.get(action, 0.0)) - float(b.get(action, 0.0))) for action in actions)
    return changed / max(total, 1.0)


def simulate_estimator_variant(config: Mapping[str, Any], *, config_dir, seed: int, regime: str, variant: Mapping[str, Any]) -> tuple[Dict[str, Any], list[dict[str, dict[str, float]]]]:
    """Run one XAI-Gate estimator variant while evaluating a fixed realization profile.

    Controller-side compute, exposure, debt, and RTT estimates are perturbed only for
    action selection. Service accumulation uses the unperturbed realization profile.
    The random workload is fixed across variants by using one shared simulation
    variant identifier.
    """

    install_policy_extensions()
    calibration = core.load_calibration_profile(config, config_dir)
    multipliers = variant.get("estimation_multipliers", {})
    compute_mult = float(multipliers.get("compute", 1.0))
    exposure_mult = float(multipliers.get("exposure", 1.0))
    debt_mult = float(multipliers.get("debt", 1.0))
    rtt_mult = float(multipliers.get("rtt", 1.0))
    actual_profiles = core.action_profiles_for(config, {"name": "shared_workload", "ablation": "default"})
    estimated_profiles = _scaled_profiles(actual_profiles, compute_mult, exposure_mult)
    original_allocate = core.allocate_actions
    estimated_exposure_total = 0.0
    trace: list[dict[str, dict[str, float]]] = []

    def estimator_allocate(policy, bucket_counts, state, base, weights, flags, signals, action_profiles):
        nonlocal estimated_exposure_total
        actual_debt = state.explanation_debt
        actual_exposure = state.exposure_total
        actual_local_load = state.slot_local_load
        state.explanation_debt = actual_debt * debt_mult
        state.exposure_total = estimated_exposure_total
        estimated_signals = dict(signals)
        estimated_signals["rtt_uncertainty"] = float(signals.get("rtt_uncertainty", 0.0)) * rtt_mult
        state.slot_local_load = 0.0
        try:
            counts = original_allocate(policy, bucket_counts, state, base, weights, flags, estimated_signals, estimated_profiles)
            estimated_exposure_total += sum(float(count) * float(estimated_profiles[action]["exposure"]) for actions in counts.values() for action, count in actions.items())
        finally:
            state.explanation_debt = actual_debt
            state.exposure_total = actual_exposure
        actual_load = sum(float(count) * float(actual_profiles[action]["compute"]) * float(base["explanation_cost_scale"]) for actions in counts.values() for action, count in actions.items())
        state.slot_local_load = actual_local_load + actual_load
        trace.append(_signature([counts])[0])
        return counts

    core.allocate_actions = estimator_allocate
    shared_variant = {"name": "shared_estimator_workload", "ablation": "default"}
    try:
        row = core.simulate_run(config, int(seed), "xai_gate", str(regime), shared_variant, calibration)
    finally:
        core.allocate_actions = original_allocate
    row["stage"] = "estimator_mismatch"
    row["variant"] = str(variant["name"])
    row["estimated_exposure_use"] = estimated_exposure_total / max(float(core.deep_merge(core.DEFAULT_BASE, config.get("base", {}))["exposure_budget_total"]), 1e-9)
    row["actual_minus_estimated_exposure_use"] = float(row["exposure_use"]) - float(row["estimated_exposure_use"])
    row["realization_profile_fixed"] = True
    row["estimate_compute_multiplier"] = compute_mult
    row["estimate_exposure_multiplier"] = exposure_mult
    row["estimate_debt_multiplier"] = debt_mult
    row["estimate_rtt_multiplier"] = rtt_mult
    return row, trace

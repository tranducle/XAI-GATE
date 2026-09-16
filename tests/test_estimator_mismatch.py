from __future__ import annotations

import inspect

import pandas as pd

import xai_surfacebench.core as core_module
from xai_surfacebench.core import CalibrationProfile, PRIMARY_METRICS, SECONDARY_METRICS, simulate_run
from xai_surfacebench.temporal_replay import simulate_trace_policy
from xai_surfacebench.validation import metric_close


def _base_config() -> dict:
    return {
        "name": "estimator_mismatch_unit",
        "slots": 300,
        "policies": ["xai_gate"],
        "regimes": ["adversarial_explanation_flood"],
        "seeds": [7],
        "base": {
            "packet_arrival_rate": 45.0,
            "packet_service_rate": 52.0,
            "packet_buffer_capacity": 240.0,
            "alert_probability": 0.15,
            "local_explanation_budget": 18.0,
            "exposure_budget_total": 1200.0,
            "threshold": 0.72,
        },
    }


def test_workload_seed_group_keeps_stochastic_workload_identical_across_variants() -> None:
    config = _base_config()
    calibration = CalibrationProfile()
    nominal = simulate_run(
        config,
        seed=7,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "nominal",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
        },
        calibration=calibration,
    )
    biased = simulate_run(
        config,
        seed=7,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "joint_optimistic",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 0.75, "exposure": 0.75, "debt": 0.75, "rtt": 0.75},
        },
        calibration=calibration,
    )

    assert nominal["packets_per_slot"] == biased["packets_per_slot"]
    assert nominal["alerts_per_slot"] == biased["alerts_per_slot"]


def test_estimation_bias_changes_policy_outcome_on_same_stochastic_workload() -> None:
    config = _base_config()
    calibration = CalibrationProfile()
    nominal = simulate_run(
        config,
        seed=9,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "shared-name",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
        },
        calibration=calibration,
    )
    optimistic = simulate_run(
        config,
        seed=9,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "shared-name",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 0.5, "exposure": 0.5, "debt": 0.5, "rtt": 0.5},
        },
        calibration=calibration,
    )

    assert nominal["packets_per_slot"] == optimistic["packets_per_slot"]
    assert nominal["alerts_per_slot"] == optimistic["alerts_per_slot"]
    changed = any(
        nominal[key] != optimistic[key]
        for key in [
            "high_risk_explanation_coverage",
            "mean_explanation_debt",
            "exposure_use",
            "packet_drop_rate",
            "offload_rate",
        ]
    )
    assert changed, "Estimator bias should change at least one policy/service outcome on an identical workload"


def test_temporal_replay_supports_estimation_multipliers_and_true_realization_accounting() -> None:
    assert "estimation_multipliers" in inspect.signature(simulate_trace_policy).parameters

    slots = pd.DataFrame(
        {
            "slot": list(range(4)),
            "flow_starts": [20, 20, 20, 20],
            "arrival_units": [45.0, 45.0, 45.0, 45.0],
            "alert_count": [20, 20, 20, 20],
            "low_count": [0, 0, 0, 0],
            "medium_count": [0, 0, 0, 0],
            "high_count": [0, 0, 0, 0],
            "critical_count": [20, 20, 20, 20],
            "low_positive_count": [0.0] * 4,
            "medium_positive_count": [0.0] * 4,
            "high_positive_count": [0.0] * 4,
            "critical_positive_count": [20.0] * 4,
        }
    )

    nominal = simulate_trace_policy(
        slots,
        policy="xai_gate",
        session_id="estimator-mismatch-cap",
        condition="chronological",
        base_overrides={"exposure_budget_total": 8.0},
        estimation_multipliers={"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
    )
    optimistic = simulate_trace_policy(
        slots,
        policy="xai_gate",
        session_id="estimator-mismatch-cap",
        condition="chronological",
        base_overrides={"exposure_budget_total": 8.0},
        estimation_multipliers={"compute": 1.0, "exposure": 0.5, "debt": 1.0, "rtt": 1.0},
    )

    assert "estimated_exposure_use" in optimistic
    assert nominal["exposure_use"] <= 1.0 + 1e-12
    assert nominal["exposure_budget_violation_rate"] == 0.0
    assert optimistic["estimated_exposure_use"] <= 1.0 + 1e-12
    assert optimistic["exposure_use"] > 1.0
    assert optimistic["exposure_budget_violation_rate"] > 0.0


def test_nominal_dual_profile_reproduces_legacy_stochastic_metrics_exactly() -> None:
    config = _base_config()
    calibration = CalibrationProfile()
    legacy = simulate_run(
        config,
        seed=11,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={"name": "default"},
        calibration=calibration,
    )
    nominal = simulate_run(
        config,
        seed=11,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "default",
            "estimation_multipliers": {"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
        },
        calibration=calibration,
    )

    assert legacy["workload_hash"] == nominal["workload_hash"]
    for metric in PRIMARY_METRICS + SECONDARY_METRICS + ["alerts_per_slot", "packets_per_slot"]:
        assert legacy[metric] == nominal[metric], metric


def test_nominal_dual_profile_reproduces_legacy_temporal_metrics_exactly() -> None:
    slots = pd.DataFrame(
        {
            "slot": [0, 1, 2, 3],
            "flow_starts": [8, 5, 12, 4],
            "arrival_units": [36.0, 22.5, 54.0, 18.0],
            "alert_count": [4, 3, 7, 2],
            "low_count": [0, 0, 0, 0],
            "medium_count": [1, 1, 1, 1],
            "high_count": [2, 1, 3, 0],
            "critical_count": [1, 1, 3, 1],
            "low_positive_count": [0.0] * 4,
            "medium_positive_count": [0.0, 1.0, 1.0, 0.0],
            "high_positive_count": [2.0, 1.0, 2.0, 0.0],
            "critical_positive_count": [1.0, 1.0, 3.0, 1.0],
        }
    )
    legacy = simulate_trace_policy(
        slots,
        policy="xai_gate",
        session_id="nominal-regression",
        condition="chronological",
    )
    nominal = simulate_trace_policy(
        slots,
        policy="xai_gate",
        session_id="nominal-regression",
        condition="chronological",
        estimation_multipliers={"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
    )

    for metric in PRIMARY_METRICS + SECONDARY_METRICS + [
        "alerts_per_slot",
        "packets_per_slot",
        "final_explanation_debt",
        "final_exposure",
        "max_packet_queue",
        "max_explanation_debt",
    ]:
        assert legacy[metric] == nominal[metric], metric
    for action in ["none", "coarse", "full", "offload", "audit", "redact", "delay"]:
        assert legacy[f"action_count_{action}"] == nominal[f"action_count_{action}"]


def test_optional_action_trace_supports_exact_assignment_disagreement_diagnostic() -> None:
    assert "collect_action_trace" in inspect.signature(simulate_run).parameters
    assert "collect_action_trace" in inspect.signature(simulate_trace_policy).parameters
    config = _base_config()
    calibration = CalibrationProfile()
    nominal = simulate_run(
        config,
        seed=13,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "nominal",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 1.0, "exposure": 1.0, "debt": 1.0, "rtt": 1.0},
        },
        calibration=calibration,
        collect_action_trace=True,
    )
    optimistic = simulate_run(
        config,
        seed=13,
        policy="xai_gate",
        regime="adversarial_explanation_flood",
        variant={
            "name": "optimistic",
            "workload_seed_group": "shared-estimator-mismatch",
            "estimation_multipliers": {"compute": 0.5, "exposure": 0.5, "debt": 0.5, "rtt": 0.5},
        },
        calibration=calibration,
        collect_action_trace=True,
    )

    assert len(nominal["_action_trace"]) == config["slots"]
    assert len(optimistic["_action_trace"]) == config["slots"]
    assert nominal["_action_trace"] != optimistic["_action_trace"]


def test_exposure_budget_comparison_ignores_machine_precision_overshoot() -> None:
    assert hasattr(core_module, "budget_exceeded")
    assert not core_module.budget_exceeded(18000.0 + 3.7e-12, 18000.0)
    assert core_module.budget_exceeded(18000.0 + 1e-4, 18000.0)


def test_metric_comparator_tolerates_csv_roundtrip_only() -> None:
    assert metric_close(186704.77816129057, 186704.77816129054)
    assert not metric_close(186704.77816129057, 186704.7781600)

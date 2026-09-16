from __future__ import annotations

import pandas as pd

from xai_surfacebench.temporal_replay import (
    build_slot_table,
    simulate_trace_policy,
    shuffle_slot_order,
)


def test_build_slot_table_preserves_empty_seconds_and_alert_buckets() -> None:
    frame = pd.DataFrame(
        {
            "ts_start": [100.1, 100.9, 102.2],
            "score": [0.91, 0.20, 0.61],
            "true_label": [1, 0, 1],
        }
    )

    slots = build_slot_table(frame, reference_nonzero_median=2.0)

    assert list(slots["slot"]) == [0, 1, 2]
    assert list(slots["flow_starts"]) == [2, 0, 1]
    assert slots.loc[0, "critical_count"] == 1
    assert slots.loc[0, "alert_count"] == 1
    assert slots.loc[1, "alert_count"] == 0
    assert slots.loc[2, "medium_count"] == 1
    assert slots.loc[2, "alert_count"] == 1
    assert slots["flow_starts"].sum() == len(frame)
    assert slots.loc[0, "arrival_units"] == 45.0
    assert slots.loc[2, "arrival_units"] == 22.5


def test_shuffle_slot_order_preserves_marginals_but_changes_sequence() -> None:
    slots = pd.DataFrame(
        {
            "slot": list(range(8)),
            "flow_starts": [1, 2, 3, 4, 5, 6, 7, 8],
            "arrival_units": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "alert_count": [0, 1, 0, 2, 0, 3, 0, 4],
            "low_count": [0, 1, 0, 0, 0, 0, 0, 0],
            "medium_count": [0, 0, 0, 2, 0, 0, 0, 0],
            "high_count": [0, 0, 0, 0, 0, 3, 0, 0],
            "critical_count": [0, 0, 0, 0, 0, 0, 0, 4],
        }
    )

    shuffled = shuffle_slot_order(slots, seed=20260914)

    assert list(shuffled["slot"]) == list(range(8))
    assert shuffled["flow_starts"].sum() == slots["flow_starts"].sum()
    assert shuffled["arrival_units"].sum() == slots["arrival_units"].sum()
    assert shuffled["alert_count"].sum() == slots["alert_count"].sum()
    assert sorted(shuffled["flow_starts"].tolist()) == sorted(slots["flow_starts"].tolist())
    assert shuffled["flow_starts"].tolist() != slots["flow_starts"].tolist()


def test_simulate_trace_policy_uses_empirical_slot_workload() -> None:
    slots = pd.DataFrame(
        {
            "slot": [0, 1, 2],
            "flow_starts": [4, 0, 2],
            "arrival_units": [36.0, 0.0, 18.0],
            "alert_count": [2, 0, 1],
            "low_count": [0, 0, 0],
            "medium_count": [0, 0, 0],
            "high_count": [1, 0, 0],
            "critical_count": [1, 0, 1],
            "low_positive_count": [0.0, 0.0, 0.0],
            "medium_positive_count": [0.0, 0.0, 0.0],
            "high_positive_count": [1.0, 0.0, 0.0],
            "critical_positive_count": [1.0, 0.0, 1.0],
        }
    )

    result = simulate_trace_policy(
        slots,
        policy="always_explain",
        session_id="unit-session",
        condition="chronological",
    )

    assert result["slots"] == 3
    assert result["packets_per_slot"] == 18.0
    assert result["alerts_per_slot"] == 1.0
    assert result["explanation_coverage"] == 1.0
    assert result["high_risk_explanation_coverage"] == 1.0
    assert result["trace_total_flow_starts"] == 6.0
    assert result["trace_total_alerts"] == 3.0
    assert result["action_count_total"] == 3.0


def test_simulate_trace_policy_xai_gate_hard_cap_limits_exposure() -> None:
    slots = pd.DataFrame(
        {
            "slot": list(range(4)),
            "flow_starts": [10, 10, 10, 10],
            "arrival_units": [45.0, 45.0, 45.0, 45.0],
            "alert_count": [10, 10, 10, 10],
            "low_count": [0, 0, 0, 0],
            "medium_count": [0, 0, 0, 0],
            "high_count": [0, 0, 0, 0],
            "critical_count": [10, 10, 10, 10],
            "low_positive_count": [0.0, 0.0, 0.0, 0.0],
            "medium_positive_count": [0.0, 0.0, 0.0, 0.0],
            "high_positive_count": [0.0, 0.0, 0.0, 0.0],
            "critical_positive_count": [10.0, 10.0, 10.0, 10.0],
        }
    )

    result = simulate_trace_policy(
        slots,
        policy="xai_gate",
        session_id="cap-session",
        condition="chronological",
        base_overrides={"exposure_budget_total": 5.0},
    )

    assert result["exposure_use"] <= 1.0 + 1e-12
    assert result["exposure_budget_violation_rate"] == 0.0
    assert result["action_count_total"] == 40.0


def test_true_labels_affect_evaluation_only_not_policy_state() -> None:
    common = {
        "slot": list(range(6)),
        "flow_starts": [12, 12, 12, 12, 12, 12],
        "arrival_units": [45.0, 45.0, 45.0, 45.0, 45.0, 45.0],
        "alert_count": [10, 10, 10, 10, 10, 10],
        "low_count": [0, 0, 0, 0, 0, 0],
        "medium_count": [0, 0, 0, 0, 0, 0],
        "high_count": [10, 10, 10, 10, 10, 10],
        "critical_count": [0, 0, 0, 0, 0, 0],
        "low_positive_count": [0.0] * 6,
        "medium_positive_count": [0.0] * 6,
        "critical_positive_count": [0.0] * 6,
    }
    no_positive = pd.DataFrame({**common, "high_positive_count": [0.0] * 6})
    all_positive = pd.DataFrame({**common, "high_positive_count": [10.0] * 6})

    no_positive_result = simulate_trace_policy(
        no_positive,
        policy="xai_gate",
        session_id="label-isolation",
        condition="chronological",
    )
    all_positive_result = simulate_trace_policy(
        all_positive,
        policy="xai_gate",
        session_id="label-isolation",
        condition="chronological",
    )

    assert no_positive_result["high_risk_explanation_coverage"] == 0.0
    assert all_positive_result["high_risk_explanation_coverage"] > 0.0
    for metric in [
        "mean_explanation_debt",
        "final_explanation_debt",
        "exposure_use",
        "packet_drop_rate",
        "mean_packet_delay",
        "budget_violation_rate",
    ]:
        assert no_positive_result[metric] == all_positive_result[metric]
    for action in ["none", "coarse", "full", "offload", "audit", "redact", "delay"]:
        assert no_positive_result[f"action_count_{action}"] == all_positive_result[f"action_count_{action}"]

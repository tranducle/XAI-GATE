from xai_surfacebench import core
from xai_surfacebench.extensions import install_policy_extensions
from xai_surfacebench.hardware_benchmark import capacity_overlay
from xai_surfacebench.temporal_replay import shuffled_slots, slot_bucket_counts
from xai_surfacebench.validation import metric_close
import pandas as pd


def test_comparator_extensions_allocate_all_alerts():
    install_policy_extensions()
    for policy in ["selective_explanations_adapted","resource_aware_offload_adapted"]:
        state = core.SimulationState()
        counts = core.allocate_actions(policy, {"low":2,"medium":3,"high":4,"critical":1}, state, core.DEFAULT_BASE, core.DEFAULT_XAI_GATE_WEIGHTS, core.ablation_flags("default"), {"rtt_uncertainty":0.1,"suspicion":0.2}, core.ACTION_PROFILES)
        assert sum(sum(actions.values()) for actions in counts.values()) == 10


def test_shuffled_slots_preserves_rows():
    frame = pd.DataFrame({"packet_arrivals":[1,2,3],"low_count":[1,0,0],"medium_count":[0,2,0],"high_count":[0,0,3],"critical_count":[0,0,0]})
    shuffled = shuffled_slots(frame, 7)
    assert sorted(map(tuple, frame.to_numpy())) == sorted(map(tuple, shuffled.to_numpy()))


def test_bucket_schema_and_metric_tolerance():
    counts = slot_bucket_counts({"low_count":1,"medium_count":2,"high_count":3,"critical_count":4})
    assert counts == {"low":1,"medium":2,"high":3,"critical":4}
    assert metric_close(1.0, 1.0 + 1e-12)


def test_capacity_overlay_detects_overload():
    trace = [{"high":{"full":2.0}}]
    result = capacity_overlay(trace, {"full":600.0,"none":0.0,"delay":0.0,"coarse":0.0,"offload":0.0,"audit":0.0,"redact":0.0})
    assert result["overload_slots"] == 1
    assert result["max_work_backlog_ms"] == 200.0

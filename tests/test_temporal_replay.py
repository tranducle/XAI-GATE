import pandas as pd
from xai_surfacebench.temporal_replay import shuffled_slots, simulate_trace_policy


def frame():
    return pd.DataFrame({"packet_arrivals":[45,60,30],"low_count":[3,2,1],"medium_count":[2,3,1],"high_count":[1,2,2],"critical_count":[0,1,1]})


def test_shuffle_preserves_slot_multiset():
    left = sorted(map(tuple, frame().to_numpy())); right = sorted(map(tuple, shuffled_slots(frame(), 11).to_numpy())); assert left == right


def test_temporal_replay_returns_service_metrics():
    result = simulate_trace_policy(frame(), policy="xai_gate", session_id="unit")
    assert result["slots"] == 3
    assert 0.0 <= result["packet_drop_rate"] <= 1.0
    assert result["mean_explanation_debt"] >= 0.0

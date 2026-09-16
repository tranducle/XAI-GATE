from __future__ import annotations

import pandas as pd

from xai_surfacebench.hardware_benchmark import (
    FEATURES,
    build_measured_compute_profile,
    slot_demand_ms,
    stable_record_id,
    select_deterministic_rows,
)


def test_feature_contract_matches_temporal_replay_predictors() -> None:
    assert FEATURES == (
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


def test_stable_record_id_is_deterministic_and_source_specific() -> None:
    a = stable_record_id("Recon-PortScan/Recon-PortScan.pcap", 123)
    b = stable_record_id("Recon-PortScan/Recon-PortScan.pcap", 123)
    c = stable_record_id("Recon-PingSweep/Recon-PingSweep.pcap", 123)
    assert a == b
    assert a != c
    assert len(a) == 16


def test_select_deterministic_rows_is_repeatable_and_keeps_only_features_plus_id() -> None:
    frame = pd.DataFrame(
        {
            "protocol": [6, 17, 6, 17, 6],
            "src_port": [1, 2, 3, 4, 5],
            "dst_port": [11, 12, 13, 14, 15],
            "packets": [1, 2, 3, 4, 5],
            "packets_rev": [0, 1, 0, 1, 0],
            "bytes": [100, 200, 300, 400, 500],
            "bytes_rev": [0, 20, 0, 40, 0],
            "tcp_flags": [2, 2, 18, 2, 18],
            "tcp_flags_rev": [0, 16, 16, 0, 16],
            "duration": [0.1, 0.2, 0.3, 0.4, 0.5],
            "ts_start": [10, 11, 12, 13, 14],
            "label_class": ["x"] * 5,
        }
    )
    first = select_deterministic_rows(frame, source_file="capture-a.pcap", count=3)
    second = select_deterministic_rows(frame, source_file="capture-a.pcap", count=3)
    assert first.equals(second)
    assert list(first.columns) == ["record_id", "source_file", "row_index", *FEATURES]
    assert len(first) == 3
    assert "ts_start" not in first.columns
    assert "label_class" not in first.columns


def test_measured_profile_changes_only_compute_and_normalizes_full() -> None:
    medians = {
        "none": 0.01,
        "coarse": 2.0,
        "full_lime": 20.0,
        "offload": 1.0,
        "audit": 0.5,
        "redact": 1.5,
        "delay": 0.01,
    }
    profile = build_measured_compute_profile(medians, full_measurement="full_lime")
    assert profile["full"]["compute"] == 1.0
    assert profile["coarse"]["compute"] == 0.1
    assert profile["offload"]["compute"] == 0.05
    assert profile["audit"]["compute"] == 0.025
    assert profile["redact"]["compute"] == 0.075
    assert profile["none"]["compute"] == 0.0
    assert profile["delay"]["compute"] == 0.0
    for action, values in profile.items():
        assert set(values) == {"compute"}, action


def test_slot_demand_ms_uses_absolute_p95_measurements() -> None:
    counts = {"full": 2.0, "coarse": 3.0, "audit": 1.0, "none": 5.0}
    p95 = {"full": 100.0, "coarse": 10.0, "audit": 4.0, "none": 0.2}
    assert slot_demand_ms(counts, p95) == 235.0


def test_redaction_masks_only_requested_indices() -> None:
    from xai_surfacebench.hardware_benchmark import redact_vector

    row = [1.0, 2.0, 3.0, 4.0]
    assert redact_vector(row, [1, 3]) == [1.0, 0.0, 3.0, 0.0]


def test_offload_payload_contains_only_sanitized_benchmark_fields() -> None:
    import gzip
    import json

    from xai_surfacebench.hardware_benchmark import build_offload_payload

    payload = build_offload_payload([1.234567, 2.0], score=0.8123456)
    parsed = json.loads(gzip.decompress(payload).decode("utf-8"))
    assert set(parsed) == {"score", "features", "request", "explainer"}
    assert parsed["features"] == [1.23457, 2.0]
    assert parsed["score"] == 0.812346
    assert parsed["request"] == "remote_explanation"


def test_capacity_overlay_tracks_overload_and_backlog() -> None:
    from xai_surfacebench.hardware_benchmark import capacity_overlay

    trace = [
        {"critical": {"full": 3.0}},
        {"high": {"coarse": 2.0}},
        {"medium": {"full": 1.0, "audit": 1.0}},
    ]
    p95 = {"full": 400.0, "coarse": 100.0, "audit": 50.0}
    out = capacity_overlay(trace, p95, capacity_ms=1000.0)
    assert out["slots"] == 3
    assert out["overload_slots"] == 1
    assert out["overload_slot_fraction"] == 1 / 3
    assert out["max_consecutive_overload_slots"] == 1
    assert out["final_work_backlog_ms"] == 0.0
    assert out["max_work_backlog_ms"] == 200.0
    assert out["total_demand_ms"] == 1850.0

import pandas as pd
from xai_surfacebench.hardware_benchmark import FEATURES, capacity_overlay, select_deterministic_rows


def test_deterministic_row_selection():
    frame = pd.DataFrame({name:[float(i) for i in range(10)] for name in FEATURES})
    first = select_deterministic_rows(frame, source_file="capture.parquet", count=4)
    second = select_deterministic_rows(frame, source_file="capture.parquet", count=4)
    assert first.equals(second)


def test_capacity_overlay():
    result = capacity_overlay([{"high":{"full":2.0}}], {"full":600.0,"none":0.0,"coarse":0.0,"offload":0.0,"audit":0.0,"redact":0.0,"delay":0.0})
    assert result["overload_slots"] == 1
    assert result["max_work_backlog_ms"] == 200.0

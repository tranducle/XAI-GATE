"""Public reproducibility validation helpers."""

from __future__ import annotations

import math


def metric_close(left: float, right: float) -> bool:
    """Compare deterministic reruns while tolerating decimal CSV round-trip noise only."""
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-10)

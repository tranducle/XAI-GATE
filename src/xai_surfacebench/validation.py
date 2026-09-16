"""Small public validation helpers used by reproducibility checks."""

from __future__ import annotations

import math


def metric_close(left: float, right: float) -> bool:
    """Allow only decimal round-trip noise in deterministic metric comparisons."""
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-10)

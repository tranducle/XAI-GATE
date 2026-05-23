"""XAI-SurfaceBench: deterministic no-training simulator for explanation-surface governance."""

from .core import (
    ABLATIONS,
    MANDATORY_POLICIES,
    MANDATORY_REGIMES,
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    run_experiment,
    stable_seed,
    write_outputs,
)

__all__ = [
    "ABLATIONS",
    "MANDATORY_POLICIES",
    "MANDATORY_REGIMES",
    "PRIMARY_METRICS",
    "SECONDARY_METRICS",
    "run_experiment",
    "stable_seed",
    "write_outputs",
]

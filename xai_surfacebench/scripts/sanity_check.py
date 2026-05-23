#!/usr/bin/env python3
"""Stage 0 deterministic sanity check for XAI-SurfaceBench."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xai_surfacebench.core import (  # noqa: E402
    MANDATORY_POLICIES,
    MANDATORY_REGIMES,
    PRIMARY_METRICS,
    SECONDARY_METRICS,
    load_json,
    run_experiment,
    validate_required_coverage,
    write_outputs,
)


def normalize(rows):
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def assert_valid(rows):
    required_metrics = PRIMARY_METRICS + SECONDARY_METRICS
    for row in rows:
        for metric in required_metrics:
            value = float(row[metric])
            if not math.isfinite(value):
                raise AssertionError(f"non-finite {metric}: {row}")
            if metric != "attacker_trigger_gain" and value < -1e-12:
                raise AssertionError(f"negative {metric}: {row}")
        if row["policy"] not in MANDATORY_POLICIES:
            raise AssertionError(f"unknown policy {row['policy']}")
        if row["regime"] not in MANDATORY_REGIMES:
            raise AssertionError(f"unknown regime {row['regime']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=ROOT / "configs" / "sanity.json", type=Path)
    parser.add_argument("--output-root", default=ROOT, type=Path)
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_json(config_path)
    validate_required_coverage(config, require_all=True)
    first = run_experiment(config, config_path.parent)
    second = run_experiment(config, config_path.parent)
    assert_valid(first)
    assert_valid(second)
    if normalize(first) != normalize(second):
        raise AssertionError("deterministic rerun mismatch")
    paths = write_outputs(first, config, args.output_root.resolve())
    print(f"sanity_runs={len(first)}")
    print("deterministic_rerun=pass")
    for label, path in paths.items():
        print(f"{label}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

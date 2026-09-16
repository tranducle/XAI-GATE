#!/usr/bin/env python3
"""Run a short deterministic XAI-SurfaceBench reproducibility check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.core import load_json, run_experiment
from xai_surfacebench.extensions import install_policy_extensions


def main() -> int:
    install_policy_extensions()
    path = ROOT / "configs" / "sanity_check.json"
    config = load_json(path)
    first = run_experiment(config, path.parent)
    second = run_experiment(config, path.parent)
    left = json.dumps(first, sort_keys=True, separators=(",", ":"))
    right = json.dumps(second, sort_keys=True, separators=(",", ":"))
    if left != right:
        raise SystemExit("deterministic rerun mismatch")
    print(f"sanity_runs={len(first)}")
    print("deterministic_rerun=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

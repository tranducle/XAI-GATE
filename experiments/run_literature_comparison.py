#!/usr/bin/env python3
"""Run literature-grounded operational comparator experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.core import load_json, run_experiment, write_outputs
from xai_surfacebench.extensions import install_policy_extensions

CONFIGS = {
    "main": "literature_comparison_main.json",
    "tuned": "literature_comparison_tuned.json",
    "unsw": "literature_comparison_unsw_deduplicated.json",
    "toniot": "literature_comparison_toniot.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=sorted(CONFIGS), nargs="?", default="main")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    install_policy_extensions()
    path = ROOT / "configs" / CONFIGS[args.mode]
    config = load_json(path)
    rows = run_experiment(config, path.parent)
    write_outputs(rows, config, args.output_root.resolve())
    print(f"mode={args.mode} runs={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

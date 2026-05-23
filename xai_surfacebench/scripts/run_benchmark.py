#!/usr/bin/env python3
"""Run an XAI-SurfaceBench experiment config and write CSV/JSON/TeX/log artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xai_surfacebench.core import load_json, run_experiment, write_outputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Path to a JSON experiment config.")
    parser.add_argument("--output-root", default=ROOT, type=Path, help="Package output root.")
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_json(config_path)
    results = run_experiment(config, config_path.parent)
    paths = write_outputs(results, config, args.output_root.resolve())
    print(f"runs={len(results)}")
    for label, path in paths.items():
        print(f"{label}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

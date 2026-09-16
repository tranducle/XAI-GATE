#!/usr/bin/env python3
"""Run an XAI-SurfaceBench JSON configuration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.core import load_json, run_experiment, write_outputs
from xai_surfacebench.extensions import install_policy_extensions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    install_policy_extensions()
    config_path = args.config.resolve()
    config = load_json(config_path)
    rows = run_experiment(config, config_path.parent)
    paths = write_outputs(rows, config, args.output_root.resolve())
    print(f"runs={len(rows)}")
    for label, path in paths.items():
        print(f"{label}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

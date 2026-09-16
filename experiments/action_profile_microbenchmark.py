#!/usr/bin/env python3
"""Dependency-light microbenchmark for XAI-SurfaceBench action primitives."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import time
from pathlib import Path

ACTIONS = ["none","coarse","full","offload","audit","redact","delay"]


def vectors(count: int, width: int) -> list[list[float]]:
    rng = random.Random(1207)
    return [[rng.uniform(-1.0, 1.0) for _ in range(width)] for _ in range(count)]


def execute(action: str, vector: list[float]) -> None:
    if action in {"none","delay"}: return
    if action == "coarse": sorted(enumerate(vector), key=lambda item: abs(item[1]), reverse=True)[:6]; return
    if action == "full":
        base = sum((index + 1) * value for index, value in enumerate(vector))
        for rep in range(48):
            sum((index + 1) * value * (1.0 - ((index + rep) % 7) * 0.015) for index, value in enumerate(vector)) - base
        return
    payload = json.dumps(vector, separators=(",", ":")).encode("utf-8")
    if action == "offload": len(payload); return
    if action == "audit": hashlib.sha256(payload).digest(); return
    if action == "redact":
        copy = list(vector)
        for index, _ in sorted(enumerate(copy), key=lambda item: abs(item[1]), reverse=True)[:6]: copy[index] = 0.0
        return
    raise ValueError(action)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("results/action_profile_microbenchmark.json"))
    args = parser.parse_args()
    sample = vectors(args.records, args.width)
    report = {}
    for action in ACTIONS:
        observations = []
        for vector in sample:
            start = time.perf_counter_ns(); execute(action, vector); observations.append((time.perf_counter_ns() - start) / 1e6)
        ordered = sorted(observations)
        report[action] = {"median_ms":statistics.median(ordered),"p95_ms":ordered[min(len(ordered)-1, int(0.95*len(ordered)))],"observations":len(ordered)}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())

#!/usr/bin/env python3
"""Run local proxy microbenchmarks for XAI-SurfaceBench action profiles."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xai_surfacebench.core import ACTION_PROFILES  # noqa: E402


def make_vectors(count: int, width: int) -> List[List[float]]:
    rng = random.Random(1207)
    return [[rng.uniform(-1.0, 1.0) for _ in range(width)] for _ in range(count)]


def action_none(vector: List[float]) -> int:
    return 0


def action_coarse(vector: List[float]) -> int:
    ranked = sorted(enumerate(vector), key=lambda item: abs(item[1]), reverse=True)[:6]
    return sum(index for index, _ in ranked)


def action_full(vector: List[float]) -> int:
    total = 0.0
    base = sum((idx + 1) * value for idx, value in enumerate(vector))
    for rep in range(48):
        subtotal = 0.0
        for idx, value in enumerate(vector):
            perturbed = value * (1.0 - ((idx + rep) % 7) * 0.015)
            subtotal += (idx + 1) * perturbed
        total += abs(base - subtotal)
    return int(total * 1000.0) % 100000


def action_redact(vector: List[float]) -> int:
    ranked = sorted(enumerate(vector), key=lambda item: abs(item[1]), reverse=True)
    redacted = [(idx, 0.0 if rank < 8 else value) for rank, (idx, value) in enumerate(ranked)]
    return int(sum(idx * abs(value) for idx, value in redacted) * 1000.0) % 100000


def action_audit(vector: List[float]) -> int:
    payload = json.dumps(
        {
            "score": sum(abs(value) for value in vector) / max(len(vector), 1),
            "top_features": sorted(range(len(vector)), key=lambda idx: abs(vector[idx]), reverse=True)[:10],
            "action": "audit",
        },
        sort_keys=True,
    ).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def action_offload(vector: List[float]) -> int:
    payload = json.dumps(
        {
            "score": sum(abs(value) for value in vector) / max(len(vector), 1),
            "features": [round(value, 5) for value in vector],
            "request": "remote_explanation",
        },
        sort_keys=True,
    ).encode("utf-8")
    compressed = gzip.compress(payload, compresslevel=3)
    return len(compressed)


def action_delay(vector: List[float]) -> int:
    return 1


ACTIONS: Dict[str, Callable[[List[float]], int]] = {
    "none": action_none,
    "coarse": action_coarse,
    "full": action_full,
    "offload": action_offload,
    "audit": action_audit,
    "redact": action_redact,
    "delay": action_delay,
}


def command_output(command: List[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def local_hardware_summary() -> Dict[str, object]:
    mem_bytes = command_output(["sysctl", "-n", "hw.memsize"])
    physical_cpu = command_output(["sysctl", "-n", "hw.physicalcpu"])
    logical_cpu = command_output(["sysctl", "-n", "hw.logicalcpu"])
    gpu_lines = []
    profiler = command_output(["system_profiler", "SPDisplaysDataType"])
    for line in profiler.splitlines():
        stripped = line.strip()
        if stripped.startswith(("Chipset Model:", "Total Number of Cores:", "Metal Support:")):
            gpu_lines.append(stripped)
    return {
        "privacy_note": "Serial numbers and user identifiers are intentionally excluded.",
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "machine": platform.machine(),
        "model": command_output(["sysctl", "-n", "hw.model"]),
        "cpu_brand": command_output(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "physical_cpu": int(physical_cpu) if physical_cpu.isdigit() else physical_cpu,
        "logical_cpu": int(logical_cpu) if logical_cpu.isdigit() else logical_cpu,
        "memory_gb": round(int(mem_bytes) / (1024**3), 2) if mem_bytes.isdigit() else mem_bytes,
        "gpu_summary": gpu_lines,
    }


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def measure(action: str, vectors: Iterable[List[float]], repeats: int) -> Dict[str, float]:
    fn = ACTIONS[action]
    samples: List[float] = []
    checksum = 0
    for vector in vectors:
        start = time.perf_counter()
        for _ in range(repeats):
            checksum ^= fn(vector)
        elapsed = time.perf_counter() - start
        samples.append(elapsed / repeats)
    median = statistics.median(samples)
    return {
        "median_us": median * 1_000_000.0,
        "p95_us": percentile(samples, 0.95) * 1_000_000.0,
        "checksum": float(checksum % 100000),
    }


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def tex_escape(value: object) -> str:
    text = str(value)
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
    ]:
        text = text.replace(old, new)
    return text


def write_tex(path: Path, rows: List[Dict[str, str]]) -> None:
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Action-profile provenance for XAI-SurfaceBench. Runtime values are local proxy measurements; coverage and exposure values are design parameters bounded by sensitivity analysis.}",
        r"\label{tab:action_profile_provenance}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrll}",
        r"\toprule",
        r"Action & Default compute & Measured compute & Exposure & Delay & Provenance & Sensitivity status \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(row['action'])} & {row['default_compute']} & {row['measured_compute_norm']} & {row['default_exposure']} & {row['default_delay']} & {tex_escape(row['provenance'])} & {tex_escape(row['sensitivity_status'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table*}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown(path: Path, rows: List[Dict[str, str]], summary: Dict[str, object]) -> None:
    table_rows = [
        "| Action | Default compute | Measured compute norm | Median us | Exposure | Delay | Provenance |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        table_rows.append(
            f"| {row['action']} | {row['default_compute']} | {row['measured_compute_norm']} | {row['median_us']} | {row['default_exposure']} | {row['default_delay']} | {row['provenance']} |"
        )
    text = f"""# Action-Profile Provenance

This artifact documents the source of each default action-profile value used by
XAI-SurfaceBench. Runtime values are local proxy measurements over deterministic
synthetic alert vectors. They are not hardware deployment benchmarks; they justify
relative compute tiers and are bounded by the existing action-profile sensitivity
experiment.

## Environment

```json
{json.dumps(summary, indent=2, sort_keys=True)}
```

## Profile Table

{chr(10).join(table_rows)}

## Interpretation

- `full` is the normalization baseline for local high-fidelity explanation cost.
- `offload` measures local request packaging only; its larger delay profile comes
  from modeled RTT/service latency, not from local serialization time.
- Coverage, high-risk coverage, exposure, and delay values remain design
  parameters. Their influence is tested in the profile-sensitivity experiment.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--vectors", type=int, default=500)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    root = args.root.resolve()
    vectors = make_vectors(args.vectors, args.width)
    measured = {action: measure(action, vectors, args.repeats) for action in ACTIONS}
    full_median = max(measured["full"]["median_us"], 1e-9)
    provenance = {
        "none": "administrative no-op",
        "coarse": "top-feature local proxy",
        "full": "perturbation-style local proxy",
        "offload": "request packaging proxy plus modeled RTT",
        "audit": "metadata serialization and hash proxy",
        "redact": "top-feature masking proxy",
        "delay": "administrative deferral",
    }
    rows: List[Dict[str, str]] = []
    for action in ["none", "coarse", "full", "offload", "audit", "redact", "delay"]:
        profile = ACTION_PROFILES[action]
        rows.append(
            {
                "action": action,
                "default_compute": f"{profile['compute']:.2f}",
                "measured_compute_norm": f"{measured[action]['median_us'] / full_median:.3f}",
                "median_us": f"{measured[action]['median_us']:.3f}",
                "p95_us": f"{measured[action]['p95_us']:.3f}",
                "default_exposure": f"{profile['exposure']:.2f}",
                "default_delay": f"{profile['delay']:.2f}",
                "provenance": provenance[action],
                "sensitivity_status": "bounded by profile_sensitivity",
            }
        )
    summary = {
        "vectors": args.vectors,
        "width": args.width,
        "repeats": args.repeats,
        "normalization": "median runtime divided by full-action median runtime",
        "measurement_scope": "local proxy measurement on the listed host, not edge/gateway deployment benchmark",
        "hardware": local_hardware_summary(),
    }
    write_csv(root / "results" / "action_profile_microbenchmark.csv", rows)
    (root / "results").mkdir(parents=True, exist_ok=True)
    (root / "results" / "action_profile_microbenchmark_summary.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_tex(root / "tables" / "action_profile_provenance.tex", rows)
    write_markdown(root / "ACTION_PROFILE_PROVENANCE.md", rows, summary)
    print(f"rows={len(rows)}")
    print(f"report={root / 'ACTION_PROFILE_PROVENANCE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

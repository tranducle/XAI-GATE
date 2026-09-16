#!/usr/bin/env python3
"""Generate a diagnostic showing explanation debt is not a simple item count."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List


HIGH_RISK_PROBS = {
    "low": 0.04,
    "medium": 0.22,
    "high": 0.70,
    "critical": 0.93,
}

ACTION_COVERAGE = {
    "delay": 0.0,
    "none": 0.0,
    "coarse": 0.45,
    "redact": 0.58,
    "audit": 0.72,
    "full": 1.0,
}


def debt_increment(count: int, bucket: str, action: str) -> float:
    coverage = ACTION_COVERAGE[action]
    debt = count * (1.0 - coverage) * (0.65 + 0.70 * HIGH_RISK_PROBS[bucket])
    if action == "delay":
        debt += 0.35 * count
    return debt


def rows() -> List[Dict[str, object]]:
    scenarios = [
        ("same count, low-risk delayed", 100, "low", "delay"),
        ("same count, critical delayed", 100, "critical", "delay"),
        ("same count, high-risk coarse", 100, "high", "coarse"),
        ("same count, high-risk audit", 100, "high", "audit"),
        ("same count, full explanation", 100, "critical", "full"),
    ]
    output = []
    for name, item_count, bucket, action in scenarios:
        debt = debt_increment(item_count, bucket, action)
        output.append(
            {
                "scenario": name,
                "item_count": item_count,
                "risk_bucket": bucket,
                "action": action,
                "coverage": ACTION_COVERAGE[action],
                "explanation_debt": debt,
                "debt_per_item": debt / max(item_count, 1),
            }
        )
    return output


def write_csv(path: Path, data: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)


def write_tex(path: Path, data: List[Dict[str, object]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Debt-vs-count diagnostic. Equal alert-obligation counts can imply different explanation debt because debt is risk- and obligation-weighted.}",
        r"\label{tab:debt_backlog_diagnostic}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Scenario & Items & Coverage & Debt \\",
        r"\midrule",
    ]
    for row in data:
        lines.append(
            f"{row['scenario']} & {row['item_count']} & {float(row['coverage']):.2f} & {float(row['explanation_debt']):.1f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown(path: Path, data: List[Dict[str, object]]) -> None:
    table = [
        "| Scenario | Items | Risk bucket | Action | Coverage | Debt | Debt/item |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for row in data:
        table.append(
            f"| {row['scenario']} | {row['item_count']} | {row['risk_bucket']} | {row['action']} | {float(row['coverage']):.2f} | {float(row['explanation_debt']):.1f} | {float(row['debt_per_item']):.3f} |"
        )
    text = f"""# Explanation Debt vs Item Count Diagnostic

Explanation debt is not a renamed queue length or item count. A count records
unserved items, whereas explanation debt weights unserved obligations by risk and by the
remaining explanation work after a selected action. The diagnostic below holds
the number of alert obligations fixed and varies risk bucket and action fidelity.

{chr(10).join(table)}

The first two rows have the same item count, but critical delayed alerts
produce larger debt than low-risk delayed alerts. The third and fourth rows have
the same item count and high-risk bucket, but audit creates less debt than
coarse explanation because it satisfies more of the explanation obligation.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    data = rows()
    write_csv(root / "results" / "debt_backlog_diagnostic.csv", data)
    (root / "results" / "debt_backlog_diagnostic.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_tex(root / "tables" / "debt_backlog_diagnostic.tex", data)
    write_markdown(root / "DEBT_BACKLOG_DIAGNOSTIC.md", data)
    print(f"rows={len(data)}")
    print(f"report={root / 'DEBT_BACKLOG_DIAGNOSTIC.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

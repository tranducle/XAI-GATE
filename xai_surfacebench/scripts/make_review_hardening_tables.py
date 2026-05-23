#!/usr/bin/env python3
"""Generate reviewer-hardening tables and short reports from benchmark outputs."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


KEY_METRICS = [
    "mean_high_risk_explanation_coverage",
    "mean_mean_explanation_debt",
    "mean_exposure_use",
    "mean_exposure_budget_violation_rate",
    "mean_packet_drop_rate",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def tex_table(path: Path, caption: str, label: str, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    spec = "l" + "r" * (len(headers) - 1)
    lines = [
        "\\begin{table*}[t]",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\centering",
        "\\scriptsize",
        f"\\begin{{tabular}}{{@{{}}{spec}@{{}}}}",
        "\\toprule",
        " & ".join(headers) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def choose_best_feasible(group: list[dict[str, str]]) -> dict[str, str]:
    feasible = [row for row in group if f(row, "mean_exposure_budget_violation_rate") <= 1e-9]
    candidates = feasible or group
    return sorted(
        candidates,
        key=lambda row: (
            -f(row, "mean_high_risk_explanation_coverage"),
            f(row, "mean_mean_explanation_debt"),
            f(row, "mean_exposure_use"),
        ),
    )[0]


def generate_tuned_envelope(root: Path) -> None:
    rows = read_rows(root / "results" / "tuned_baseline_envelopes_summary.csv")
    if not rows:
        return

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["regime"], row["policy"])].append(row)

    envelope_rows: list[dict[str, str]] = []
    for (regime, policy), group in sorted(grouped.items()):
        best = choose_best_feasible(group)
        envelope_rows.append(
            {
                "regime": regime,
                "policy": policy,
                "selected_variant": best["variant"],
                "high_risk_coverage": fmt(f(best, "mean_high_risk_explanation_coverage")),
                "mean_debt": fmt(f(best, "mean_mean_explanation_debt"), 1),
                "exposure_use": fmt(f(best, "mean_exposure_use")),
                "exposure_violation": fmt(f(best, "mean_exposure_budget_violation_rate")),
                "packet_drop": fmt(f(best, "mean_packet_drop_rate")),
                "selection_rule": "max coverage subject to zero exposure violation; fallback max coverage",
            }
        )

    write_csv(root / "results" / "tuned_baseline_envelope_selected.csv", envelope_rows)

    adversarial = [row for row in envelope_rows if row["regime"] == "adversarial_explanation_flood"]
    tex_table(
        root / "tables" / "tuned_baseline_envelope_adversarial.tex",
        "Tuned baseline envelope under adversarial explanation-demand inflation.",
        "tab:tuned_baseline_envelope_adversarial",
        ["Policy", "Selected variant", "High-risk cov.", "Debt", "Exposure", "Viol.", "Drop"],
        [
            [
                row["policy"].replace("_", "\\_"),
                row["selected_variant"].replace("_", "\\_"),
                row["high_risk_coverage"],
                row["mean_debt"],
                row["exposure_use"],
                row["exposure_violation"],
                row["packet_drop"],
            ]
            for row in adversarial
        ],
    )

    report = [
        "# Tuned Baseline Envelope Report",
        "",
        "Selection rule: for each policy and regime, select the variant with maximum high-risk coverage subject to zero exposure-budget violation. If no variant is feasible, select the maximum-coverage variant and preserve its violation rate.",
        "",
        "## Adversarial Explanation-Demand Inflation",
        "",
        "| Policy | Selected variant | High-risk coverage | Mean debt | Exposure use | Exposure violation | Packet drop |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in adversarial:
        report.append(
            f"| `{row['policy']}` | `{row['selected_variant']}` | {row['high_risk_coverage']} | {row['mean_debt']} | {row['exposure_use']} | {row['exposure_violation']} | {row['packet_drop']} |"
        )
    report.extend(
        [
            "",
            "Reviewer interpretation: this table prevents weak-baseline comparison by giving each baseline a tuning envelope before comparison. XAI-Gate should be interpreted against the selected feasible envelope, not only against default threshold settings.",
            "",
        ]
    )
    (root / "BASELINE_ENVELOPE_REPORT.md").write_text("\n".join(report), encoding="utf-8")


def generate_profile_sensitivity(root: Path) -> None:
    rows = read_rows(root / "results" / "profile_sensitivity_summary.csv")
    if not rows:
        return
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["regime"]].append(row)

    out_rows: list[dict[str, str]] = []
    for regime, group in sorted(grouped.items()):
        cov = [f(row, "mean_high_risk_explanation_coverage") for row in group]
        debt = [f(row, "mean_mean_explanation_debt") for row in group]
        exposure = [f(row, "mean_exposure_use") for row in group]
        violation = [f(row, "mean_exposure_budget_violation_rate") for row in group]
        out_rows.append(
            {
                "regime": regime,
                "coverage_min": fmt(min(cov)),
                "coverage_max": fmt(max(cov)),
                "debt_min": fmt(min(debt), 1),
                "debt_max": fmt(max(debt), 1),
                "exposure_min": fmt(min(exposure)),
                "exposure_max": fmt(max(exposure)),
                "violation_max": fmt(max(violation)),
            }
        )

    write_csv(root / "results" / "profile_sensitivity_ranges.csv", out_rows)
    tex_table(
        root / "tables" / "profile_sensitivity_ranges.tex",
        "XAI-Gate action-profile sensitivity ranges over profile perturbations.",
        "tab:profile_sensitivity_ranges",
        ["Regime", "Coverage min", "Coverage max", "Debt min", "Debt max", "Exposure min", "Exposure max", "Viol. max"],
        [
            [
                row["regime"].replace("_", "\\_"),
                row["coverage_min"],
                row["coverage_max"],
                row["debt_min"],
                row["debt_max"],
                row["exposure_min"],
                row["exposure_max"],
                row["violation_max"],
            ]
            for row in out_rows
        ],
    )

    report = [
        "# Action-Profile Sensitivity Report",
        "",
        "This report perturbs the abstract action profiles used by XAI-Gate. It tests whether the main conclusion is an artifact of one exact exposure, delay, coverage, cost, or debt coefficient.",
        "",
        "| Regime | Coverage range | Debt range | Exposure range | Max exposure violation |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in out_rows:
        report.append(
            f"| `{row['regime']}` | {row['coverage_min']}--{row['coverage_max']} | {row['debt_min']}--{row['debt_max']} | {row['exposure_min']}--{row['exposure_max']} | {row['violation_max']} |"
        )
    report.extend(
        [
            "",
            "Reviewer interpretation: profile sensitivity should be used to bound the strength of action-profile claims. A manuscript claim is credible only if it is stable across this perturbation envelope or explicitly reported as profile-dependent.",
            "",
        ]
    )
    (root / "ACTION_PROFILE_SENSITIVITY_REPORT.md").write_text("\n".join(report), encoding="utf-8")


def generate_worst_case(root: Path) -> None:
    rows = read_rows(root / "results" / "main_summary.csv")
    if not rows:
        return
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["policy"]].append(row)

    out_rows: list[dict[str, str]] = []
    for policy, group in sorted(grouped.items()):
        out_rows.append(
            {
                "policy": policy,
                "min_high_risk_coverage": fmt(min(f(row, "mean_high_risk_explanation_coverage") for row in group)),
                "max_mean_debt": fmt(max(f(row, "mean_mean_explanation_debt") for row in group), 1),
                "max_exposure_violation": fmt(max(f(row, "mean_exposure_budget_violation_rate") for row in group)),
                "max_packet_drop": fmt(max(f(row, "mean_packet_drop_rate") for row in group)),
            }
        )

    write_csv(root / "results" / "main_worst_case_by_policy.csv", out_rows)
    tex_table(
        root / "tables" / "main_worst_case_by_policy.tex",
        "Worst-case main-benchmark summary by policy across tested regimes.",
        "tab:main_worst_case_by_policy",
        ["Policy", "Min high-risk cov.", "Max debt", "Max exposure viol.", "Max drop"],
        [
            [
                row["policy"].replace("_", "\\_"),
                row["min_high_risk_coverage"],
                row["max_mean_debt"],
                row["max_exposure_violation"],
                row["max_packet_drop"],
            ]
            for row in out_rows
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    generate_tuned_envelope(root)
    generate_profile_sensitivity(root)
    generate_worst_case(root)
    print("review_hardening_tables=written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

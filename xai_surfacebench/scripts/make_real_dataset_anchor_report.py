#!/usr/bin/env python3
"""Generate UNSW-NB15 real-dataset benchmark tables and reports."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REGIMES = [
    "adversarial_explanation_flood",
    "transient_overload",
    "non_markovian",
    "rtt_uncertainty",
]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f(row: Dict[str, str], key: str) -> float:
    return float(row.get(key, "0") or 0.0)


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


def find_row(rows: Iterable[Dict[str, str]], regime: str, policy: str, variant: Optional[str] = None) -> Dict[str, str]:
    matches = [
        row
        for row in rows
        if row.get("regime") == regime and row.get("policy") == policy and (variant is None or row.get("variant") == variant)
    ]
    if not matches:
        raise SystemExit(f"Missing row for regime={regime}, policy={policy}, variant={variant}")
    return matches[0]


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_default_directional(root: Path, summary_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for regime in REGIMES:
        xai = find_row(summary_rows, regime, "xai_gate", "default")
        budget = find_row(summary_rows, regime, "budget_only_bexgov", "default")
        threshold = find_row(summary_rows, regime, "threshold_explain", "default")
        rows.append(
            {
                "regime": regime,
                "xai_hr_coverage": f(xai, "mean_high_risk_explanation_coverage"),
                "xai_debt": f(xai, "mean_mean_explanation_debt"),
                "xai_exposure_use": f(xai, "mean_exposure_use"),
                "xai_violation": f(xai, "mean_exposure_budget_violation_rate"),
                "budget_hr_coverage": f(budget, "mean_high_risk_explanation_coverage"),
                "budget_debt": f(budget, "mean_mean_explanation_debt"),
                "budget_exposure_use": f(budget, "mean_exposure_use"),
                "budget_violation": f(budget, "mean_exposure_budget_violation_rate"),
                "threshold_hr_coverage": f(threshold, "mean_high_risk_explanation_coverage"),
                "threshold_debt": f(threshold, "mean_mean_explanation_debt"),
                "threshold_exposure_use": f(threshold, "mean_exposure_use"),
                "threshold_violation": f(threshold, "mean_exposure_budget_violation_rate"),
            }
        )
    write_csv(root / "results" / "unsw_nb15_default_directional.csv", rows)
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{UNSW-NB15 real-dataset calibrated-anchor benchmark under fixed exposure budget. Threshold values are shown to expose infeasible high-coverage baselines.}",
        r"\label{tab:unsw_nb15_anchor}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrrrrr}",
        r"\toprule",
        r"Regime & XAI HR & XAI debt & XAI exp. & Budget HR & Budget debt & Budget exp. & Thresh. HR & Thresh. exp. & Thresh. viol. \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(row['regime'])} & {row['xai_hr_coverage']:.3f} & {row['xai_debt']:.1f} & {row['xai_exposure_use']:.3f} & "
            f"{row['budget_hr_coverage']:.3f} & {row['budget_debt']:.1f} & {row['budget_exposure_use']:.3f} & "
            f"{row['threshold_hr_coverage']:.3f} & {row['threshold_exposure_use']:.3f} & {row['threshold_violation']:.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table*}", ""])
    (root / "tables" / "unsw_nb15_default_directional.tex").write_text("\n".join(lines), encoding="utf-8")
    return rows


def make_tuning_table(root: Path, tuning_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    selected_specs = [
        ("adversarial_explanation_flood", "high_local_budget", "fixed exposure, larger local capacity"),
        ("adversarial_explanation_flood", "suspicion_strict", "fixed exposure, stricter suspicion"),
        ("adversarial_explanation_flood", "exposure_strict", "fixed exposure, stricter exposure weight"),
        ("adversarial_explanation_flood", "high_exposure_budget", "expanded exposure budget"),
        ("transient_overload", "balanced_coverage", "fixed exposure, balanced coverage"),
        ("non_markovian", "suspicion_strict", "fixed exposure, stricter suspicion"),
        ("rtt_uncertainty", "balanced_coverage", "fixed exposure, balanced coverage"),
    ]
    rows: List[Dict[str, object]] = []
    for regime, variant, note in selected_specs:
        row = find_row(tuning_rows, regime, "xai_gate", variant)
        rows.append(
            {
                "regime": regime,
                "variant": variant,
                "note": note,
                "hr_coverage": f(row, "mean_high_risk_explanation_coverage"),
                "debt": f(row, "mean_mean_explanation_debt"),
                "exposure_use": f(row, "mean_exposure_use"),
                "violation": f(row, "mean_exposure_budget_violation_rate"),
                "drop": f(row, "mean_packet_drop_rate"),
            }
        )
    write_csv(root / "results" / "unsw_nb15_xai_gate_selected_operating_points.csv", rows)
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Selected XAI-Gate operating points on the UNSW-NB15 calibrated anchor. The expanded-budget row is reported separately and is not a fixed-budget comparison.}",
        r"\label{tab:unsw_nb15_xai_tuning}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllrrrrr}",
        r"\toprule",
        r"Regime & Variant & Note & HR coverage & Debt & Exposure & Violation & Drop \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(row['regime'])} & {tex_escape(row['variant'])} & {tex_escape(row['note'])} & "
            f"{row['hr_coverage']:.3f} & {row['debt']:.1f} & {row['exposure_use']:.3f} & {row['violation']:.3f} & {row['drop']:.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table*}", ""])
    (root / "tables" / "unsw_nb15_xai_tuning.tex").write_text("\n".join(lines), encoding="utf-8")
    return rows


def make_report(root: Path, default_rows: List[Dict[str, object]], tuning_rows: List[Dict[str, object]]) -> None:
    summary = json.loads((root / "data" / "unsw_nb15" / "unsw_nb15_calibration_summary.json").read_text(encoding="utf-8"))
    default_md = [
        "| Regime | XAI HR | XAI debt | XAI exposure | Budget HR | Budget debt | Threshold HR | Threshold violation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in default_rows:
        default_md.append(
            f"| {row['regime']} | {row['xai_hr_coverage']:.3f} | {row['xai_debt']:.1f} | {row['xai_exposure_use']:.3f} | "
            f"{row['budget_hr_coverage']:.3f} | {row['budget_debt']:.1f} | {row['threshold_hr_coverage']:.3f} | {row['threshold_violation']:.3f} |"
        )
    tuning_md = [
        "| Regime | Variant | Note | HR coverage | Debt | Exposure | Violation |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in tuning_rows:
        tuning_md.append(
            f"| {row['regime']} | {row['variant']} | {row['note']} | {row['hr_coverage']:.3f} | {row['debt']:.1f} | {row['exposure_use']:.3f} | {row['violation']:.3f} |"
        )
    report = f"""# UNSW-NB15 Benchmark Report

This report records the first modern public real-dataset calibrated anchor for
XAI-SurfaceBench. The score stream is generated from UNSW-NB15 using a held-out
linear logistic calibration model. The model is not a detector contribution.

## Dataset Calibration

- Score-stream rows: {summary['score_stream_rows']}
- Positive-label rate: {summary['positive_rate']:.3f}
- Calibration ROC AUC metadata: {summary['model_metadata']['roc_auc']:.3f}
- Calibration average precision metadata: {summary['model_metadata']['average_precision']:.3f}
- Raw hashes: stored in `data/unsw_nb15/unsw_nb15_calibration_summary.json`

## Fixed-Budget Directional Result

{chr(10).join(default_md)}

Interpretation: XAI-Gate is exposure-feasible in all four UNSW-NB15 regimes after
the hard exposure-cap fix. It is not a universal high-risk coverage maximizer:
budget-only governance has higher adversarial high-risk coverage but substantially
higher debt, while threshold governance often obtains high coverage only with
exposure-budget violations.

## Selected XAI-Gate Operating Points

{chr(10).join(tuning_md)}

The expanded-budget adversarial row is reported separately because it changes the
exposure-capacity assumption. Fixed-budget rows are the appropriate fair comparison.

## Claim Boundary

The UNSW-NB15 anchor supports the claim that explanation-surface governance remains
meaningful under modern public IDS score/label distributions. It does not support
claims about new detector accuracy, real hardware latency, SME/operator benefit, or
deployment readiness.
"""
    (root / "UNSW_NB15_BENCHMARK_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    summary_rows = read_rows(root / "results" / "unsw_nb15_calibrated_anchor_summary.csv")
    tuning_rows = read_rows(root / "results" / "unsw_nb15_xai_gate_tuning_envelope_summary.csv")
    default_rows = make_default_directional(root, summary_rows)
    selected_tuning = make_tuning_table(root, tuning_rows)
    make_report(root, default_rows, selected_tuning)
    print(f"report={root / 'UNSW_NB15_BENCHMARK_REPORT.md'}")
    print(f"table={root / 'tables' / 'unsw_nb15_default_directional.tex'}")
    print(f"table={root / 'tables' / 'unsw_nb15_xai_tuning.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

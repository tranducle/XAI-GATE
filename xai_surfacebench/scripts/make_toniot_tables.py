#!/usr/bin/env python3
"""Generate compact manuscript tables for the TON_IoT calibration anchor."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def tex(value: str) -> str:
    return value.replace("_", "\\_")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_directional_table(root: Path = ROOT) -> None:
    rows = read_rows(root / "results" / "toniot_calibrated_anchor_summary.csv")
    by_key = {(row["regime"], row["policy"]): row for row in rows}
    regimes = [
        "adversarial_explanation_flood",
        "transient_overload",
        "non_markovian",
        "rtt_uncertainty",
    ]
    out_rows: list[dict[str, str]] = []
    tex_rows: list[list[str]] = []
    for regime in regimes:
        xai = by_key[(regime, "xai_gate")]
        budget = by_key[(regime, "budget_only_bexgov")]
        threshold = by_key[(regime, "threshold_explain")]
        out = {
            "regime": regime,
            "xai_high_risk_coverage": fmt(f(xai, "mean_high_risk_explanation_coverage")),
            "xai_mean_debt": fmt(f(xai, "mean_mean_explanation_debt"), 1),
            "xai_exposure_use": fmt(f(xai, "mean_exposure_use")),
            "xai_exposure_violation": fmt(f(xai, "mean_exposure_budget_violation_rate")),
            "budget_high_risk_coverage": fmt(f(budget, "mean_high_risk_explanation_coverage")),
            "budget_mean_debt": fmt(f(budget, "mean_mean_explanation_debt"), 1),
            "budget_exposure_use": fmt(f(budget, "mean_exposure_use")),
            "threshold_high_risk_coverage": fmt(f(threshold, "mean_high_risk_explanation_coverage")),
            "threshold_exposure_use": fmt(f(threshold, "mean_exposure_use")),
            "threshold_exposure_violation": fmt(f(threshold, "mean_exposure_budget_violation_rate")),
        }
        out_rows.append(out)
        tex_rows.append(
            [
                tex(regime),
                out["xai_high_risk_coverage"],
                out["xai_mean_debt"],
                out["xai_exposure_use"],
                out["xai_exposure_violation"],
                out["budget_high_risk_coverage"],
                out["budget_mean_debt"],
                out["budget_exposure_use"],
                out["threshold_high_risk_coverage"],
                out["threshold_exposure_use"],
                out["threshold_exposure_violation"],
            ]
        )

    write_csv(root / "results" / "toniot_default_directional.csv", out_rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\scriptsize",
        "\\caption{TON\\_IoT calibrated-anchor results under fixed exposure budget. The stream is generated from an overlap-controlled, held-out test split and is used only as calibration metadata for explanation-surface stress testing.}",
        "\\label{tab:toniot_anchor}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lrrrrrrrrrr}",
        "\\toprule",
        "Regime & XAI HR & XAI debt & XAI exp. & XAI viol. & Budget HR & Budget debt & Budget exp. & Thresh. HR & Thresh. exp. & Thresh. viol. \\\\",
        "\\midrule",
    ]
    for row in tex_rows:
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "}", "\\end{table*}", ""])
    (root / "tables" / "toniot_default_directional.tex").write_text("\n".join(lines), encoding="utf-8")


def write_report(root: Path = ROOT) -> None:
    summary = json.loads((root / "data" / "toniot" / "toniot_calibration_summary.json").read_text())
    rows = read_rows(root / "results" / "toniot_default_directional.csv")
    model = summary["model_metadata"]
    split = summary["split"]
    dedup = summary["deduplication"]
    lines = [
        "# TON_IoT Benchmark Report",
        "",
        "This report summarizes the third public calibration anchor. TON_IoT is treated as an IoT/IIoT score-stream source for explanation-surface benchmarking, not as a detector contribution.",
        "",
        "## Data Audit",
        "",
        f"- Raw rows: {dedup['rows_before']}",
        f"- Rows after feature deduplication: {dedup['rows_after']}",
        f"- Stratified train/test rows: {split['train_rows']} / {split['test_rows']}",
        f"- Train-test feature-hash overlap after split: {split['train_test_feature_hash_overlap']}",
        f"- Held-out score-stream rows: {summary['score_stream_rows']}",
        f"- Test positive-label rate: {summary['positive_rate']:.3f}",
        f"- Calibration ROC AUC / AP / Brier: {model['roc_auc']:.3f} / {model['average_precision']:.3f} / {model['brier_score']:.3f}",
        "",
        "## Directional Results",
        "",
        "| Regime | XAI HR | XAI debt | XAI exposure | XAI violation | Budget HR | Budget debt | Threshold HR | Threshold violation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['regime']}` | {row['xai_high_risk_coverage']} | {row['xai_mean_debt']} | {row['xai_exposure_use']} | {row['xai_exposure_violation']} | {row['budget_high_risk_coverage']} | {row['budget_mean_debt']} | {row['threshold_high_risk_coverage']} | {row['threshold_exposure_violation']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The TON_IoT anchor broadens the public-data validation story beyond KDDCup99 and UNSW-NB15. It does not establish detector novelty, human/operator validation, hardware deployment readiness, or general deployment efficacy.",
            "",
        ]
    )
    (root / "TONIOT_BENCHMARK_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    write_directional_table(ROOT)
    write_report(ROOT)
    print(
        json.dumps(
            {
                "csv": str(ROOT / "results" / "toniot_default_directional.csv"),
                "tex": str(ROOT / "tables" / "toniot_default_directional.tex"),
                "report": str(ROOT / "TONIOT_BENCHMARK_REPORT.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

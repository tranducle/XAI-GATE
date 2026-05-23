#!/usr/bin/env python3
"""Generate compact manuscript tables for the de-duplicated UNSW-NB15 rerun."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
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
    rows = read_rows(root / "results" / "unsw_nb15_deduplicated_anchor_summary.csv")
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

    write_csv(root / "results" / "unsw_nb15_deduplicated_directional.csv", out_rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\scriptsize",
        "\\caption{De-duplicated UNSW-NB15 calibrated-anchor rerun under fixed exposure budget. The stream removes feature-duplicate rows and train-test feature overlap before calibration.}",
        "\\label{tab:unsw_nb15_deduplicated_anchor}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lrrrrrrrrrr}",
        "\\toprule",
        "Regime & XAI HR & XAI debt & XAI exp. & XAI viol. & Budget HR & Budget debt & Budget exp. & Thresh. HR & Thresh. exp. & Thresh. viol. \\\\",
        "\\midrule",
    ]
    for row in tex_rows:
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "}", "\\end{table*}", ""])
    (root / "tables" / "unsw_nb15_deduplicated_directional.tex").write_text("\n".join(lines), encoding="utf-8")


def write_report(root: Path = ROOT) -> None:
    summary = json.loads((root / "data" / "unsw_nb15_dedup" / "unsw_nb15_dedup_calibration_summary.json").read_text())
    rows = read_rows(root / "results" / "unsw_nb15_deduplicated_directional.csv")
    lines = [
        "# De-duplicated UNSW-NB15 Rerun Report",
        "",
        "This report summarizes the de-duplicated UNSW-NB15 anchor rerun. The rerun removes within-split feature duplicates and removes any de-duplicated test row whose feature hash appears in the de-duplicated training split.",
        "",
        "## Data Audit",
        "",
        f"- Train rows before/after: {summary['deduplication']['train_rows_before']} / {summary['deduplication']['train_rows_after']}",
        f"- Test rows before/after: {summary['deduplication']['test_rows_before']} / {summary['deduplication']['test_rows_after']}",
        f"- Feature train-test overlap before/after: {summary['deduplication']['feature_hash_train_test_overlap_before']} / {summary['deduplication']['feature_hash_train_test_overlap_after']}",
        f"- Exact train-test overlap before/after: {summary['deduplication']['exact_hash_train_test_overlap_before']} / {summary['deduplication']['exact_hash_train_test_overlap_after']}",
        f"- Calibration ROC AUC / AP: {summary['model_metadata']['roc_auc']:.3f} / {summary['model_metadata']['average_precision']:.3f}",
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
            "The de-duplicated rerun strengthens the public-data realism check by removing known duplicate/overlap artifacts. It remains a single public IDS calibration anchor and must not be described as detector novelty, leakage-free community benchmark generality, hardware validation, or operator validation.",
            "",
        ]
    )
    (root / "UNSW_NB15_DEDUP_RERUN_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    write_directional_table(ROOT)
    write_report(ROOT)
    print(
        json.dumps(
            {
                "csv": str(ROOT / "results" / "unsw_nb15_deduplicated_directional.csv"),
                "tex": str(ROOT / "tables" / "unsw_nb15_deduplicated_directional.tex"),
                "report": str(ROOT / "UNSW_NB15_DEDUP_RERUN_REPORT.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

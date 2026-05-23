#!/usr/bin/env python3
"""Generate final hardening tables and reports for submission readiness."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f(row: Dict[str, str], key: str) -> float:
    return float(row.get(key, "0") or 0.0)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
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


def select_xai_gate(root: Path) -> List[Dict[str, object]]:
    summary_path = root / "results" / "xai_gate_tuning_envelope_summary.csv"
    rows = [
        row
        for row in read_rows(summary_path)
        if row.get("policy") == "xai_gate" and row.get("regime") == "adversarial_explanation_flood"
    ]
    if not rows:
        raise SystemExit(f"No xai_gate rows found in {summary_path}")
    feasible = [row for row in rows if f(row, "mean_exposure_budget_violation_rate") <= 1e-9]
    ranked = sorted(
        feasible or rows,
        key=lambda row: (
            -f(row, "mean_high_risk_explanation_coverage"),
            f(row, "mean_mean_explanation_debt"),
            f(row, "mean_exposure_use"),
        ),
    )
    selected = []
    for rank, row in enumerate(ranked[:10], start=1):
        selected.append(
            {
                "rank": rank,
                "variant": row["variant"],
                "feasible_zero_exposure_violation": f(row, "mean_exposure_budget_violation_rate") <= 1e-9,
                "high_risk_coverage": f(row, "mean_high_risk_explanation_coverage"),
                "mean_debt": f(row, "mean_mean_explanation_debt"),
                "exposure_use": f(row, "mean_exposure_use"),
                "exposure_violation": f(row, "mean_exposure_budget_violation_rate"),
                "local_load": f(row, "mean_local_compute_load"),
            }
        )
    write_csv(root / "results" / "xai_gate_tuning_selected.csv", selected)
    return selected


def write_xai_gate_tex(root: Path, selected: List[Dict[str, object]]) -> None:
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{XAI-Gate tuning envelope under adversarial explanation-demand inflation. Rows are ranked by high-risk coverage among zero-exposure-violation variants.}",
        r"\label{tab:xai_gate_tuning_envelope}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Rank & Variant & Feasible & HR coverage & Debt & Exposure use & Violation \\",
        r"\midrule",
    ]
    for row in selected[:8]:
        lines.append(
            f"{row['rank']} & {tex_escape(row['variant'])} & {str(row['feasible_zero_exposure_violation'])} & "
            f"{float(row['high_risk_coverage']):.3f} & {float(row['mean_debt']):.1f} & "
            f"{float(row['exposure_use']):.3f} & {float(row['exposure_violation']):.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table*}", ""])
    (root / "tables").mkdir(parents=True, exist_ok=True)
    (root / "tables" / "xai_gate_tuning_envelope.tex").write_text("\n".join(lines), encoding="utf-8")


def make_exposure_taxonomy(root: Path) -> None:
    rows = [
        {
            "action": "none",
            "feature": "none",
            "model_behavior": "none",
            "policy_threshold": "none",
            "offload_path": "none",
            "audit_trace": "none",
            "exposure": "0.00",
        },
        {
            "action": "coarse",
            "feature": "top feature groups",
            "model_behavior": "low",
            "policy_threshold": "low",
            "offload_path": "none",
            "audit_trace": "none",
            "exposure": "0.10",
        },
        {
            "action": "full",
            "feature": "full attribution vector",
            "model_behavior": "high",
            "policy_threshold": "medium",
            "offload_path": "none",
            "audit_trace": "low",
            "exposure": "0.85",
        },
        {
            "action": "offload",
            "feature": "sanitized alert vector",
            "model_behavior": "high",
            "policy_threshold": "medium",
            "offload_path": "managed fog/cloud service",
            "audit_trace": "medium",
            "exposure": "1.00",
        },
        {
            "action": "audit",
            "feature": "metadata summary",
            "model_behavior": "medium",
            "policy_threshold": "medium",
            "offload_path": "none",
            "audit_trace": "high",
            "exposure": "0.34",
        },
        {
            "action": "redact",
            "feature": "masked attribution",
            "model_behavior": "low",
            "policy_threshold": "low",
            "offload_path": "none",
            "audit_trace": "low",
            "exposure": "0.08",
        },
        {
            "action": "delay",
            "feature": "none now",
            "model_behavior": "none now",
            "policy_threshold": "low",
            "offload_path": "none",
            "audit_trace": "queue marker",
            "exposure": "0.00",
        },
    ]
    write_csv(root / "results" / "exposure_taxonomy.csv", rows)
    tex = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Exposure taxonomy for explanation-surface actions.}",
        r"\label{tab:exposure_taxonomy}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllllr}",
        r"\toprule",
        r"Action & Feature disclosure & Model behavior & Offload path & Audit trace & Exposure \\",
        r"\midrule",
    ]
    for row in rows:
        tex.append(
            f"{tex_escape(row['action'])} & {tex_escape(row['feature'])} & {tex_escape(row['model_behavior'])} & {tex_escape(row['offload_path'])} & {tex_escape(row['audit_trace'])} & {row['exposure']} \\\\"
        )
    tex.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table*}", ""])
    (root / "tables" / "exposure_taxonomy.tex").write_text("\n".join(tex), encoding="utf-8")
    md_rows = [
        "| Action | Feature disclosure | Model behavior | Policy/threshold disclosure | Offload path | Audit trace | Exposure |",
        "|---|---|---|---|---|---|---:|",
    ]
    for row in rows:
        md_rows.append(
            f"| {row['action']} | {row['feature']} | {row['model_behavior']} | {row['policy_threshold']} | {row['offload_path']} | {row['audit_trace']} | {row['exposure']} |"
        )
    text = f"""# Exposure Taxonomy and Offload Trust Model

XAI-Gate treats explanations as information-bearing service outputs. Exposure is
an abstract accounting variable for five disclosure channels: feature attribution,
model-behavior cues, policy-threshold cues, offload data-path disclosure, and audit
trace disclosure.

{chr(10).join(md_rows)}

## Offload Model

The offload action sends a sanitized alert feature vector, calibrated score,
requested explainer type, and policy metadata to a managed fog/cloud explanation
service. Raw packet payload is outside the default data path. The higher exposure
profile reflects both data-path disclosure and richer returned explanation content.
The RTT belief in XAI-Gate represents the observed round-trip service delay of this
managed explanation tier.
"""
    (root / "EXPOSURE_TAXONOMY.md").write_text(text, encoding="utf-8")


def calibration_report(root: Path) -> Dict[str, object]:
    summary_path = root / "results" / "calibrated_anchor_summary.csv"
    rows = read_rows(summary_path)
    status = "kddcup99_no_training_score_stream"
    adversarial = [
        row for row in rows if row.get("regime") == "adversarial_explanation_flood" and row.get("policy") in {"xai_gate", "threshold_explain", "budget_only_bexgov"}
    ]
    ordered = sorted(adversarial, key=lambda row: row.get("policy", ""))
    text_rows = [
        "| Policy | HR coverage | Debt | Exposure use | Exposure violation | Calibration |",
        "|---|---:|---:|---:|---:|---|",
    ]
    payload_rows = []
    for row in ordered:
        payload = {
            "policy": row["policy"],
            "high_risk_coverage": f(row, "mean_high_risk_explanation_coverage"),
            "mean_debt": f(row, "mean_mean_explanation_debt"),
            "exposure_use": f(row, "mean_exposure_use"),
            "exposure_violation": f(row, "mean_exposure_budget_violation_rate"),
            "calibration_status": row.get("calibration_status", "") or status,
        }
        payload_rows.append(payload)
        text_rows.append(
            f"| {payload['policy']} | {payload['high_risk_coverage']:.3f} | {payload['mean_debt']:.1f} | {payload['exposure_use']:.3f} | {payload['exposure_violation']:.3f} | {payload['calibration_status']} |"
        )
    tex = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{KDDCup99 no-training calibrated-anchor check under adversarial explanation-demand inflation.}",
        r"\label{tab:calibrated_anchor}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Policy & HR coverage & Debt & Exposure use & Violation \\",
        r"\midrule",
    ]
    for row in payload_rows:
        tex.append(
            f"{tex_escape(row['policy'])} & {float(row['high_risk_coverage']):.3f} & {float(row['mean_debt']):.1f} & {float(row['exposure_use']):.3f} & {float(row['exposure_violation']):.3f} \\\\"
        )
    tex.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""])
    (root / "tables" / "calibrated_anchor_directional.tex").write_text("\n".join(tex), encoding="utf-8")
    report = f"""# Calibrated-Anchor Benchmark Report

This report summarizes the KDDCup99-anchored run. The score stream is used as
calibration metadata only; XAI-Gate is still evaluated as an explanation-service
controller rather than as a detector.

## Adversarial-Regime Directional Check

{chr(10).join(text_rows)}

## Interpretation

The calibrated anchor is a realism check against the default synthetic score-bucket
profile. Directional consistency means the service-management claim remains bounded
to exposure/debt control under calibrated score priors. If a policy wins only by
violating the exposure budget, it is not treated as exposure-feasible evidence.
"""
    (root / "CALIBRATED_ANCHOR_BENCHMARK_REPORT.md").write_text(report, encoding="utf-8")
    return {"adversarial_rows": payload_rows}


def xai_gate_report(root: Path, selected: List[Dict[str, object]]) -> Dict[str, object]:
    best = selected[0]
    default_rows = [
        row
        for row in read_rows(root / "results" / "xai_gate_tuning_envelope_summary.csv")
        if row.get("policy") == "xai_gate"
        and row.get("regime") == "adversarial_explanation_flood"
        and row.get("variant") == "xai_default"
    ]
    default = default_rows[0] if default_rows else None
    default_text = "not found"
    if default:
        default_text = (
            f"HR coverage {f(default, 'mean_high_risk_explanation_coverage'):.3f}, "
            f"debt {f(default, 'mean_mean_explanation_debt'):.1f}, "
            f"exposure use {f(default, 'mean_exposure_use'):.3f}, "
            f"violation {f(default, 'mean_exposure_budget_violation_rate'):.3f}"
        )
    top_rows = [
        "| Rank | Variant | HR coverage | Debt | Exposure use | Violation |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in selected[:8]:
        top_rows.append(
            f"| {row['rank']} | {row['variant']} | {float(row['high_risk_coverage']):.3f} | {float(row['mean_debt']):.1f} | {float(row['exposure_use']):.3f} | {float(row['exposure_violation']):.3f} |"
        )
    report = f"""# XAI-Gate Tuning Envelope Report

This stage gives XAI-Gate the same kind of tuning budget previously given to
threshold, FIFO, rate, static-fidelity, static-offload, and budget-only baselines.
Variants are ranked by high-risk coverage among zero-exposure-violation operating
points.

Default XAI-Gate: {default_text}

Best selected variant: `{best['variant']}` with HR coverage {float(best['high_risk_coverage']):.3f},
mean debt {float(best['mean_debt']):.1f}, exposure use {float(best['exposure_use']):.3f}, and
exposure violation {float(best['exposure_violation']):.3f}.

{chr(10).join(top_rows)}
"""
    (root / "XAI_GATE_TUNING_REPORT.md").write_text(report, encoding="utf-8")
    return {"best": best, "default": default_text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    make_exposure_taxonomy(root)
    selected = select_xai_gate(root)
    write_xai_gate_tex(root, selected)
    payload = {
        "xai_gate_tuning": xai_gate_report(root, selected),
        "calibration_anchor": calibration_report(root),
    }
    (root / "results" / "submission_readiness_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"selected={root / 'results' / 'xai_gate_tuning_selected.csv'}")
    print(f"report={root / 'XAI_GATE_TUNING_REPORT.md'}")
    print(f"report={root / 'CALIBRATED_ANCHOR_BENCHMARK_REPORT.md'}")
    print(f"report={root / 'EXPOSURE_TAXONOMY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

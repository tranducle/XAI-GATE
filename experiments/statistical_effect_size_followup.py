#!/usr/bin/env python3
"""Seed-level paired effect-size follow-up for XAI-SurfaceBench claims.

This script is intentionally dependency-light. It reads existing run-level CSV
artifacts, reconstructs the tuned-envelope selection rule from the manuscript,
and reports paired seed differences with bootstrap confidence intervals and an
exact two-sided sign test. It does not replace the manuscript's descriptive
confidence intervals; it is a follow-up guard against unsupported comparative
language.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
METRICS = {
    "high_risk_explanation_coverage": "higher",
    "mean_explanation_debt": "lower",
    "exposure_use": "lower",
    "exposure_budget_violation_rate": "lower",
    "packet_drop_rate": "lower",
    "mean_packet_delay": "lower",
}
BOOTSTRAP_REPS = 2000
BOOTSTRAP_SEED = 20260521


def read_runs(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def group_by(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    return grouped


def mean_metric(rows: list[dict[str, str]], metric: str) -> float:
    return mean(f(row, metric) for row in rows)


def select_envelope_variants(rows: list[dict[str, str]], regime: str) -> dict[str, str]:
    """Select one variant per policy using the manuscript's fairness rule.

    Rule: choose maximum high-risk coverage among variants with zero mean
    exposure-budget violation; if no feasible variant exists, fallback to maximum
    high-risk coverage overall.
    """
    grouped = group_by([r for r in rows if r["regime"] == regime], ("policy", "variant"))
    by_policy: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    for (policy, variant), variants in grouped.items():
        by_policy[policy].append(
            (
                variant,
                mean_metric(variants, "high_risk_explanation_coverage"),
                mean_metric(variants, "exposure_budget_violation_rate"),
            )
        )

    selected: dict[str, str] = {}
    for policy, candidates in by_policy.items():
        feasible = [c for c in candidates if abs(c[2]) <= 1e-12]
        pool = feasible if feasible else candidates
        selected[policy] = max(pool, key=lambda item: (item[1], -item[2], item[0]))[0]
    return selected


def rows_for(rows: list[dict[str, str]], regime: str, policy: str, variant: str) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in rows:
        if row["regime"] == regime and row["policy"] == policy and row["variant"] == variant:
            out[int(row["seed"])] = row
    return out


def bootstrap_ci(values: list[float]) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED)
    if not values:
        return (math.nan, math.nan)
    estimates = []
    n = len(values)
    for _ in range(BOOTSTRAP_REPS):
        estimates.append(mean(values[rng.randrange(n)] for _ in range(n)))
    estimates.sort()
    lo = estimates[int(0.025 * (BOOTSTRAP_REPS - 1))]
    hi = estimates[int(0.975 * (BOOTSTRAP_REPS - 1))]
    return lo, hi


def sign_test_p(pos: int, neg: int) -> float | None:
    n = pos + neg
    if n == 0:
        return None
    k = min(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def paired_comparison(
    rows: list[dict[str, str]],
    comparison_family: str,
    dataset: str,
    regime: str,
    policy_a: str,
    variant_a: str,
    policy_b: str,
    variant_b: str,
) -> list[dict[str, object]]:
    a_by_seed = rows_for(rows, regime, policy_a, variant_a)
    b_by_seed = rows_for(rows, regime, policy_b, variant_b)
    seeds = sorted(set(a_by_seed) & set(b_by_seed))
    results: list[dict[str, object]] = []
    for metric, direction in METRICS.items():
        pairs = [(f(a_by_seed[s], metric), f(b_by_seed[s], metric)) for s in seeds]
        diffs = [a - b for a, b in pairs]
        if not diffs:
            continue
        if direction == "higher":
            favorable = sum(1 for d in diffs if d > 0)
            unfavorable = sum(1 for d in diffs if d < 0)
        else:
            favorable = sum(1 for d in diffs if d < 0)
            unfavorable = sum(1 for d in diffs if d > 0)
        ties = len(diffs) - favorable - unfavorable
        diff_mean = mean(diffs)
        diff_sd = pstdev(diffs) if len(diffs) > 1 else 0.0
        ci_lo, ci_hi = bootstrap_ci(diffs)
        results.append(
            {
                "comparison_family": comparison_family,
                "dataset": dataset,
                "regime": regime,
                "policy_a": policy_a,
                "variant_a": variant_a,
                "policy_b": policy_b,
                "variant_b": variant_b,
                "metric": metric,
                "direction_for_a": direction,
                "paired_seeds": len(seeds),
                "mean_a": mean(a for a, _ in pairs),
                "mean_b": mean(b for _, b in pairs),
                "mean_diff_a_minus_b": diff_mean,
                "bootstrap_ci95_low": ci_lo,
                "bootstrap_ci95_high": ci_hi,
                "cohens_dz": None if diff_sd == 0 else diff_mean / diff_sd,
                "favorable_seed_count": favorable,
                "unfavorable_seed_count": unfavorable,
                "tie_seed_count": ties,
                "sign_test_two_sided_p": sign_test_p(favorable, unfavorable),
            }
        )
    return results


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.4g}"
    return str(value)


def tex_escape(value: object) -> str:
    return str(value).replace("_", "\\_")


def metric_label(metric: str) -> str:
    return {
        "high_risk_explanation_coverage": "HR coverage",
        "mean_explanation_debt": "Mean debt",
        "exposure_use": "Exposure use",
        "exposure_budget_violation_rate": "Exposure viol.",
        "packet_drop_rate": "Packet drop",
        "mean_packet_delay": "Packet delay",
    }.get(metric, metric.replace("_", " "))


def write_compact_tex(path: Path, rows: list[dict[str, object]]) -> None:
    wanted = [
        ("tuned_envelope", "synthetic", "threshold_explain", "high_risk_explanation_coverage", "Synthetic tuned", "XAI--threshold"),
        ("tuned_envelope", "synthetic", "threshold_explain", "mean_explanation_debt", "Synthetic tuned", "XAI--threshold"),
        ("tuned_envelope", "synthetic", "threshold_explain", "exposure_budget_violation_rate", "Synthetic tuned", "XAI--threshold"),
        ("tuned_envelope", "synthetic", "budget_only_bexgov", "high_risk_explanation_coverage", "Synthetic tuned", "XAI--budget"),
        ("tuned_envelope", "synthetic", "budget_only_bexgov", "mean_explanation_debt", "Synthetic tuned", "XAI--budget"),
        ("default_policy", "unsw_nb15", "budget_only_bexgov", "high_risk_explanation_coverage", "UNSW default", "XAI--budget"),
        ("default_policy", "unsw_nb15", "budget_only_bexgov", "mean_explanation_debt", "UNSW default", "XAI--budget"),
        ("default_policy", "unsw_nb15_deduplicated", "budget_only_bexgov", "high_risk_explanation_coverage", "UNSW dedup", "XAI--budget"),
        ("default_policy", "unsw_nb15_deduplicated", "budget_only_bexgov", "mean_explanation_debt", "UNSW dedup", "XAI--budget"),
        ("default_policy", "unsw_nb15_deduplicated", "threshold_explain", "exposure_budget_violation_rate", "UNSW dedup", "XAI--threshold"),
        ("default_policy", "toniot", "budget_only_bexgov", "high_risk_explanation_coverage", "TON_IoT", "XAI--budget"),
        ("default_policy", "toniot", "budget_only_bexgov", "mean_explanation_debt", "TON_IoT", "XAI--budget"),
        ("default_policy", "toniot", "threshold_explain", "exposure_budget_violation_rate", "TON_IoT", "XAI--threshold"),
    ]
    by_key = {
        (str(row["comparison_family"]), str(row["dataset"]), str(row["policy_b"]), str(row["metric"])): row
        for row in rows
        if row["policy_a"] == "xai_gate"
    }
    table_rows: list[list[str]] = []
    for family, dataset, policy_b, metric, anchor, comparison in wanted:
        row = by_key.get((family, dataset, policy_b, metric))
        if not row:
            continue
        counts = f"{row['favorable_seed_count']}/{row['tie_seed_count']}/{row['unfavorable_seed_count']}"
        interval = f"[{fmt(row['bootstrap_ci95_low'])}, {fmt(row['bootstrap_ci95_high'])}]"
        table_rows.append(
            [
                anchor,
                comparison,
                metric_label(metric),
                str(row["paired_seeds"]),
                fmt(row["mean_diff_a_minus_b"]),
                interval,
                counts,
                fmt(row["sign_test_two_sided_p"]),
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table*}[t]",
        "\\caption{Compact paired statistical follow-up for adversarial explanation-demand comparisons. Differences are XAI-Gate minus the comparator. Positive differences favor XAI-Gate for high-risk coverage; negative differences favor XAI-Gate for debt and exposure-violation metrics.}",
        "\\label{tab:paired_statistical_followup}",
        "\\centering",
        "\\scriptsize",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{@{}lllrrrrr@{}}",
        "\\toprule",
        "Anchor & Comparison & Metric & Seeds & Mean diff. & 95\\% CI & Fav/tie/unfav & Sign $p$ \\\\",
        "\\midrule",
    ]
    for row in table_rows:
        lines.append(" & ".join(tex_escape(cell) for cell in row) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "}",
            "\\end{table*}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown(path: Path, rows: list[dict[str, object]], selected: dict[str, dict[str, str]]) -> None:
    lines = [
        "# Statistical Effect-Size Follow-up",
        "",
        "This report uses seed-paired comparisons over existing XAI-SurfaceBench CSV artifacts. "
        "It reports raw mean differences, bootstrap 95% confidence intervals over paired seed "
        "differences, and exact two-sided sign-test p-values. These checks are follow-up evidence; "
        "they should not be described as the original manuscript's descriptive CI procedure.",
        "",
        "## Tuned-Envelope Variant Selection",
        "",
    ]
    for family, variants in selected.items():
        lines.append(f"### {family}")
        lines.append("")
        lines.append("| Policy | Selected variant |")
        lines.append("|---|---|")
        for policy, variant in sorted(variants.items()):
            lines.append(f"| `{policy}` | `{variant}` |")
        lines.append("")

    lines.extend(
        [
            "## Key Paired Comparisons",
            "",
            "| Family | Dataset | A | B | Metric | n | mean(A-B) | 95% CI | favorable/tie/unfavorable | sign p |",
            "|---|---|---|---|---|---:|---:|---|---|---:|",
        ]
    )
    focus = {
        "high_risk_explanation_coverage",
        "mean_explanation_debt",
        "exposure_budget_violation_rate",
        "exposure_use",
    }
    for row in rows:
        if row["metric"] not in focus:
            continue
        a = f"{row['policy_a']}:{row['variant_a']}"
        b = f"{row['policy_b']}:{row['variant_b']}"
        interval = f"[{fmt(row['bootstrap_ci95_low'])}, {fmt(row['bootstrap_ci95_high'])}]"
        counts = f"{row['favorable_seed_count']}/{row['tie_seed_count']}/{row['unfavorable_seed_count']}"
        lines.append(
            f"| {row['comparison_family']} | {row['dataset']} | `{a}` | `{b}` | "
            f"`{row['metric']}` | {row['paired_seeds']} | {fmt(row['mean_diff_a_minus_b'])} | "
            f"{interval} | {counts} | {fmt(row['sign_test_two_sided_p'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Guardrails",
            "",
            "- Positive `mean(A-B)` means policy A has a larger raw value than policy B; whether that is favorable depends on the metric.",
            "- For coverage, larger is favorable. For debt, exposure use, exposure-violation, drop, and delay, smaller is favorable.",
            "- The sign test ignores ties. When all paired differences are identical, `cohens_dz` is omitted in the CSV because the paired standard deviation is zero.",
            "- Use these results to support bounded comparative statements only; they do not establish deployment readiness, operator benefit, or detector novelty.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    main_rows = read_runs(RESULTS / "main_runs.csv")
    tuned_rows = read_runs(RESULTS / "tuned_baseline_envelopes_runs.csv")
    unsw_rows = read_runs(RESULTS / "unsw_nb15_calibrated_anchor_runs.csv")
    unsw_tuned_rows = read_runs(RESULTS / "unsw_nb15_tuned_baseline_envelopes_runs.csv")
    unsw_dedup_rows = read_runs(RESULTS / "unsw_nb15_deduplicated_anchor_runs.csv")
    toniot_rows = read_runs(RESULTS / "toniot_calibrated_anchor_runs.csv")

    regime = "adversarial_explanation_flood"
    selected_synthetic = select_envelope_variants(tuned_rows, regime)
    selected_unsw = select_envelope_variants(unsw_tuned_rows, regime)

    comparisons: list[dict[str, object]] = []
    for baseline in ["threshold_explain", "budget_only_bexgov", "rate_limited", "static_coarse_full"]:
        comparisons += paired_comparison(
            main_rows,
            "default_policy",
            "synthetic",
            regime,
            "xai_gate",
            "default",
            baseline,
            "default",
        )

    for baseline, variant_b in selected_synthetic.items():
        if baseline == "xai_gate":
            continue
        comparisons += paired_comparison(
            tuned_rows,
            "tuned_envelope",
            "synthetic",
            regime,
            "xai_gate",
            selected_synthetic["xai_gate"],
            baseline,
            variant_b,
        )

    for baseline in ["threshold_explain", "budget_only_bexgov", "rate_limited", "static_coarse_full"]:
        comparisons += paired_comparison(
            unsw_rows,
            "default_policy",
            "unsw_nb15",
            regime,
            "xai_gate",
            "default",
            baseline,
            "default",
        )

    for baseline, variant_b in selected_unsw.items():
        if baseline == "xai_gate":
            continue
        comparisons += paired_comparison(
            unsw_tuned_rows,
            "tuned_envelope",
            "unsw_nb15",
            regime,
            "xai_gate",
            selected_unsw["xai_gate"],
            baseline,
            variant_b,
        )

    if unsw_dedup_rows:
        for baseline in ["threshold_explain", "budget_only_bexgov", "rate_limited", "static_coarse_full"]:
            comparisons += paired_comparison(
                unsw_dedup_rows,
                "default_policy",
                "unsw_nb15_deduplicated",
                regime,
                "xai_gate",
                "default",
                baseline,
                "default",
            )

    if toniot_rows:
        for baseline in ["threshold_explain", "budget_only_bexgov", "rate_limited", "static_coarse_full"]:
            comparisons += paired_comparison(
                toniot_rows,
                "default_policy",
                "toniot",
                regime,
                "xai_gate",
                "default",
                baseline,
                "default",
            )

    out_csv = RESULTS / "statistical_effect_size_followup.csv"
    out_json = RESULTS / "statistical_effect_size_followup.json"
    out_md = ROOT / "STATISTICAL_EFFECT_SIZE_REPORT.md"
    write_csv(out_csv, comparisons)
    out_json.write_text(
        json.dumps(
            {
                "bootstrap_reps": BOOTSTRAP_REPS,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "metrics": METRICS,
                "selected_variants": {
                    "synthetic_tuned_envelope_adversarial": selected_synthetic,
                    "unsw_tuned_envelope_adversarial": selected_unsw,
                },
                "comparisons": comparisons,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_markdown(
        out_md,
        comparisons,
        {
            "Synthetic tuned envelope, adversarial regime": selected_synthetic,
            "UNSW-NB15 tuned envelope, adversarial regime": selected_unsw,
        },
    )
    compact_tex = ROOT / "tables" / "paired_statistical_followup_compact.tex"
    write_compact_tex(compact_tex, comparisons)
    print(
        json.dumps(
            {
                "csv": str(out_csv),
                "json": str(out_json),
                "markdown": str(out_md),
                "compact_tex": str(compact_tex),
                "rows": len(comparisons),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

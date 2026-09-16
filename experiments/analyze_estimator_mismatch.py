#!/usr/bin/env python3
"""Analyze full estimator-mismatch robustness results."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "estimator_mismatch"
ANALYSIS = RESULTS / "analysis"
ANALYSIS.mkdir(parents=True, exist_ok=True)

SYN = RESULTS / "full_synthetic_runs.csv"
TEMP = RESULTS / "full_temporal_runs.csv"

METRICS = [
    "high_risk_explanation_coverage",
    "mean_explanation_debt",
    "exposure_use",
    "estimated_exposure_use",
    "exposure_budget_violation_rate",
    "packet_drop_rate",
    "action_assignment_disagreement_rate",
]
PAIRED_METRICS = [
    "high_risk_explanation_coverage",
    "mean_explanation_debt",
    "exposure_use",
    "exposure_budget_violation_rate",
]
VARIANT_ORDER = [
    "nominal",
    "compute_under_25",
    "compute_over_25",
    "exposure_under_25",
    "exposure_over_25",
    "debt_under_25",
    "debt_over_25",
    "rtt_under_25",
    "rtt_over_25",
    "joint_optimistic_25",
    "joint_conservative_25",
    "severe_optimistic_50",
    "severe_conservative_50",
]

def exact_sign_test(values: Iterable[float], tol: float = 1e-12) -> tuple[int, int, float]:
    vals = [float(v) for v in values if abs(float(v)) > tol]
    n = len(vals)
    if n == 0:
        return 0, 0, 1.0
    positive = sum(v > 0 for v in vals)
    k = min(positive, n - positive)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return n, positive, min(1.0, 2.0 * tail)


def bootstrap_ci(values: np.ndarray, seed_key: str, reps: int = 10000) -> tuple[float, float]:
    if len(values) == 0:
        return float("nan"), float("nan")
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16) % (2**32)
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(reps, len(values)), replace=True).mean(axis=1)
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def paired_stats(syn: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime in sorted(syn.regime.unique()):
        nominal = syn[syn.variant == "nominal"]
        nominal = nominal[nominal.regime == regime].set_index("seed")
        for variant in VARIANT_ORDER:
            if variant == "nominal":
                continue
            block = syn[(syn.regime == regime) & (syn.variant == variant)].set_index("seed")
            joined = nominal.join(block, how="inner", lsuffix="_nominal", rsuffix="_variant")
            if len(joined) != 20:
                raise RuntimeError(f"Expected 20 paired seeds for {regime}/{variant}, got {len(joined)}")
            for metric in PAIRED_METRICS:
                diffs = (
                    joined[f"{metric}_variant"].astype(float)
                    - joined[f"{metric}_nominal"].astype(float)
                ).to_numpy()
                lo, hi = bootstrap_ci(diffs, f"{regime}|{variant}|{metric}")
                n_non_tied, n_positive, p = exact_sign_test(diffs)
                rows.append(
                    {
                        "regime": regime,
                        "variant": variant,
                        "metric": metric,
                        "paired_seed_count": len(diffs),
                        "mean_difference_variant_minus_nominal": float(diffs.mean()),
                        "bootstrap_ci95_low": lo,
                        "bootstrap_ci95_high": hi,
                        "non_tied_count": n_non_tied,
                        "positive_difference_count": n_positive,
                        "two_sided_sign_test_p": p,
                    }
                )
    return pd.DataFrame(rows)


def summary_table(syn: pd.DataFrame) -> pd.DataFrame:
    return (
        syn.groupby(["regime", "variant"], as_index=False)[METRICS]
        .mean()
        .sort_values(["regime", "variant"], kind="mergesort")
    )


def temporal_effects(temp: pd.DataFrame) -> pd.DataFrame:
    nominal = temp[temp.variant == "nominal"].set_index("session_id")
    rows = []
    for _, row in temp[temp.variant != "nominal"].iterrows():
        ref = nominal.loc[row.session_id]
        out = {"session_id": row.session_id, "variant": row.variant}
        for metric in METRICS:
            out[f"{metric}_value"] = float(row[metric])
            out[f"{metric}_difference_from_nominal"] = float(row[metric]) - float(ref[metric])
        rows.append(out)
    return pd.DataFrame(rows)



def main() -> int:
    syn = pd.read_csv(SYN)
    temp = pd.read_csv(TEMP)
    syn_summary = summary_table(syn)
    paired = paired_stats(syn)
    temp_effect = temporal_effects(temp)

    syn_summary.to_csv(ANALYSIS / "synthetic_variant_summary.csv", index=False)
    paired.to_csv(ANALYSIS / "paired_seed_statistics.csv", index=False)
    temp_effect.to_csv(ANALYSIS / "temporal_capture_effects.csv", index=False)

    adv = syn_summary[syn_summary.regime == "adversarial_explanation_flood"].set_index("variant")
    ddos = temp[temp.session_id.str.startswith("DDoS-SynonymousIP_Flood")].set_index("variant")
    key = {
        "official_run_counts": {"synthetic": len(syn), "temporal": len(temp), "total": len(syn) + len(temp)},
        "adversarial_nominal": adv.loc["nominal", METRICS].to_dict(),
        "adversarial_exposure_under_25": adv.loc["exposure_under_25", METRICS].to_dict(),
        "adversarial_exposure_over_25": adv.loc["exposure_over_25", METRICS].to_dict(),
        "adversarial_joint_optimistic_25": adv.loc["joint_optimistic_25", METRICS].to_dict(),
        "adversarial_joint_conservative_25": adv.loc["joint_conservative_25", METRICS].to_dict(),
        "adversarial_severe_optimistic_50": adv.loc["severe_optimistic_50", METRICS].to_dict(),
        "adversarial_severe_conservative_50": adv.loc["severe_conservative_50", METRICS].to_dict(),
        "temporal_ddos_nominal": ddos.loc["nominal", METRICS].to_dict(),
        "temporal_ddos_exposure_under_25": ddos.loc["exposure_under_25", METRICS].to_dict(),
        "temporal_ddos_severe_optimistic_50": ddos.loc["severe_optimistic_50", METRICS].to_dict(),
        "temporal_ddos_severe_conservative_50": ddos.loc["severe_conservative_50", METRICS].to_dict(),
    }
    (ANALYSIS / "key_findings.json").write_text(json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Estimator-Mismatch Robustness Analysis",
        "",
        f"Full runs: {len(syn)} synthetic + {len(temp)} temporal = {len(syn) + len(temp)} total.",
        "",
        "## Adversarial synthetic operating point",
        "",
    ]
    for variant in [
        "nominal",
        "exposure_under_25",
        "exposure_over_25",
        "joint_optimistic_25",
        "joint_conservative_25",
        "severe_optimistic_50",
        "severe_conservative_50",
    ]:
        r = adv.loc[variant]
        lines.append(
            f"- {variant}: HR coverage {r.high_risk_explanation_coverage:.4f}, debt {r.mean_explanation_debt:.1f}, "
            f"actual exposure {r.exposure_use:.4f}, estimated exposure {r.estimated_exposure_use:.4f}, "
            f"violation {r.exposure_budget_violation_rate:.4f}, reassignment {r.action_assignment_disagreement_rate:.4f}."
        )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "Exposure underestimation is the clearest safety-sensitive failure mode: the controller can remain within its estimated cap while the fixed realization profile exceeds the true accounting budget. Conservative exposure estimation trades lower realized exposure for lower coverage and higher debt. Compute, debt, and RTT estimation errors also change action selection, but the exposure estimator directly governs whether a hard cap expressed in estimated units remains a hard cap in realized units.",
        "",
        "The four temporal captures are reported descriptively per capture. No inferential p-value is attached to them because the capture, not a synthetic seed, is the validation unit.",
    ]
    (ANALYSIS / "estimator_mismatch_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"synthetic_summary={ANALYSIS / 'synthetic_variant_summary.csv'}")
    print(f"paired_statistics={ANALYSIS / 'paired_seed_statistics.csv'}")
    print(f"temporal_effects={ANALYSIS / 'temporal_capture_effects.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Analyze literature-grounded operational comparator experiments.

The pre-specified selection rule is:
1) maximize high-risk coverage among variants with zero mean exposure violation;
2) if none are feasible, minimize mean exposure violation, then maximize coverage.
The script also computes paired seed-level differences for the adversarial regime.
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
REPORT_DIR = RESULTS / "literature_comparison"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REGIMES = [
    "adversarial_explanation_flood",
    "transient_overload",
    "non_markovian",
    "rtt_uncertainty",
]
POLICY_LABELS = {
    "selective_explanations_adapted": "Selective explanations adaptation",
    "resource_aware_offload_adapted": "Resource-aware offload adaptation",
    "xai_gate": "XAI-Gate",
}
METRICS = [
    "high_risk_explanation_coverage",
    "mean_explanation_debt",
    "exposure_use",
    "exposure_budget_violation_rate",
    "packet_drop_rate",
    "offload_rate",
    "local_compute_load",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def m(rows: list[dict[str, str]], key: str) -> float:
    return mean(float(r[key]) for r in rows)


def select_variants(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        groups[(r["regime"], r["policy"], r["variant"])].append(r)
    by_rp: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for (regime, policy, variant), rs in groups.items():
        cand: dict[str, object] = {
            "regime": regime,
            "policy": policy,
            "variant": variant,
            "seed_count": len(rs),
        }
        for metric in METRICS:
            cand[metric] = m(rs, metric)
        by_rp[(regime, policy)].append(cand)

    selected: list[dict[str, object]] = []
    for regime in REGIMES:
        for policy in POLICY_LABELS:
            candidates = by_rp[(regime, policy)]
            if not candidates:
                continue
            feasible = [c for c in candidates if abs(float(c["exposure_budget_violation_rate"])) <= 1e-12]
            if feasible:
                pick = max(
                    feasible,
                    key=lambda c: (
                        float(c["high_risk_explanation_coverage"]),
                        -float(c["mean_explanation_debt"]),
                        str(c["variant"]),
                    ),
                )
                pick = dict(pick)
                pick["selection_status"] = "zero_exposure_violation"
            else:
                min_violation = min(float(c["exposure_budget_violation_rate"]) for c in candidates)
                pool = [c for c in candidates if abs(float(c["exposure_budget_violation_rate"]) - min_violation) <= 1e-12]
                pick = max(pool, key=lambda c: (float(c["high_risk_explanation_coverage"]), str(c["variant"])))
                pick = dict(pick)
                pick["selection_status"] = "minimum_violation_fallback"
            selected.append(pick)
    return selected


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def bootstrap_ci(values: list[float], reps: int = 4000, seed: int = 20260914) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(values)
    estimates = sorted(mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(reps))
    return estimates[int(0.025*(reps-1))], estimates[int(0.975*(reps-1))]


def sign_test(pos: int, neg: int) -> float | None:
    n = pos + neg
    if n == 0:
        return None
    k = min(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k+1)) / (2**n)
    return min(1.0, 2.0*tail)


def paired_stats(runs: list[dict[str, str]], selected: list[dict[str, object]]) -> list[dict[str, object]]:
    adv = {str(r["policy"]): str(r["variant"]) for r in selected if r["regime"] == "adversarial_explanation_flood"}
    by = {(r["policy"], r["variant"], int(r["seed"])): r for r in runs if r["regime"] == "adversarial_explanation_flood"}
    out: list[dict[str, object]] = []
    for comparator in ["selective_explanations_adapted", "resource_aware_offload_adapted"]:
        va, vb = adv.get("xai_gate"), adv.get(comparator)
        if not va or not vb:
            continue
        for metric, direction in [
            ("high_risk_explanation_coverage", "higher"),
            ("mean_explanation_debt", "lower"),
            ("exposure_use", "lower"),
            ("exposure_budget_violation_rate", "lower"),
        ]:
            diffs=[]; avals=[]; bvals=[]
            for seed in range(1,21):
                a=by[("xai_gate",va,seed)]; b=by[(comparator,vb,seed)]
                av=float(a[metric]); bv=float(b[metric])
                avals.append(av); bvals.append(bv); diffs.append(av-bv)
            fav=sum(1 for d in diffs if d>0) if direction=="higher" else sum(1 for d in diffs if d<0)
            unf=sum(1 for d in diffs if d<0) if direction=="higher" else sum(1 for d in diffs if d>0)
            lo,hi=bootstrap_ci(diffs)
            sd=pstdev(diffs)
            out.append({
                "regime":"adversarial_explanation_flood",
                "policy_a":"xai_gate","variant_a":va,
                "policy_b":comparator,"variant_b":vb,
                "metric":metric,"direction_for_a":direction,"paired_seeds":20,
                "mean_a":mean(avals),"mean_b":mean(bvals),"mean_diff_a_minus_b":mean(diffs),
                "bootstrap_ci95_low":lo,"bootstrap_ci95_high":hi,
                "cohens_dz":None if sd==0 else mean(diffs)/sd,
                "favorable_seed_count":fav,"unfavorable_seed_count":unf,
                "tie_seed_count":20-fav-unf,"sign_test_two_sided_p":sign_test(fav,unf),
            })
    return out


def main() -> int:
    tuned_runs = read_csv(RESULTS / "literature_comparison_tuned_runs.csv")
    selected = select_variants(tuned_runs)
    stats = paired_stats(tuned_runs, selected)
    write_csv(REPORT_DIR / "selected_tuned_operating_points.csv", selected)
    write_csv(REPORT_DIR / "paired_adversarial_followup.csv", stats)
    (REPORT_DIR / "selected_tuned_operating_points.json").write_text(json.dumps(selected, indent=2)+"\n", encoding="utf-8")
    (REPORT_DIR / "paired_adversarial_followup.json").write_text(json.dumps(stats, indent=2)+"\n", encoding="utf-8")

    lines=["# Literature-Grounded Operational Comparison","","## Selected tuned operating points","",
           "| Regime | Policy | Variant | HR coverage | Debt | Exposure use | Exposure violation | Status |",
           "|---|---|---|---:|---:|---:|---:|---|"]
    for r in selected:
        lines.append(f"| {r['regime']} | {POLICY_LABELS[str(r['policy'])]} | `{r['variant']}` | {float(r['high_risk_explanation_coverage']):.3f} | {float(r['mean_explanation_debt']):.1f} | {float(r['exposure_use']):.3f} | {float(r['exposure_budget_violation_rate']):.3f} | {r['selection_status']} |")
    lines += ["","## Paired adversarial follow-up","",
              "Statistics use the 20 shared seeds and compare XAI-Gate with each selected literature-grounded adaptation. Raw differences are XAI-Gate minus comparator.",""]
    for r in stats:
        lines.append(f"- {r['policy_b']} / {r['metric']}: diff={float(r['mean_diff_a_minus_b']):.4g}, 95% bootstrap CI=[{float(r['bootstrap_ci95_low']):.4g}, {float(r['bootstrap_ci95_high']):.4g}], sign p={r['sign_test_two_sided_p']}")
    (REPORT_DIR / "literature_comparison_analysis.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print('selected_rows',len(selected)); print('paired_rows',len(stats)); print(REPORT_DIR)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

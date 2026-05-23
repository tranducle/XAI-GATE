# XAI-SurfaceBench

Deterministic no-training benchmark package for evaluating explanation-surface governance policies under network-defense resource constraints.

This package is separate from the earlier `../xai_gate_simulator.py`, which remains a prototype reference only. XAI-SurfaceBench is config-driven, multi-seed, calibration-ready, and designed to produce manuscript-ready evidence artifacts without adding performance claims automatically.

## Implemented Policy Set

- `never_explain`
- `always_explain`
- `threshold_explain`
- `rate_limited`
- `fifo_explanation`
- `static_coarse_full`
- `static_offload`
- `budget_only_bexgov`
- `xai_gate`

## Implemented Regime Set

- `poisson`
- `bursty`
- `self_similar`
- `markov_modulated`
- `non_markovian`
- `transient_overload`
- `adversarial_explanation_flood`
- `rtt_uncertainty`
- `detection_matrix_perturbation`

## Artifact Layout

- `configs/*.json`: reproducible experiment definitions.
- `results/*.csv`: per-run and aggregated mean/95% CI metrics.
- `results/*.json`: aggregate metadata and metric schema.
- `logs/*.jsonl`: per-run metric logs.
- `tables/*.tex`: LaTeX tables for manuscript integration.
- `figures/*.pdf`: generated diagnostic figures.

## Run Commands

From this package directory:

```bash
python3 scripts/sanity_check.py
python3 scripts/run_benchmark.py --config configs/main.json
python3 scripts/run_benchmark.py --config configs/demand_sweep.json
python3 scripts/run_benchmark.py --config configs/frontier.json
python3 scripts/run_benchmark.py --config configs/ablations.json
python3 scripts/run_benchmark.py --config configs/robustness.json
python3 scripts/make_figures.py
```

## Calibration-Ready Interface

The default suite does not train AI models. A calibrated score stream can be supplied later by setting:

```json
{
  "calibration": {
    "score_stream_path": "calibrated_score_stream.csv",
    "training_summary_path": "calibration_training_summary.json"
  }
}
```

Accepted score-stream columns are `score` or `calibrated_score`, plus `true_label` or `label`. If the files are absent, the simulator records a synthetic-default calibration status and continues.

## Reproducibility Rules

- Same config and same seed must produce identical in-memory metrics.
- Seeds use SHA-256-derived stable seeds; Python `hash()` is not used.
- Stage 0 checks finite metrics, required policy/regime coverage, deterministic reruns, and non-negative queue/debt-derived metrics.
- Stochastic summaries report seed means and 95% confidence intervals.

## Manuscript Gate

Do not add performance claims to `manuscript.tex` until Stages 1-5 have been run and `CLAIM_TO_EVIDENCE_MATRIX.md` has been reviewed. Results may show negative or mixed tradeoffs; those should be reported as validity-relevant findings, not hidden.

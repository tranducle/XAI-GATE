# Baseline Fairness and Tuning Grid

The benchmark includes strong non-learning baselines so that XAI-Gate is not compared only against weak strawmen.

## Fixed Baselines

- `never_explain`: lower bound on explanation coverage and upper bound on unmet explanation demand.
- `always_explain`: upper bound on immediate explanation coverage with no budget awareness.
- `static_coarse_full`: deterministic fidelity split: full explanations for high scores, coarse explanations for medium scores.
- `static_offload`: deterministic offload for high-score alerts, coarse local explanations for medium-score alerts.

## Budget and Queue Baselines

- `threshold_explain`: default threshold `0.72`; frontier experiments vary budgets so threshold behavior is observed under different resource envelopes.
- `rate_limited`: default quota `10` explanations per slot with token carryover capped at three slots.
- `fifo_explanation`: default FIFO service quota `12` explanations per slot; it deliberately does not prioritize high-risk alerts.
- `budget_only_bexgov`: uses local budget and exposure pressure but no suspicion, RTT, debt, or fidelity-aware scoring.

## Frontier Grid

The default frontier stage sweeps local explanation budgets and exposure budgets:

```text
local_explanation_budget = [10, 14, 18, 24, 32]
exposure_budget_total = [10000, 18000, 26000]
```

All mandatory policies are evaluated under the same seed set and regimes. This produces baseline envelopes rather than a single handpicked comparison point.

## Robustness Grid

The robustness stage sweeps:

```text
rtt_noise_scale = [0.5, 1.5]
explanation_cost_scale = [0.8, 1.25]
service_capacity_multiplier = [0.85, 1.15]
detection_matrix_noise = [0.1, 0.3]
burstiness_scale = [0.75, 1.5]
```

The benchmark should report cases where XAI-Gate loses or trades away one objective for another. Such cases are not failures of reproducibility; they define the credible boundary of the method.

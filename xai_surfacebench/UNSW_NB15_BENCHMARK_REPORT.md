# UNSW-NB15 Benchmark Report

This report records the first modern public real-dataset calibrated anchor for
XAI-SurfaceBench. The score stream is generated from UNSW-NB15 using a held-out
linear logistic calibration model. The model is not a detector contribution.

## Dataset Calibration

- Score-stream rows: 175341
- Positive-label rate: 0.681
- Calibration ROC AUC metadata: 0.976
- Calibration average precision metadata: 0.988
- Raw hashes: stored in `data/unsw_nb15/unsw_nb15_calibration_summary.json`

## Fixed-Budget Directional Result

| Regime | XAI HR | XAI debt | XAI exposure | Budget HR | Budget debt | Threshold HR | Threshold violation |
|---|---:|---:|---:|---:|---:|---:|---:|
| adversarial_explanation_flood | 0.670 | 4357.4 | 1.000 | 0.737 | 7946.8 | 0.927 | 0.566 |
| transient_overload | 0.730 | 3960.0 | 1.000 | 0.683 | 6710.6 | 0.842 | 0.428 |
| non_markovian | 0.752 | 768.6 | 0.954 | 0.672 | 5792.1 | 0.829 | 0.230 |
| rtt_uncertainty | 0.848 | 18.0 | 0.875 | 0.675 | 2543.4 | 0.821 | 0.002 |

Interpretation: XAI-Gate is exposure-feasible in all four UNSW-NB15 regimes after
the hard exposure-cap fix. It is not a universal high-risk coverage maximizer:
budget-only governance has higher adversarial high-risk coverage but substantially
higher debt, while threshold governance often obtains high coverage only with
exposure-budget violations.

## Selected XAI-Gate Operating Points

| Regime | Variant | Note | HR coverage | Debt | Exposure | Violation |
|---|---|---|---:|---:|---:|---:|
| adversarial_explanation_flood | high_local_budget | fixed exposure, larger local capacity | 0.699 | 3382.6 | 1.000 | 0.000 |
| adversarial_explanation_flood | suspicion_strict | fixed exposure, stricter suspicion | 0.689 | 4090.5 | 1.000 | 0.000 |
| adversarial_explanation_flood | exposure_strict | fixed exposure, stricter exposure weight | 0.686 | 4169.4 | 1.000 | 0.000 |
| adversarial_explanation_flood | high_exposure_budget | expanded exposure budget | 0.790 | 2794.0 | 0.990 | 0.000 |
| transient_overload | balanced_coverage | fixed exposure, balanced coverage | 0.766 | 3741.4 | 1.000 | 0.000 |
| non_markovian | suspicion_strict | fixed exposure, stricter suspicion | 0.772 | 593.1 | 0.932 | 0.000 |
| rtt_uncertainty | balanced_coverage | fixed exposure, balanced coverage | 0.873 | 5.9 | 0.888 | 0.000 |

The expanded-budget adversarial row is reported separately because it changes the
exposure-capacity assumption. Fixed-budget rows are the appropriate fair comparison.

## Claim Boundary

The UNSW-NB15 anchor supports the claim that explanation-surface governance remains
meaningful under modern public IDS score/label distributions. It does not support
claims about new detector accuracy, real hardware latency, SME/operator benefit, or
deployment readiness.

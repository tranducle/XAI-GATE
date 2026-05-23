# Calibrated-Anchor Benchmark Report

This report summarizes the KDDCup99-anchored run. The score stream is used as
calibration metadata only; XAI-Gate is still evaluated as an explanation-service
controller rather than as a detector.

## Adversarial-Regime Directional Check

| Policy | HR coverage | Debt | Exposure use | Exposure violation | Calibration |
|---|---:|---:|---:|---:|---|
| budget_only_bexgov | 0.177 | 10964.0 | 0.035 | 0.000 | kddcup99_no_training_score_stream |
| threshold_explain | 0.177 | 10992.7 | 0.035 | 0.000 | kddcup99_no_training_score_stream |
| xai_gate | 0.790 | 872.0 | 0.947 | 0.000 | kddcup99_no_training_score_stream |

## Interpretation

The calibrated anchor is a realism check against the default synthetic score-bucket
profile. Directional consistency means the service-management claim remains bounded
to exposure/debt control under calibrated score priors. If a policy wins only by
violating the exposure budget, it is not treated as exposure-feasible evidence.

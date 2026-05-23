# De-duplicated UNSW-NB15 Rerun Report

This report summarizes the de-duplicated UNSW-NB15 anchor rerun. The rerun removes within-split feature duplicates and removes any de-duplicated test row whose feature hash appears in the de-duplicated training split.

## Data Audit

- Train rows before/after: 82332 / 53946
- Test rows before/after: 175341 / 99738
- Feature train-test overlap before/after: 1302 / 0
- Exact train-test overlap before/after: 940 / 0
- Calibration ROC AUC / AP: 0.955 / 0.946

## Directional Results

| Regime | XAI HR | XAI debt | XAI exposure | XAI violation | Budget HR | Budget debt | Threshold HR | Threshold violation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `adversarial_explanation_flood` | 0.729 | 2866.1 | 1.000 | 0.000 | 0.715 | 8220.4 | 0.845 | 0.407 |
| `transient_overload` | 0.746 | 3023.7 | 0.993 | 0.000 | 0.641 | 6811.3 | 0.734 | 0.000 |
| `non_markovian` | 0.771 | 274.4 | 0.906 | 0.000 | 0.628 | 5869.9 | 0.720 | 0.000 |
| `rtt_uncertainty` | 0.813 | 0.8 | 0.663 | 0.000 | 0.621 | 2694.7 | 0.706 | 0.000 |

## Claim Boundary

The de-duplicated rerun strengthens the public-data realism check by removing known duplicate/overlap artifacts. It remains a single public IDS calibration anchor and must not be described as detector novelty, leakage-free community benchmark generality, hardware validation, or operator validation.

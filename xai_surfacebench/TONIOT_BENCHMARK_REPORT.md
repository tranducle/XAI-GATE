# TON_IoT Benchmark Report

This report summarizes the third public calibration anchor. TON_IoT is treated as an IoT/IIoT score-stream source for explanation-surface benchmarking, not as a detector contribution.

## Data Audit

- Raw rows: 211043
- Rows after feature deduplication: 190474
- Stratified train/test rows: 133331 / 57143
- Train-test feature-hash overlap after split: 0
- Held-out score-stream rows: 57143
- Test positive-label rate: 0.779
- Calibration ROC AUC / AP / Brier: 0.995 / 0.998 / 0.014

## Directional Results

| Regime | XAI HR | XAI debt | XAI exposure | XAI violation | Budget HR | Budget debt | Threshold HR | Threshold violation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `adversarial_explanation_flood` | 0.654 | 5020.2 | 1.000 | 0.000 | 0.767 | 6792.3 | 0.994 | 0.625 |
| `transient_overload` | 0.689 | 4947.5 | 1.000 | 0.000 | 0.786 | 5201.8 | 0.986 | 0.489 |
| `non_markovian` | 0.754 | 1274.4 | 0.979 | 0.000 | 0.788 | 3639.3 | 0.984 | 0.438 |
| `rtt_uncertainty` | 0.863 | 98.0 | 0.932 | 0.000 | 0.793 | 867.6 | 0.984 | 0.277 |

## Claim Boundary

The TON_IoT anchor broadens the public-data validation story beyond KDDCup99 and UNSW-NB15. It does not establish detector novelty, human/operator validation, hardware deployment readiness, or general deployment efficacy.

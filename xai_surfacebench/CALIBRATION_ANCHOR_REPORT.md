# KDDCup99 Calibration Anchor

This artifact adds an externally anchored, no-training calibration run for XAI-SurfaceBench.
It uses `sklearn.datasets.fetch_kddcup99(subset='SA', percent10=True)` and generates a
transparent score proxy from public traffic/error features. The proxy is used only to
instantiate score-bucket and high-risk priors; it is not a detector contribution.

## Files

- Score stream: `data/kddcup99_sa_score_stream.csv`
- Benchmark config: `configs/calibrated_anchor.json`
- Summary JSON: `data/kddcup99_sa_calibration_summary.json`

## Metadata

- Rows used: 50000
- Attack-label rate: 0.033
- Mean proxy score: 0.151
- AUC metadata: 0.955
- Training: none

## Bucket Summary

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
| low | 46995 | 0.940 | 0.025 | 0.131 |
| medium | 2920 | 0.058 | 0.128 | 0.455 |
| high | 85 | 0.002 | 1.000 | 0.678 |
| critical | 0 | 0.000 | 0.000 | 0.000 |

## Claim Boundary

This run addresses the reviewer risk that the evaluation was purely synthetic. It does
not establish deployment readiness, hardware timing, or detector novelty. Detector
accuracy should be interpreted only as calibration metadata.

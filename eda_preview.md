# EDA Preview: UNSW-NB15 Calibration Anchor

## Basic Counts

- Train rows: 82332
- Test / score-stream rows: 175341
- Test positive-label rate: 0.681
- Mean calibration score: 0.584

## Score Buckets

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
| low | 70761 | 0.404 | 0.253 | 0.089 |
| medium | 13909 | 0.079 | 0.825 | 0.532 |
| high | 6675 | 0.038 | 0.938 | 0.764 |
| critical | 83996 | 0.479 | 0.996 | 0.995 |

## Top Attack Families

| Attack family | Rows |
|---|---:|
| Normal | 56000 |
| Generic | 40000 |
| Exploits | 33393 |
| Fuzzers | 18184 |
| DoS | 12264 |
| Reconnaissance | 10491 |
| Analysis | 2000 |
| Backdoor | 1746 |
| Shellcode | 1133 |
| Worms | 130 |

## Feasibility Check

The data are compatible with the XAI-SurfaceBench calibrated score-stream schema:
`score`, `true_label`, `attack_family`, `cost_proxy`, `score_source`, and `split`.

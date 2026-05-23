# UNSW-NB15 De-duplicated Calibration Anchor

This artifact reruns the modern UNSW-NB15 calibrated anchor after removing
feature-duplicate rows and train-test feature overlap. It is a provenance and
robustness check for XAI-SurfaceBench, not a new detector contribution.

## Files

- Score stream: `data/unsw_nb15_dedup/unsw_nb15_dedup_score_stream.csv`
- Benchmark config: `configs/unsw_nb15_deduplicated_anchor.json`
- Summary JSON: `data/unsw_nb15_dedup/unsw_nb15_dedup_calibration_summary.json`
- Raw train/test CSVs: `data/unsw_nb15/raw/`

## Deduplication Audit

- Train rows before/after: 82332 / 53946
- Test rows before/after: 175341 / 99738
- Train feature-duplicate rows removed: 28386
- Test feature-duplicate rows removed: 74301
- Remaining test rows removed due to train feature overlap: 1302
- Feature train-test overlap before/after: 1302 / 0
- Exact train-test overlap before/after: 940 / 0

## Source And Provenance

- Official dataset page: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- Download mirror used for automation: https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15
- Dataset paper DOI: `10.1109/MilCIS.2015.7348942`
- De-duplicated train rows used: 53946
- De-duplicated test / score-stream rows: 99738
- Test positive-label rate: 0.484

## Calibration Model Metadata

- Model role: calibration metadata only
- Model family: linear SGD logistic classifier with balanced class weights
- ROC AUC: 0.955
- Average precision: 0.946
- Brier score: 0.103
- F1 at threshold 0.5: 0.827
- Numeric features: 39
- Categorical features: proto, service, state

## Score Bucket Summary

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
| low | 55117 | 0.553 | 0.156 | 0.060 |
| medium | 15393 | 0.154 | 0.760 | 0.553 |
| high | 10069 | 0.101 | 0.916 | 0.769 |
| critical | 19159 | 0.192 | 0.981 | 0.976 |

## Attack Family Preview

| Attack family | Rows |
|---|---:|
| Normal | 51446 |
| Exploits | 18699 |
| Fuzzers | 14678 |
| Reconnaissance | 6195 |
| Generic | 3686 |
| DoS | 2989 |
| Shellcode | 1072 |
| Analysis | 498 |
| Backdoor | 355 |
| Worms | 120 |

## Claim Boundary

The de-duplicated UNSW run addresses the reviewer concern that train-test
duplicate/overlap artifacts may inflate the calibration anchor. It does not
claim detector novelty, hardware timing, operator validation, or deployment
readiness.

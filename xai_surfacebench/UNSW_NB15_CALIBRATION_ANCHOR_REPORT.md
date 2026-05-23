# UNSW-NB15 Real-Dataset Calibration Anchor

This artifact adds a modern public real-dataset anchor for XAI-SurfaceBench.
UNSW-NB15 is used because it is a widely cited intrusion-detection dataset with
public train/test flow records. The downloaded CSV files come from the Hugging Face
mirror documented as UNSW-NB15 train/test CSVs, while the original dataset source
and citation remain the UNSW project page and the MilCIS dataset paper.

## Files

- Score stream: `data/unsw_nb15/unsw_nb15_score_stream.csv`
- Benchmark config: `configs/unsw_nb15_calibrated_anchor.json`
- Summary JSON: `data/unsw_nb15/unsw_nb15_calibration_summary.json`
- Raw train/test CSVs: `data/unsw_nb15/raw/`

## Source And Provenance

- Official dataset page: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- Download mirror used for automation: https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15
- Dataset paper DOI: `10.1109/MilCIS.2015.7348942`
- Train rows: 82332
- Test rows / score stream rows: 175341
- Test positive-label rate: 0.681

## Calibration Model Metadata

- Model role: calibration metadata only
- Model family: linear SGD logistic classifier with balanced class weights
- ROC AUC: 0.976
- Average precision: 0.988
- Brier score: 0.086
- F1 at threshold 0.5: 0.888
- Numeric features: 39
- Categorical features: proto, service, state

## Score Bucket Summary

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
| low | 70761 | 0.404 | 0.253 | 0.089 |
| medium | 13909 | 0.079 | 0.825 | 0.532 |
| high | 6675 | 0.038 | 0.938 | 0.764 |
| critical | 83996 | 0.479 | 0.996 | 0.995 |

## Attack Family Preview

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

## Claim Boundary

This run addresses the reviewer risk that XAI-SurfaceBench had only synthetic or
legacy calibration. It does not claim new detector accuracy, hardware timing,
operator validation, or deployment readiness. Detector metrics are calibration
metadata for the score stream; the paper's contribution remains explanation-surface
governance under finite service capacity and exposure constraints.

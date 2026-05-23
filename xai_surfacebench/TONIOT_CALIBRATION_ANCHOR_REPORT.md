# TON_IoT Calibration Anchor

This artifact adds a third public real-dataset anchor for XAI-SurfaceBench.
TON_IoT is used as an IoT/IIoT network-flow score-stream source. The calibration
classifier is not a detector contribution.

## Files

- Score stream: `data/toniot/toniot_score_stream.csv`
- Benchmark config: `configs/toniot_calibrated_anchor.json`
- Summary JSON: `data/toniot/toniot_calibration_summary.json`
- Raw CSV: `data/toniot/raw/train_test_network.csv`

## Source And Provenance

- Dataset card used for automation: https://huggingface.co/datasets/codymlewis/TON_IoT_network
- Dataset paper DOI: `10.1109/ACCESS.2020.3022862`
- Raw SHA-256: `26ddc513552de36de6428b2e578efaed2b57504c716dfba847cc0109a64e1974`
- Rows before/after feature deduplication: 211043 / 190474
- Stratified train/test rows: 133331 / 57143
- Train/test feature-hash overlap after deduplication and split: 0
- Test positive-label rate: 0.779

## Calibration Model Metadata

- Model role: calibration metadata only
- Model family: linear SGD logistic classifier with balanced class weights
- ROC AUC: 0.995
- Average precision: 0.998
- Brier score: 0.014
- F1 at threshold 0.5: 0.991
- Numeric features: 16
- Categorical features: proto, service, conn_state, dns_AA, dns_RD, dns_RA, dns_rejected, ssl_version, ssl_cipher, ssl_resumed, ssl_established, http_trans_depth, http_method, http_version, http_orig_mime_types, http_resp_mime_types, weird_name, weird_notice
- Dropped high-cardinality fields: dns_query, dst_ip, http_uri, http_user_agent, src_ip, ssl_issuer, ssl_subject, weird_addl

## Score Bucket Summary

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
| low | 12952 | 0.227 | 0.044 | 0.016 |
| medium | 536 | 0.009 | 0.972 | 0.568 |
| high | 1456 | 0.025 | 0.914 | 0.744 |
| critical | 42199 | 0.738 | 0.998 | 0.989 |

## Attack Family Preview

| Attack family | Rows |
|---|---:|
| normal | 12612 |
| injection | 6026 |
| ddos | 6014 |
| scanning | 6005 |
| password | 5983 |
| dos | 5801 |
| backdoor | 5589 |
| xss | 4421 |
| ransomware | 4377 |
| mitm | 315 |

## Claim Boundary

The TON_IoT anchor strengthens public-data score-stream breadth beyond KDDCup99
and UNSW-NB15. It remains a calibration anchor and does not support claims about
new detector accuracy, hardware deployment readiness, or SME/operator benefit.

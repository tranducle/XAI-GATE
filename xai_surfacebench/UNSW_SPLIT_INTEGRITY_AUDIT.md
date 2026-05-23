# UNSW-NB15 Split-Integrity Audit

This audit checks the public train/test files, the derived score stream, and exact-overlap indicators. It does not prove the historical UNSW-NB15 collection is leakage-free; it verifies the local calibration-anchor artifact used by this manuscript.

## Checks

| Check | Status | Detail |
|---|---|---|
| `raw_train_test_columns_match` | PASS | train columns=45, test columns=45 |
| `score_stream_rows_match_public_test_rows` | PASS | score rows=175341, test rows=175341 |
| `score_stream_uses_test_split_only` | PASS | {'test': 175341} |
| `score_stream_label_counts_match_test` | PASS | score labels={'0': 56000, '1': 119341}, test labels={'0': 56000, '1': 119341} |
| `no_exact_train_test_overlap_excluding_id` | WARN | overlap full rows excluding id=940 |
| `feature_only_train_test_overlap_recorded` | WARN | feature-only overlap excluding id/label/attack_cat=1302 |

## File Summary

| File | Rows | SHA-256 |
|---|---:|---|
| `data/unsw_nb15/raw/train.csv` | 82332 | `734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559` |
| `data/unsw_nb15/raw/test.csv` | 175341 | `bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa` |
| `data/unsw_nb15/unsw_nb15_score_stream.csv` | 175341 | `71e3b5956ed5a63ca96c778be6f79114aa2d50534d63140359cbe45f548fd809` |

## Duplicate/Overlap Notes

- Train duplicate full rows excluding `id`: 26387.
- Test duplicate full rows excluding `id`: 67601.
- Train/test exact full-row overlap excluding `id`: 940.
- Train/test feature-only overlap excluding `id`, `label`, and `attack_cat`: 1302.

## Manuscript-Safe Interpretation

- Safe: the local score stream is generated for the public test split only, with row and label counts matching the public test file.
- Safe: the local pipeline evidence supports a public test-split score-stream calibration-anchor claim, not detector novelty.
- Not safe without additional provenance work: claiming that UNSW-NB15 itself has no temporal, duplicate-flow, or collection-process leakage.

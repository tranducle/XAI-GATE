# Tuned Baseline Envelope Report

Selection rule: for each policy and regime, select the variant with maximum high-risk coverage subject to zero exposure-budget violation. If no variant is feasible, select the maximum-coverage variant and preserve its violation rate.

## Adversarial Explanation-Demand Inflation

| Policy | Selected variant | High-risk coverage | Mean debt | Exposure use | Exposure violation | Packet drop |
|---|---:|---:|---:|---:|---:|---:|
| `always_explain` | `always_default` | 1.000 | 0.0 | 2.869 | 0.652 | 0.000 |
| `budget_only_bexgov` | `bexgov_pressure_0.72` | 0.774 | 5294.8 | 0.918 | 0.000 | 0.000 |
| `fifo_explanation` | `fifo_quota_24` | 1.000 | 0.0 | 2.868 | 0.651 | 0.000 |
| `never_explain` | `never_default` | 0.000 | 20088.8 | 0.000 | 0.000 | 0.000 |
| `rate_limited` | `rate_quota_4` | 0.588 | 17510.8 | 0.877 | 0.000 | 0.000 |
| `static_coarse_full` | `static_cf_h0.86_m0.45` | 0.605 | 7700.0 | 0.689 | 0.000 | 0.000 |
| `static_offload` | `static_off_h0.86_m0.55` | 0.544 | 7576.9 | 0.778 | 0.000 | 0.000 |
| `threshold_explain` | `threshold_0.84` | 0.549 | 10395.0 | 0.592 | 0.000 | 0.000 |
| `xai_gate` | `xai_gate_default` | 0.800 | 1536.4 | 0.995 | 0.000 | 0.000 |

Reviewer interpretation: this table prevents weak-baseline comparison by giving each baseline a tuning envelope before comparison. XAI-Gate should be interpreted against the selected feasible envelope, not only against default threshold settings.

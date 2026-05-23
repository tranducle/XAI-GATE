# Statistical Effect-Size Follow-up

This report uses seed-paired comparisons over existing XAI-SurfaceBench CSV artifacts. It reports raw mean differences, bootstrap 95% confidence intervals over paired seed differences, and exact two-sided sign-test p-values. These checks are follow-up evidence; they should not be described as the original manuscript's descriptive CI procedure.

## Tuned-Envelope Variant Selection

### Synthetic tuned envelope, adversarial regime

| Policy | Selected variant |
|---|---|
| `always_explain` | `always_default` |
| `budget_only_bexgov` | `bexgov_pressure_0.72` |
| `fifo_explanation` | `fifo_quota_24` |
| `never_explain` | `never_default` |
| `rate_limited` | `rate_quota_4` |
| `static_coarse_full` | `static_cf_h0.86_m0.45` |
| `static_offload` | `static_off_h0.86_m0.55` |
| `threshold_explain` | `threshold_0.84` |
| `xai_gate` | `xai_gate_default` |

### UNSW-NB15 tuned envelope, adversarial regime

| Policy | Selected variant |
|---|---|
| `always_explain` | `always_default` |
| `budget_only_bexgov` | `bexgov_pressure_0.88` |
| `fifo_explanation` | `fifo_quota_24` |
| `never_explain` | `never_default` |
| `rate_limited` | `rate_quota_4` |
| `static_coarse_full` | `static_cf_h0.78_m0.45` |
| `static_offload` | `static_off_h0.78_m0.35` |
| `threshold_explain` | `threshold_0.55` |
| `xai_gate` | `xai_gate_default` |

## Key Paired Comparisons

| Family | Dataset | A | B | Metric | n | mean(A-B) | 95% CI | favorable/tie/unfavorable | sign p |
|---|---|---|---|---|---:|---:|---|---|---:|
| default_policy | synthetic | `xai_gate:default` | `threshold_explain:default` | `high_risk_explanation_coverage` | 20 | -0.08401 | [-0.08465, -0.0834] | 0/0/20 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `threshold_explain:default` | `mean_explanation_debt` | 20 | -2099 | [-2130, -2069] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `threshold_explain:default` | `exposure_use` | 20 | -0.3923 | [-0.3964, -0.3886] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `threshold_explain:default` | `exposure_budget_violation_rate` | 20 | -0.2796 | [-0.2813, -0.278] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `budget_only_bexgov:default` | `high_risk_explanation_coverage` | 20 | 0.02676 | [0.02626, 0.02729] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `budget_only_bexgov:default` | `mean_explanation_debt` | 20 | -3766 | [-3797, -3732] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_use` | 20 | 0.07704 | [0.07603, 0.07799] | 0/0/20 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | synthetic | `xai_gate:default` | `rate_limited:default` | `high_risk_explanation_coverage` | 20 | -0.07623 | [-0.07689, -0.07557] | 0/0/20 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `rate_limited:default` | `mean_explanation_debt` | 20 | -3443 | [-3515, -3364] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `rate_limited:default` | `exposure_use` | 20 | -0.4151 | [-0.4187, -0.4114] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `rate_limited:default` | `exposure_budget_violation_rate` | 20 | -0.2916 | [-0.2936, -0.2898] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `static_coarse_full:default` | `high_risk_explanation_coverage` | 20 | -0.08432 | [-0.08487, -0.08376] | 0/0/20 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `static_coarse_full:default` | `mean_explanation_debt` | 20 | -2096 | [-2133, -2063] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `static_coarse_full:default` | `exposure_use` | 20 | -0.3928 | [-0.3972, -0.3881] | 20/0/0 | 1.907e-06 |
| default_policy | synthetic | `xai_gate:default` | `static_coarse_full:default` | `exposure_budget_violation_rate` | 20 | -0.2804 | [-0.283, -0.2778] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `never_explain:never_default` | `high_risk_explanation_coverage` | 20 | 0.8002 | [0.7998, 0.8006] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `never_explain:never_default` | `mean_explanation_debt` | 20 | -1.855e+04 | [-1.862e+04, -1.848e+04] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `never_explain:never_default` | `exposure_use` | 20 | 0.9946 | [0.9939, 0.9953] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `never_explain:never_default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `always_explain:always_default` | `high_risk_explanation_coverage` | 20 | -0.1998 | [-0.2002, -0.1994] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `always_explain:always_default` | `mean_explanation_debt` | 20 | 1536 | [1517, 1554] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `always_explain:always_default` | `exposure_use` | 20 | -1.874 | [-1.878, -1.87] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `always_explain:always_default` | `exposure_budget_violation_rate` | 20 | -0.652 | [-0.6529, -0.651] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.84` | `high_risk_explanation_coverage` | 20 | 0.2512 | [0.2504, 0.2519] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.84` | `mean_explanation_debt` | 20 | -8859 | [-8898, -8815] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.84` | `exposure_use` | 20 | 0.4028 | [0.4003, 0.4053] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.84` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `high_risk_explanation_coverage` | 20 | 0.2119 | [0.2108, 0.2131] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `mean_explanation_debt` | 20 | -1.597e+04 | [-1.606e+04, -1.589e+04] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `exposure_use` | 20 | 0.1181 | [0.1168, 0.1193] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `high_risk_explanation_coverage` | 20 | -0.1996 | [-0.2, -0.1992] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `mean_explanation_debt` | 20 | 1536 | [1517, 1554] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `exposure_use` | 20 | -1.874 | [-1.878, -1.869] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `exposure_budget_violation_rate` | 20 | -0.651 | [-0.6521, -0.6498] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.86_m0.45` | `high_risk_explanation_coverage` | 20 | 0.1949 | [0.1943, 0.1955] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.86_m0.45` | `mean_explanation_debt` | 20 | -6164 | [-6210, -6116] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.86_m0.45` | `exposure_use` | 20 | 0.3061 | [0.3041, 0.308] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.86_m0.45` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.86_m0.55` | `high_risk_explanation_coverage` | 20 | 0.2558 | [0.2552, 0.2564] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.86_m0.55` | `mean_explanation_debt` | 20 | -6040 | [-6087, -5998] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.86_m0.55` | `exposure_use` | 20 | 0.2169 | [0.2145, 0.2192] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.86_m0.55` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.72` | `high_risk_explanation_coverage` | 20 | 0.02649 | [0.02599, 0.02701] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.72` | `mean_explanation_debt` | 20 | -3758 | [-3790, -3725] | 20/0/0 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.72` | `exposure_use` | 20 | 0.07616 | [0.07538, 0.07695] | 0/0/20 | 1.907e-06 |
| tuned_envelope | synthetic | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.72` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | unsw_nb15 | `xai_gate:default` | `threshold_explain:default` | `high_risk_explanation_coverage` | 20 | -0.2579 | [-0.2591, -0.2565] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `threshold_explain:default` | `mean_explanation_debt` | 20 | 3505 | [3474, 3534] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `threshold_explain:default` | `exposure_use` | 20 | -1.309 | [-1.313, -1.304] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `threshold_explain:default` | `exposure_budget_violation_rate` | 20 | -0.5664 | [-0.5674, -0.5655] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `budget_only_bexgov:default` | `high_risk_explanation_coverage` | 20 | -0.06705 | [-0.06835, -0.06571] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `budget_only_bexgov:default` | `mean_explanation_debt` | 20 | -3589 | [-3646, -3537] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_use` | 20 | 0.09277 | [0.09225, 0.09321] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | unsw_nb15 | `xai_gate:default` | `rate_limited:default` | `high_risk_explanation_coverage` | 20 | -0.1789 | [-0.1803, -0.1776] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `rate_limited:default` | `mean_explanation_debt` | 20 | -493.1 | [-570, -418.8] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `rate_limited:default` | `exposure_use` | 20 | -1.126 | [-1.128, -1.124] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `rate_limited:default` | `exposure_budget_violation_rate` | 20 | -0.5297 | [-0.5303, -0.5291] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `static_coarse_full:default` | `high_risk_explanation_coverage` | 20 | -0.258 | [-0.2593, -0.2565] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `static_coarse_full:default` | `mean_explanation_debt` | 20 | 3516 | [3475, 3554] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `static_coarse_full:default` | `exposure_use` | 20 | -1.305 | [-1.31, -1.301] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15 | `xai_gate:default` | `static_coarse_full:default` | `exposure_budget_violation_rate` | 20 | -0.5665 | [-0.5677, -0.5654] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `never_explain:never_default` | `high_risk_explanation_coverage` | 20 | 0.6705 | [0.6692, 0.672] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `never_explain:never_default` | `mean_explanation_debt` | 20 | -2.527e+04 | [-2.537e+04, -2.518e+04] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `never_explain:never_default` | `exposure_use` | 20 | 1 | [1, 1] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `never_explain:never_default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `always_explain:always_default` | `high_risk_explanation_coverage` | 20 | -0.3295 | [-0.3308, -0.328] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `always_explain:always_default` | `mean_explanation_debt` | 20 | 4334 | [4292, 4376] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `always_explain:always_default` | `exposure_use` | 20 | -1.868 | [-1.873, -1.863] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `always_explain:always_default` | `exposure_budget_violation_rate` | 20 | -0.6512 | [-0.6523, -0.6503] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.55` | `high_risk_explanation_coverage` | 20 | -0.2853 | [-0.2866, -0.2838] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.55` | `mean_explanation_debt` | 20 | 4252 | [4208, 4295] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.55` | `exposure_use` | 20 | -1.43 | [-1.435, -1.425] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `threshold_explain:threshold_0.55` | `exposure_budget_violation_rate` | 20 | -0.5883 | [-0.5896, -0.5871] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `high_risk_explanation_coverage` | 20 | 0.2964 | [0.2949, 0.2981] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `mean_explanation_debt` | 20 | -2.088e+04 | [-2.099e+04, -2.077e+04] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `exposure_use` | 20 | 0.05839 | [0.05823, 0.05857] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `rate_limited:rate_quota_4` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `high_risk_explanation_coverage` | 20 | -0.3293 | [-0.3307, -0.3279] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `mean_explanation_debt` | 20 | 4334 | [4292, 4376] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `exposure_use` | 20 | -1.869 | [-1.874, -1.865] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `fifo_explanation:fifo_quota_24` | `exposure_budget_violation_rate` | 20 | -0.6521 | [-0.6532, -0.651] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.78_m0.45` | `high_risk_explanation_coverage` | 20 | -0.2572 | [-0.2585, -0.2557] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.78_m0.45` | `mean_explanation_debt` | 20 | 3495 | [3449, 3538] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.78_m0.45` | `exposure_use` | 20 | -1.31 | [-1.313, -1.307] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_coarse_full:static_cf_h0.78_m0.45` | `exposure_budget_violation_rate` | 20 | -0.5669 | [-0.5677, -0.5661] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.78_m0.35` | `high_risk_explanation_coverage` | 20 | -0.1115 | [-0.113, -0.1099] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.78_m0.35` | `mean_explanation_debt` | 20 | 4164 | [4115, 4213] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.78_m0.35` | `exposure_use` | 20 | -1.717 | [-1.723, -1.712] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `static_offload:static_off_h0.78_m0.35` | `exposure_budget_violation_rate` | 20 | -0.6314 | [-0.6327, -0.6301] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.88` | `high_risk_explanation_coverage` | 20 | -0.06642 | [-0.06772, -0.06503] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.88` | `mean_explanation_debt` | 20 | -3582 | [-3623, -3542] | 20/0/0 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.88` | `exposure_use` | 20 | 0.09268 | [0.09229, 0.09299] | 0/0/20 | 1.907e-06 |
| tuned_envelope | unsw_nb15 | `xai_gate:xai_gate_default` | `budget_only_bexgov:bexgov_pressure_0.88` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `threshold_explain:default` | `high_risk_explanation_coverage` | 20 | -0.1158 | [-0.1172, -0.1145] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `threshold_explain:default` | `mean_explanation_debt` | 20 | -1409 | [-1449, -1365] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `threshold_explain:default` | `exposure_use` | 20 | -0.6868 | [-0.6905, -0.6832] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `threshold_explain:default` | `exposure_budget_violation_rate` | 20 | -0.4068 | [-0.4086, -0.405] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `budget_only_bexgov:default` | `high_risk_explanation_coverage` | 20 | 0.01376 | [0.01238, 0.01521] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `budget_only_bexgov:default` | `mean_explanation_debt` | 20 | -5354 | [-5398, -5311] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_use` | 20 | 0.1069 | [0.1065, 0.1072] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `rate_limited:default` | `high_risk_explanation_coverage` | 20 | -0.103 | [-0.1042, -0.1017] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `rate_limited:default` | `mean_explanation_debt` | 20 | -2702 | [-2791, -2620] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `rate_limited:default` | `exposure_use` | 20 | -0.6998 | [-0.7032, -0.6967] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `rate_limited:default` | `exposure_budget_violation_rate` | 20 | -0.4116 | [-0.4132, -0.4102] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `static_coarse_full:default` | `high_risk_explanation_coverage` | 20 | -0.1158 | [-0.117, -0.1146] | 0/0/20 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `static_coarse_full:default` | `mean_explanation_debt` | 20 | -1396 | [-1428, -1364] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `static_coarse_full:default` | `exposure_use` | 20 | -0.6909 | [-0.6948, -0.6866] | 20/0/0 | 1.907e-06 |
| default_policy | unsw_nb15_deduplicated | `xai_gate:default` | `static_coarse_full:default` | `exposure_budget_violation_rate` | 20 | -0.4091 | [-0.4106, -0.4077] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `threshold_explain:default` | `high_risk_explanation_coverage` | 20 | -0.3397 | [-0.3411, -0.3383] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `threshold_explain:default` | `mean_explanation_debt` | 20 | 5020 | [4970, 5069] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `threshold_explain:default` | `exposure_use` | 20 | -1.666 | [-1.671, -1.662] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `threshold_explain:default` | `exposure_budget_violation_rate` | 20 | -0.625 | [-0.6261, -0.6239] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `budget_only_bexgov:default` | `high_risk_explanation_coverage` | 20 | -0.1127 | [-0.1141, -0.1112] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `budget_only_bexgov:default` | `mean_explanation_debt` | 20 | -1772 | [-1841, -1703] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_use` | 20 | 0.06927 | [0.06876, 0.0698] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `budget_only_bexgov:default` | `exposure_budget_violation_rate` | 20 | 0 | [0, 0] | 0/20/0 | NA |
| default_policy | toniot | `xai_gate:default` | `rate_limited:default` | `high_risk_explanation_coverage` | 20 | -0.1972 | [-0.199, -0.1954] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `rate_limited:default` | `mean_explanation_debt` | 20 | 448.1 | [358.8, 527.2] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `rate_limited:default` | `exposure_use` | 20 | -1.293 | [-1.294, -1.292] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `rate_limited:default` | `exposure_budget_violation_rate` | 20 | -0.564 | [-0.5643, -0.5638] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `static_coarse_full:default` | `high_risk_explanation_coverage` | 20 | -0.3397 | [-0.341, -0.3383] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `static_coarse_full:default` | `mean_explanation_debt` | 20 | 5020 | [4970, 5069] | 0/0/20 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `static_coarse_full:default` | `exposure_use` | 20 | -1.662 | [-1.669, -1.656] | 20/0/0 | 1.907e-06 |
| default_policy | toniot | `xai_gate:default` | `static_coarse_full:default` | `exposure_budget_violation_rate` | 20 | -0.6241 | [-0.6254, -0.6228] | 20/0/0 | 1.907e-06 |

## Interpretation Guardrails

- Positive `mean(A-B)` means policy A has a larger raw value than policy B; whether that is favorable depends on the metric.
- For coverage, larger is favorable. For debt, exposure use, exposure-violation, drop, and delay, smaller is favorable.
- The sign test ignores ties. When all paired differences are identical, `cohens_dz` is omitted in the CSV because the paired standard deviation is zero.
- Use these results to support bounded comparative statements only; they do not establish deployment readiness, operator benefit, or detector novelty.

# XAI-SurfaceBench Experiment Tracker

## Current Execution Status

| Stage | Scope | Status | Primary artifacts |
|---|---|---|---|
| Stage 0 | 2 seeds, 200 slots, all policies/regimes, deterministic rerun check. | Complete; deterministic rerun passed. | `results/sanity_*`, `logs/sanity.jsonl` |
| Stage 1 | 20 seeds, 5,000 slots, mandatory policies across mandatory regimes. | Complete; 1,620 runs. | `results/main_*`, `tables/main_main_metrics.tex` |
| Stage 2 | Demand-inflation sweep: `[1.0, 1.15, 1.35, 1.60, 2.00]`. | Complete; 900 runs. | `results/demand_sweep_*` |
| Stage 3 | Budget frontier sweep for XAI-Gate and baseline envelopes. | Complete; 8,100 runs. | `results/frontier_*` |
| Stage 4 | Required ablations plus default XAI-Gate under adversarial, transient, non-Markovian, and RTT-uncertain regimes. | Complete; 640 runs. | `results/ablations_*` |
| Stage 5 | Robustness sweeps for RTT, cost, service capacity, detection perturbation, and burstiness. | Complete; 4,400 runs. | `results/robustness_*` |
| Stage 6 | Tuned baseline envelope for threshold, rate, FIFO, static fidelity, static offload, and budget-only controls. | Complete; 3,440 runs. | `results/tuned_baseline_envelopes_*`, `BASELINE_ENVELOPE_REPORT.md` |
| Stage 7 | Action-profile sensitivity for exposure, delay, coverage, debt, and cost coefficients. | Complete; 1,360 runs. | `results/profile_sensitivity_*`, `ACTION_PROFILE_SENSITIVITY_REPORT.md` |
| Stage 8 | XAI-Gate weight/budget tuning envelope. | Complete; 1,200 runs. | `results/xai_gate_tuning_envelope_*`, `XAI_GATE_TUNING_REPORT.md` |
| Stage 9 | KDDCup99 no-training calibrated-anchor score stream and benchmark. | Complete; 720 runs plus 50,000-row score stream. | `data/kddcup99_sa_score_stream.csv`, `results/calibrated_anchor_*`, `CALIBRATED_ANCHOR_BENCHMARK_REPORT.md` |
| Stage 10 | Action-profile measurement-lite/provenance. | Complete; 7 action rows over 500 vectors. | `results/action_profile_microbenchmark.csv`, `ACTION_PROFILE_PROVENANCE.md` |
| Stage 11 | Debt-vs-backlog diagnostic and exposure taxonomy. | Complete; deterministic diagnostics. | `results/debt_backlog_diagnostic.csv`, `EXPOSURE_TAXONOMY.md`, `DEBT_BACKLOG_DIAGNOSTIC.md` |
| Stage 12 | UNSW-NB15 real-dataset calibrated-anchor score stream and benchmark. | Complete; 720 runs plus 175,341-row held-out score stream. | `data/unsw_nb15/unsw_nb15_score_stream.csv`, `results/unsw_nb15_calibrated_anchor_*`, `UNSW_NB15_BENCHMARK_REPORT.md` |
| Stage 13 | UNSW-NB15 XAI-Gate tuning envelope. | Complete; 1,200 runs. | `results/unsw_nb15_xai_gate_tuning_envelope_*`, `tables/unsw_nb15_xai_tuning.tex` |
| Stage 14 | UNSW-NB15 tuned-baseline envelope. | Complete; 3,440 runs. | `results/unsw_nb15_tuned_baseline_envelopes_*`, `logs/unsw_nb15_tuned_baseline_envelopes.jsonl` |
| Stage 15 | De-duplicated UNSW-NB15 calibration stream and benchmark rerun. | Complete; 720 runs plus 99,738-row overlap-controlled score stream. | `data/unsw_nb15_dedup/unsw_nb15_dedup_score_stream.csv`, `results/unsw_nb15_deduplicated_anchor_*`, `UNSW_NB15_DEDUP_RERUN_REPORT.md` |
| Stage 16 | Paired seed-level statistical follow-up. | Complete; default, tuned, UNSW, and de-duplicated UNSW comparisons. | `results/statistical_effect_size_followup.*`, `tables/paired_statistical_followup_compact.tex`, `STATISTICAL_EFFECT_SIZE_REPORT.md` |
| Stage 17 | TON_IoT IoT/IIoT calibrated-anchor score stream and benchmark. | Complete; 720 runs plus 57,143-row held-out score stream after feature deduplication and stratified split. | `data/toniot/toniot_score_stream.csv`, `results/toniot_calibrated_anchor_*`, `TONIOT_BENCHMARK_REPORT.md` |

## Acceptance Criteria

- Same command and seed produce deterministic metrics.
- Every stochastic summary reports mean and 95% CI.
- Baselines are compared across documented grids, not handpicked weak settings.
- Tuned-baseline comparisons report the selection rule and preserve infeasible high-coverage baselines with violation rates.
- Action-profile claims disclose profile perturbation sensitivity.
- Outputs include CSV, JSON, TeX, JSONL, and PDF artifacts.
- Manuscript performance claims remain blocked until Stage 1-16 outputs are inspected and `CLAIM_TO_EVIDENCE_MATRIX.md` is updated.

## Notes

- The first wave is no-training plus public calibration anchors: KDDCup99 as a legacy no-training anchor, UNSW-NB15 as a modern held-out score-stream anchor, a de-duplicated UNSW rerun that removes feature-duplicate rows and train-test feature overlap, and TON_IoT as an IoT/IIoT held-out score-stream anchor.
- XAI-Gate uses a hard cumulative exposure-cap guard after the UNSW-NB15 anchor exposed bucket-level overshoot risk under high critical-score mass.
- Edge/gateway hardware benchmarking and executed SME/operator validation remain outside this package. Local action-profile proxy timing and an SME/operator validation protocol are now recorded as boundary artifacts, not deployment evidence.
- Negative or mixed results should be preserved and interpreted rather than tuned away.
- Default `exposure_budget_total` is scaled to the 5,000-slot workload (`18000` units); Stage 3 sweeps `[10000, 18000, 26000]` to expose sensitivity.

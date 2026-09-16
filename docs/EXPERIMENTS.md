# Experiment Catalog

| Experiment family | Public entry point | Purpose |
|---|---|---|
| Core multi-regime benchmark | `experiments/run_benchmark.py` + `configs/main_benchmark.json` | Compare explanation-service policies across nine traffic and uncertainty regimes. |
| Adversarial demand inflation | `configs/demand_inflation.json` | Trace coverage, debt, exposure-accounting use, and packet service as explanation demand increases. |
| Service frontier | `configs/frontier_sweep.json` | Sweep local service capacity and exposure-accounting budgets. |
| Mechanism ablation | `configs/ablation_study.json` | Remove debt, exposure, suspicion, fidelity, offload, and related controller mechanisms. |
| Robustness sweep | `configs/robustness_sweep.json` | Perturb RTT, explanation cost, service capacity, detection matrix, and burstiness. |
| Action-profile sensitivity | `configs/action_profile_sensitivity.json` | Test sensitivity to configurable action profiles. |
| Calibrated public anchors | `scripts/calibrate_*.py` | Construct public KDDCup99, UNSW-NB15, de-duplicated UNSW-NB15, and TON_IoT score streams. |
| Tuning envelopes | `configs/*tuning*.json` | Compare exposure-feasible operating points for XAI-Gate and baselines. |
| Literature-grounded comparison | `configs/literature_comparison_*.json` | Compare XAI-Gate with selective-explanation and resource-aware operational adaptations. |
| Temporal replay | `experiments/run_temporal_replay.py` | Replay timestamp-preserving CICIoT2023 captures with chronological and shuffled-order controls. |
| Estimator mismatch | `experiments/run_estimator_mismatch.py` | Separate controller estimates from fixed realization profiles and quantify estimator error effects. |
| ARM64 timing | `experiments/run_hardware_action_benchmark.py` | Measure LIME, KernelSHAP, coarse, redaction, audit, offload packaging, delay, and no-op service cost. |
| Hardware-calibrated replay | `experiments/run_hardware_calibrated_replay.py` | Propagate measured explanation times into the temporal replay service-capacity model. |
| Statistical follow-up | `experiments/statistical_effect_size_followup.py` | Compute paired differences, bootstrap intervals, and sign-test summaries. |
| Debt/backlog diagnostic | `experiments/debt_backlog_diagnostic.py` | Demonstrate the distinction between raw backlog count and risk-weighted explanation debt. |

## Interpretation boundaries

- The exposure variable is a configured accounting proxy, not an information-theoretic leakage measure.
- The literature-grounded comparators implement operational principles rather than exact source-algorithm reproductions.
- CICIoT2023 replay evidence is bounded to the selected public captures and should not be read as live-enterprise deployment evidence.
- ARM64 timing is platform-specific and resource-envelope-specific.
- Hardware-calibrated replay does not replace hardware-in-the-loop packet forwarding measurements.

# Experiment Catalog

The public release covers the full XAI-SurfaceBench evaluation used for XAI-Gate.

| Experiment family | Public entry point | Purpose |
|---|---|---|
| Core multi-regime benchmark | `experiments/run_benchmark.py` | Compare explanation-service policies across traffic and uncertainty regimes. |
| Demand inflation | `configs/demand_inflation.json` | Stress explanation demand and identify finite-capacity boundaries. |
| Frontier sweep | `configs/frontier_sweep.json` | Sweep local explanation capacity and exposure-accounting budgets. |
| Ablation study | `configs/ablation_study.json` | Remove individual XAI-Gate mechanisms. |
| Robustness sweep | `configs/robustness_sweep.json` | Perturb RTT, explanation cost, service capacity, detection matrix, and burstiness. |
| Action-profile sensitivity | `configs/action_profile_sensitivity.json` | Vary configurable explanation-action profiles. |
| Public score-stream anchors | `scripts/calibrate_*.py` | Calibrate KDDCup99, UNSW-NB15, de-duplicated UNSW-NB15, and TON_IoT score streams. |
| Literature-grounded comparison | `experiments/run_literature_comparison.py` | Compare XAI-Gate with selective-explanation and resource-aware operational adaptations. |
| Timestamp-preserving replay | `experiments/run_temporal_replay.py` | Replay CICIoT2023 captures in chronological and shuffled order. |
| Estimator mismatch | `experiments/run_estimator_mismatch.py` | Separate controller estimates from the fixed realization profile. |
| ARM64 action timing | `experiments/run_hardware_action_benchmark.py` | Measure explanation-service operations under physical and resource-constrained ARM64 conditions. |
| Hardware-calibrated replay | `experiments/run_hardware_calibrated_replay.py` | Propagate measured action times into temporal replay. |

The exposure quantity is a configured governance-accounting proxy, not a direct information-leakage measurement. Hardware timing is platform specific. Literature-grounded comparators implement service-level principles rather than exact source-algorithm reproductions.

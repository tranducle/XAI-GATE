# Reproducibility Guide

All commands below are run from the repository root after installing `requirements.txt` and the package itself with `python -m pip install -e .`.

## 1. Core benchmark and updated baseline studies

```bash
python experiments/sanity_check.py
python experiments/run_benchmark.py --config configs/main_benchmark.json
python experiments/run_benchmark.py --config configs/demand_inflation.json
python experiments/run_benchmark.py --config configs/frontier_sweep.json
python experiments/run_benchmark.py --config configs/ablation_study.json
python experiments/run_benchmark.py --config configs/robustness_sweep.json
python experiments/run_benchmark.py --config configs/action_profile_sensitivity.json
python experiments/run_benchmark.py --config configs/baseline_tuning.json
python experiments/run_benchmark.py --config configs/xai_gate_tuning.json
```

## 2. Public calibrated score-stream anchors

KDDCup99:

```bash
python scripts/calibrate_kddcup99.py
python experiments/run_benchmark.py --config configs/kddcup99_anchor.json
```

UNSW-NB15:

```bash
python scripts/calibrate_unsw_nb15.py
python experiments/run_benchmark.py --config configs/unsw_nb15_anchor.json
python experiments/run_benchmark.py --config configs/unsw_nb15_baseline_tuning.json
python experiments/run_benchmark.py --config configs/unsw_nb15_xai_gate_tuning.json
```

De-duplicated UNSW-NB15:

```bash
python scripts/calibrate_unsw_nb15_deduplicated.py
python scripts/audit_unsw_nb15_split.py
python experiments/run_benchmark.py --config configs/unsw_nb15_deduplicated_anchor.json
```

TON_IoT:

```bash
python scripts/calibrate_toniot.py
python experiments/run_benchmark.py --config configs/toniot_anchor.json
```

## 3. Literature-grounded operational comparison

The two adapted comparators implement service-level principles from selective explanation and resource-aware edge/offload control. They are not claimed to be exact reproductions of the cited source algorithms.

```bash
python experiments/run_benchmark.py --config configs/literature_comparison_main.json
python experiments/run_benchmark.py --config configs/literature_comparison_tuned.json
python experiments/run_benchmark.py --config configs/literature_comparison_unsw_deduplicated.json
python experiments/analyze_literature_comparison.py
```

An optional TON_IoT comparison configuration is also provided:

```bash
python experiments/run_benchmark.py --config configs/literature_comparison_toniot.json
```

## 4. Timestamp-preserving CICIoT2023 replay

```bash
python scripts/download_ciciot2023_temporal.py
python scripts/prepare_ciciot2023_temporal.py
python experiments/run_temporal_replay.py quick
python experiments/run_temporal_replay.py full
python experiments/analyze_temporal_replay.py
```

The chronological and shuffled conditions use the same multiset of one-second slot records. The shuffled control destroys temporal order while preserving per-slot marginals.

## 5. Estimator-mismatch robustness

This study separates the controller-side estimate from the fixed realization profile for compute, exposure accounting, explanation debt, and offload RTT. It includes 0.75x and 1.25x single-factor perturbations plus joint boundary stresses.

The temporal portion requires the CICIoT2023 preparation step above.

```bash
python experiments/run_estimator_mismatch.py quick
python experiments/run_estimator_mismatch.py full
python experiments/analyze_estimator_mismatch.py
```

## 6. ARM64 hardware timing and hardware-calibrated replay

Prepare fixed inputs after the CICIoT2023 temporal preprocessing step:

```bash
python scripts/prepare_hardware_validation_inputs.py
```

The hardware worker measures one action and one condition at a time. Example for the physical host:

```bash
python experiments/run_hardware_action_benchmark.py \
  --condition physical_m2 \
  --action full_kernelshap \
  --repeat 0 \
  --out-dir results/hardware_validation/measurements/physical_m2
```

The documented ARM64 Linux resource envelopes use semantic condition names:

- `arm64_2cpu_4gib`
- `arm64_1cpu_2gib`
- `arm64_0_5cpu_1gib`

Resource limits themselves must be applied by the runtime environment or container manager. After collecting timing observations, use:

```bash
python experiments/analyze_hardware_timing.py
python experiments/run_hardware_calibrated_replay.py
```

`configs/hardware_measured_profiles.json` records the verified reference profiles used in the documented evaluation. Hardware latency should be interpreted as platform-specific measurement evidence, not a universal performance guarantee.

## 7. Additional diagnostics

```bash
python experiments/action_profile_microbenchmark.py
python experiments/debt_backlog_diagnostic.py
python experiments/statistical_effect_size_followup.py
```

## 8. Test suite

```bash
python -m pytest -q
```

## Output policy

The public source tree intentionally excludes generated outputs. Runtime artifacts are stored in ignored directories such as `data/`, `results/`, `logs/`, `tables/`, `figures/`, and generated documentation subdirectories. Preserve configuration files and the release checksum manifest when archiving a reproduction run.

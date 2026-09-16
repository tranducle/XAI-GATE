# Reproducibility Guide

Run all commands from the repository root after creating a virtual environment and installing `requirements.txt` plus the package with `python -m pip install -e .`.

## Core benchmark and updated baseline studies

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

## Public calibrated score-stream anchors

```bash
python scripts/calibrate_kddcup99.py
python scripts/calibrate_unsw_nb15.py
python scripts/calibrate_unsw_nb15_deduplicated.py
python scripts/calibrate_toniot.py
```

The generated score streams are written under ignored `data/` paths. Use the corresponding public configuration in `configs/` with `experiments/run_benchmark.py`.

For the de-duplicated UNSW-NB15 workflow, an exact feature-hash overlap audit is available as:

```bash
python scripts/audit_unsw_nb15_split.py TRAIN.csv TEST.csv
```

## Literature-grounded operational comparison

The adapted comparators implement service-level principles from selective explanation and resource-aware edge/offload control. They are not exact reproductions of the cited source algorithms.

```bash
python experiments/run_literature_comparison.py main
python experiments/run_literature_comparison.py tuned
python experiments/run_literature_comparison.py unsw
python experiments/run_literature_comparison.py toniot
python experiments/analyze_literature_comparison.py results/literature_comparison_tuned_summary.csv
```

## Timestamp-preserving CICIoT2023 replay

Place or acquire the selected parquet captures under `data/ciciot2023_temporal/raw/`, then:

```bash
python scripts/download_ciciot2023_temporal.py
python scripts/prepare_ciciot2023_temporal.py
python experiments/run_temporal_replay.py quick
python experiments/run_temporal_replay.py full
python experiments/analyze_temporal_replay.py
```

Chronological and shuffled conditions use the same multiset of complete one-second slot records. The shuffled control destroys temporal order while preserving the per-slot marginals.

## Estimator-mismatch robustness

The controller-side compute, exposure-accounting, debt, and RTT estimates are perturbed while the realization profile and workload are fixed.

```bash
python experiments/run_estimator_mismatch.py quick
python experiments/run_estimator_mismatch.py full
python experiments/analyze_estimator_mismatch.py
```

## ARM64 timing and hardware-calibrated replay

Prepare fixed inputs after temporal preprocessing:

```bash
python scripts/prepare_hardware_validation_inputs.py
```

Example physical-host timing command:

```bash
python experiments/run_hardware_action_benchmark.py \
  --condition physical_m2 \
  --action full_kernelshap \
  --repeat 0
```

The semantic resource-envelope condition names are `arm64_2cpu_4gib`, `arm64_1cpu_2gib`, and `arm64_0_5cpu_1gib`. CPU and memory limits are applied by the runtime environment; the condition name records provenance only.

After collecting each action under each condition:

```bash
python experiments/analyze_hardware_timing.py
python experiments/run_hardware_calibrated_replay.py
```

## Additional diagnostics

```bash
python experiments/action_profile_microbenchmark.py
python experiments/debt_backlog_diagnostic.py
python experiments/statistical_effect_size_followup.py PATH_TO_RUNS.csv
```

## Verification

```bash
python scripts/release_audit.py
python -m pytest -q
python experiments/sanity_check.py
```

Raw datasets, generated result files, manuscript sources, rendered figures, model objects, local workspace metadata, and machine-specific paths are outside the public source release.

# XAI-Gate and XAI-SurfaceBench

This repository provides the public research implementation of **XAI-Gate**, a detector-agnostic service-governance layer for explainable network intrusion detection, together with **XAI-SurfaceBench**, the evaluation framework used to study explanation service behavior under finite capacity, adversarial explanation demand, uncertainty, and resource constraints.

XAI-Gate operates after alert generation. It does not replace the detector or explainer. The controller chooses among seven explanation-service actions: suppress, coarse explanation, delay, full local explanation, offload, audit-only logging, and redacted release.

The exposure quantity used by the controller is a **configured governance-accounting proxy**. It is not a direct measurement or guarantee of real-world information leakage.

## What is included

The current public release contains code and configurations for:

- the multi-regime XAI-SurfaceBench benchmark;
- adversarial explanation-demand sweeps and service-frontier sweeps;
- mechanism ablations and action-profile sensitivity;
- public calibrated score-stream anchors for KDDCup99, UNSW-NB15, de-duplicated UNSW-NB15, and TON_IoT;
- XAI-Gate and baseline tuning-envelope studies;
- literature-grounded selective-explanation and resource-aware operational comparisons;
- timestamp-preserving CICIoT2023 replay with chronological and shuffled-order controls;
- estimator-mismatch robustness with fixed realization profiles;
- physical and resource-constrained ARM64 explanation timing utilities;
- hardware-calibrated temporal replay;
- statistical effect-size follow-up, action-profile microbenchmarking, and debt/backlog diagnostics.

Raw datasets, generated result files, manuscript files, manuscript figures, editorial-response materials, local workspace metadata, and machine-specific paths are intentionally excluded.

## Repository layout

```text
.
├── README.md
├── DATA.md
├── REPRODUCIBILITY.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── configs/          # Public experiment configurations
├── docs/             # Experiment catalog and reference outputs
├── experiments/      # Benchmark and analysis entry points
├── scripts/          # Dataset preparation and calibration utilities
├── src/xai_surfacebench/
└── tests/
```

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q
```

Run the deterministic sanity check:

```bash
python experiments/sanity_check.py
```

Run the main benchmark:

```bash
python experiments/run_benchmark.py --config configs/main_benchmark.json
```

Runtime artifacts are written to ignored directories such as `results/`, `logs/`, `tables/`, `figures/`, and `data/`. They are not part of the public source release.

For the complete evaluation workflow, see [REPRODUCIBILITY.md](REPRODUCIBILITY.md). For dataset provenance and acquisition boundaries, see [DATA.md](DATA.md).

## Reproducibility boundary

The benchmark code fixes experiment seeds and configuration parameters for the documented runs. Public-dataset workflows may require network access and can change in runtime if an upstream host changes file availability or packaging. Hardware timing is inherently platform-specific; the included hardware utilities are intended to reproduce the measurement protocol rather than promise identical latency on different machines.

## License

MIT License. See [LICENSE](LICENSE).

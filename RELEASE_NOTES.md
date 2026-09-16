# Public Experiment Refresh

This release refreshes the public XAI-Gate/XAI-SurfaceBench research implementation with the complete experiment families used in the current evaluation.

## Added or refreshed

- multi-regime benchmark, demand-inflation and service-frontier sweeps;
- XAI-Gate ablations, robustness sweeps, profile sensitivity, and tuning envelopes;
- KDDCup99, UNSW-NB15, de-duplicated UNSW-NB15, and TON_IoT calibration workflows;
- literature-grounded selective-explanation and resource-aware operational comparators;
- timestamp-preserving CICIoT2023 replay with matched shuffled-order controls;
- controller estimator-mismatch robustness under a fixed realization profile;
- ARM64 explanation-action timing and hardware-calibrated temporal replay;
- paired effect-size follow-up and debt/backlog diagnostics.

## Naming cleanup

Development-only experiment identifiers and machine-specific resource aliases are not used in the public tree. Public paths use semantic names such as `temporal_replay`, `estimator_mismatch`, `hardware_validation`, and `literature_comparison`.

## Publication boundary

The repository intentionally excludes manuscript sources, rendered manuscript figures, raw datasets, generated result tables, model artifacts, local workspace metadata, credentials, and machine-specific paths. Runtime outputs are ignored by Git.

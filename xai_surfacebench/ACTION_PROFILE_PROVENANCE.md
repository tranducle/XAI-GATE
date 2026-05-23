# Action-Profile Provenance

This artifact documents the source of each default action-profile value used by
XAI-SurfaceBench. Runtime values are local proxy measurements over deterministic
synthetic alert vectors. They are not hardware deployment benchmarks; they justify
relative compute tiers and are bounded by the existing action-profile sensitivity
experiment.

## Environment

```json
{
  "hardware": {
    "cpu_brand": "Apple M2",
    "gpu_summary": [
      "Chipset Model: Apple M2",
      "Total Number of Cores: 10",
      "Metal Support: Metal 4"
    ],
    "logical_cpu": 8,
    "machine": "arm64",
    "memory_gb": 16.0,
    "model": "Mac14,15",
    "os": "Darwin 25.5.0",
    "physical_cpu": 8,
    "privacy_note": "Serial numbers and user identifiers are intentionally excluded.",
    "python": "3.14.3"
  },
  "measurement_scope": "local proxy measurement on the listed host, not edge/gateway deployment benchmark",
  "normalization": "median runtime divided by full-action median runtime",
  "repeats": 20,
  "vectors": 500,
  "width": 64
}
```

## Profile Table

| Action | Default compute | Measured compute norm | Median us | Exposure | Delay | Provenance |
|---|---:|---:|---:|---:|---:|---|
| none | 0.00 | 0.000 | 0.035 | 0.00 | 0.00 | administrative no-op |
| coarse | 0.28 | 0.022 | 5.817 | 0.10 | 0.25 | top-feature local proxy |
| full | 1.00 | 1.000 | 266.582 | 0.85 | 0.85 | perturbation-style local proxy |
| offload | 0.16 | 0.148 | 39.525 | 1.00 | 1.30 | request packaging proxy plus modeled RTT |
| audit | 0.62 | 0.038 | 10.008 | 0.34 | 0.70 | metadata serialization and hash proxy |
| redact | 0.46 | 0.043 | 11.371 | 0.08 | 0.55 | top-feature masking proxy |
| delay | 0.00 | 0.000 | 0.033 | 0.00 | 1.00 | administrative deferral |

## Interpretation

- `full` is the normalization baseline for local high-fidelity explanation cost.
- `offload` measures local request packaging only; its larger delay profile comes
  from modeled RTT/service latency, not from local serialization time.
- Coverage, high-risk coverage, exposure, and delay values remain design
  parameters. Their influence is tested in the profile-sensitivity stage.

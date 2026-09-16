# Verified Reference Outputs

These values are reference outputs for the documented configurations. They are included to support reproduction checks and are not universal performance guarantees.

## Default adversarial explanation-demand condition

For the documented default XAI-Gate operating point:

- high-risk explanation coverage: approximately **0.800**;
- mean explanation debt: approximately **1,562**;
- configured exposure-accounting use: approximately **0.995**;
- configured exposure-budget violation rate: **0**.

## Literature-grounded operational comparison

For the documented synthetic tuned operating points:

| Method | High-risk coverage | Mean debt | Exposure use | Violation rate |
|---|---:|---:|---:|---:|
| XAI-Gate | 0.813 | 1612.0 | 0.987 | 0.000 |
| Resource-aware adaptation | 0.884 | 3656.2 | 1.387 | 0.279 |
| Selective-explanation adaptation | 0.504 | 6440.9 | 0.844 | 0.000 |

The comparison is a multi-objective tradeoff, not an overall ranking.

## Timestamp-preserving CICIoT2023 replay

- non-flood attack captures: high-risk coverage remains approximately **0.84** under the documented XAI-Gate configuration;
- high-volume DDoS capture: high-risk coverage approximately **0.0083**, packet drop approximately **0.9843**;
- chronological minus shuffled packet-drop difference: approximately **+0.177552** on PingSweep and **+0.140261** on PortScan;
- maximum absolute chronological-versus-shuffled debt difference: approximately **14,838.3**.

## Estimator-mismatch robustness

Under the documented adversarial workload:

| Controller profile | HR coverage | Mean debt | Realized exposure | Violation rate |
|---|---:|---:|---:|---:|
| Nominal | 0.800 | 1528.5 | 0.994 | 0.000 |
| Exposure estimate 25% low | 0.820 | 748.5 | 1.250 | 0.374 |
| Exposure estimate 25% high | 0.761 | 2526.4 | 0.756 | 0.000 |

This result demonstrates calibration sensitivity of the accounting proxy. It does not establish a bound on real-world information leakage.

## ARM64 timing reference

Physical fanless Apple M2, CPU-only, documented configuration:

- LIME median / p95 latency: approximately **1.552 / 2.869 ms**;
- KernelSHAP median / p95 latency: approximately **3.847 / 5.161 ms**.

Under the most constrained documented native ARM64 Linux envelope, KernelSHAP p95 is approximately **54.885 ms**, with a throttled-period fraction of approximately **0.989**. Hardware-calibrated replay records zero one-worker overload slots for XAI-Gate across the measured profiles, while the always-explain and threshold policies reach approximately **0.8742** maximum overload fraction in the most constrained KernelSHAP profile.

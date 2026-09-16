# Verified Reference Outputs

These values summarize verified runs for the documented configurations and are intended as reproduction targets, not universal guarantees.

## Default adversarial explanation demand

XAI-Gate: high-risk coverage approximately 0.800, mean explanation debt approximately 1,562, exposure-accounting use approximately 0.995, and zero configured exposure-budget violations.

## Literature-grounded operational comparison

| Method | High-risk coverage | Mean debt | Exposure use | Violation rate |
|---|---:|---:|---:|---:|
| XAI-Gate | 0.813 | 1612.0 | 0.987 | 0.000 |
| Resource-aware adaptation | 0.884 | 3656.2 | 1.387 | 0.279 |
| Selective-explanation adaptation | 0.504 | 6440.9 | 0.844 | 0.000 |

## Timestamp-preserving CICIoT2023 replay

For non-flood attack captures, XAI-Gate high-risk coverage remains near 0.84. On the high-volume DDoS capture, high-risk coverage is approximately 0.0083 and packet drop approximately 0.9843. Chronological versus shuffled ordering materially changes queue and debt behavior.

## Estimator mismatch

A 25% underestimate of the exposure coefficient raises realized accounting exposure above the controller's estimate and produces nonzero configured exposure-budget violations. A conservative 25% overestimate preserves zero violations at the cost of lower coverage and higher debt.

## ARM64 timing

On the documented physical fanless Apple M2 condition, LIME median/p95 latency is approximately 1.552/2.869 ms and KernelSHAP approximately 3.847/5.161 ms. Under the most constrained documented native ARM64 Linux envelope, KernelSHAP p95 is approximately 54.885 ms.

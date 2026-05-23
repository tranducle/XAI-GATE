# XAI-Gate Tuning Envelope Report

This stage gives XAI-Gate the same kind of tuning budget previously given to
threshold, FIFO, rate, static-fidelity, static-offload, and budget-only baselines.
Variants are ranked by high-risk coverage among zero-exposure-violation operating
points.

Default XAI-Gate: HR coverage 0.801, debt 1549.8, exposure use 0.995, violation 0.000

Best selected variant: `high_exposure_budget` with HR coverage 0.835,
mean debt 1018.7, exposure use 0.949, and
exposure violation 0.000.

| Rank | Variant | HR coverage | Debt | Exposure use | Violation |
|---:|---|---:|---:|---:|---:|
| 1 | high_exposure_budget | 0.835 | 1018.7 | 0.949 | 0.000 |
| 2 | suspicion_strict | 0.817 | 1666.4 | 0.988 | 0.000 |
| 3 | exposure_strict | 0.813 | 1609.0 | 0.987 | 0.000 |
| 4 | balanced_coverage | 0.812 | 1209.7 | 0.987 | 0.000 |
| 5 | high_local_budget | 0.809 | 981.0 | 0.968 | 0.000 |
| 6 | rtt_strict | 0.808 | 1542.8 | 0.994 | 0.000 |
| 7 | coverage_heavy_budget20 | 0.805 | 1240.1 | 0.985 | 0.000 |
| 8 | coverage_heavy | 0.801 | 1515.2 | 0.997 | 0.000 |

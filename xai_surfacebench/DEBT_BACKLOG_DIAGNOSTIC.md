# Explanation Debt vs Item Count Diagnostic

Explanation debt is not a renamed queue length or item count. A count records
unserved items, whereas explanation debt weights unserved obligations by risk and by the
remaining explanation work after a selected action. The diagnostic below holds
the number of alert obligations fixed and varies risk bucket and action fidelity.

| Scenario | Items | Risk bucket | Action | Coverage | Debt | Debt/item |
|---|---:|---|---|---:|---:|---:|
| same count, low-risk delayed | 100 | low | delay | 0.00 | 102.8 | 1.028 |
| same count, critical delayed | 100 | critical | delay | 0.00 | 165.1 | 1.651 |
| same count, high-risk coarse | 100 | high | coarse | 0.45 | 62.7 | 0.627 |
| same count, high-risk audit | 100 | high | audit | 0.72 | 31.9 | 0.319 |
| same count, full explanation | 100 | critical | full | 1.00 | 0.0 | 0.000 |

The first two rows have the same item count, but critical delayed alerts
produce larger debt than low-risk delayed alerts. The third and fourth rows have
the same item count and high-risk bucket, but audit creates less debt than
coarse explanation because it satisfies more of the explanation obligation.

# Action-Profile Sensitivity Report

This report perturbs the abstract action profiles used by XAI-Gate. It tests whether the main conclusion is an artifact of one exact exposure, delay, coverage, cost, or debt coefficient.

| Regime | Coverage range | Debt range | Exposure range | Max exposure violation |
|---|---:|---:|---:|---:|
| `adversarial_explanation_flood` | 0.626--0.868 | 402.2--3124.1 | 0.884--1.000 | 0.127 |
| `non_markovian` | 0.647--0.857 | 42.3--371.5 | 0.621--0.917 | 0.000 |
| `rtt_uncertainty` | 0.754--0.908 | 0.1--4.0 | 0.490--0.656 | 0.000 |
| `transient_overload` | 0.595--0.816 | 1287.4--3394.1 | 0.879--1.000 | 0.149 |

Reviewer interpretation: profile sensitivity should be used to bound the strength of action-profile claims. A manuscript claim is credible only if it is stable across this perturbation envelope or explicitly reported as profile-dependent.

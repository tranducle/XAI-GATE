# XAI-Gate Simulation Summary

Lower packet-drop, lower debt, and bounded leakage are better. Explanation coverage should be interpreted jointly with packet QoS.

| Regime | Policy | Drop rate | Coverage | Mean debt | Leakage used | Offload | Audit | Redact |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| adversarial_explanation_flood | never_explain | 0.1675 | 0.000 | 0.00 | 0.0 | 0.000 | 0.000 | 0.000 |
| adversarial_explanation_flood | budget_only_bexgov | 0.1734 | 0.044 | 3009.91 | 1883.5 | 0.000 | 0.000 | 0.000 |
| adversarial_explanation_flood | fifo_explanation | 0.2474 | 0.250 | 97652.02 | 10791.5 | 0.000 | 0.000 | 0.000 |
| adversarial_explanation_flood | xai_gate | 0.2508 | 0.167 | 0.00 | 10158.2 | 0.019 | 0.429 | 0.000 |
| adversarial_explanation_flood | rate_limited | 0.2761 | 0.118 | 0.00 | 10026.9 | 0.000 | 0.000 | 0.000 |
| adversarial_explanation_flood | static_offload | 0.3672 | 0.688 | 0.00 | 118921.4 | 0.859 | 0.000 | 0.000 |
| adversarial_explanation_flood | threshold_explain | 0.9068 | 0.601 | 0.00 | 128343.0 | 0.000 | 0.000 | 0.000 |
| adversarial_explanation_flood | always_explain | 0.9153 | 1.000 | 0.00 | 213067.0 | 0.000 | 0.000 | 0.000 |
| bursty | never_explain | 0.0754 | 0.000 | 0.00 | 0.0 | 0.000 | 0.000 | 0.000 |
| bursty | budget_only_bexgov | 0.0773 | 0.158 | 3300.88 | 3541.7 | 0.000 | 0.000 | 0.000 |
| bursty | xai_gate | 0.0840 | 0.209 | 0.00 | 6364.2 | 0.001 | 0.088 | 0.000 |
| bursty | rate_limited | 0.0949 | 0.093 | 0.00 | 2534.2 | 0.000 | 0.000 | 0.000 |
| bursty | fifo_explanation | 0.0992 | 0.431 | 17879.94 | 20144.8 | 0.000 | 0.000 | 0.000 |
| bursty | static_offload | 0.1062 | 0.543 | 0.00 | 30078.8 | 0.678 | 0.000 | 0.000 |
| bursty | threshold_explain | 0.2123 | 0.358 | 0.00 | 24501.0 | 0.000 | 0.000 | 0.000 |
| bursty | always_explain | 0.7232 | 1.000 | 0.00 | 78821.0 | 0.000 | 0.000 | 0.000 |
| non_markovian | static_offload | 0.0000 | 0.543 | 0.00 | 24022.1 | 0.679 | 0.000 | 0.000 |
| non_markovian | xai_gate | 0.0000 | 0.304 | 0.00 | 7860.4 | 0.000 | 0.000 | 0.000 |
| non_markovian | budget_only_bexgov | 0.0000 | 0.253 | 10693.01 | 2918.3 | 0.000 | 0.000 | 0.000 |
| non_markovian | rate_limited | 0.0000 | 0.094 | 0.00 | 2038.3 | 0.000 | 0.000 | 0.000 |
| non_markovian | never_explain | 0.0000 | 0.000 | 0.00 | 0.0 | 0.000 | 0.000 | 0.000 |
| non_markovian | fifo_explanation | 0.0060 | 0.525 | 9495.55 | 23430.7 | 0.000 | 0.000 | 0.000 |
| non_markovian | threshold_explain | 0.0161 | 0.360 | 0.00 | 20345.0 | 0.000 | 0.000 | 0.000 |
| non_markovian | always_explain | 0.6533 | 1.000 | 0.00 | 69213.0 | 0.000 | 0.000 | 0.000 |
| poisson | static_offload | 0.0000 | 0.541 | 0.00 | 22785.8 | 0.676 | 0.000 | 0.000 |
| poisson | threshold_explain | 0.0000 | 0.356 | 0.00 | 18517.0 | 0.000 | 0.000 | 0.000 |
| poisson | xai_gate | 0.0000 | 0.304 | 0.00 | 7614.1 | 0.000 | 0.000 | 0.000 |
| poisson | budget_only_bexgov | 0.0000 | 0.256 | 9834.96 | 3140.7 | 0.000 | 0.000 | 0.000 |
| poisson | rate_limited | 0.0000 | 0.093 | 0.00 | 1939.7 | 0.000 | 0.000 | 0.000 |
| poisson | never_explain | 0.0000 | 0.000 | 0.00 | 0.0 | 0.000 | 0.000 | 0.000 |
| poisson | fifo_explanation | 0.0046 | 0.556 | 8291.56 | 25034.6 | 0.000 | 0.000 | 0.000 |
| poisson | always_explain | 0.6143 | 1.000 | 0.00 | 66754.0 | 0.000 | 0.000 | 0.000 |

# Exposure Taxonomy and Offload Trust Model

XAI-Gate treats explanations as information-bearing service outputs. Exposure is
an abstract accounting variable for five disclosure channels: feature attribution,
model-behavior cues, policy-threshold cues, offload data-path disclosure, and audit
trace disclosure.

| Action | Feature disclosure | Model behavior | Policy/threshold disclosure | Offload path | Audit trace | Exposure |
|---|---|---|---|---|---|---:|
| none | none | none | none | none | none | 0.00 |
| coarse | top feature groups | low | low | none | none | 0.10 |
| full | full attribution vector | high | medium | none | low | 0.85 |
| offload | sanitized alert vector | high | medium | managed fog/cloud service | medium | 1.00 |
| audit | metadata summary | medium | medium | none | high | 0.34 |
| redact | masked attribution | low | low | none | low | 0.08 |
| delay | none now | none now | low | none | queue marker | 0.00 |

## Offload Model

The offload action sends a sanitized alert feature vector, calibrated score,
requested explainer type, and policy metadata to a managed fog/cloud explanation
service. Raw packet payload is outside the default data path. The higher exposure
profile reflects both data-path disclosure and richer returned explanation content.
The RTT belief in XAI-Gate represents the observed round-trip service delay of this
managed explanation tier.

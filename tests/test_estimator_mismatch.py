from pathlib import Path
from xai_surfacebench.estimation import assignment_disagreement, simulate_estimator_variant


def config():
    return {"name":"estimator_test","slots":25,"base":{"alert_probability":0.25,"local_explanation_budget":18.0,"exposure_budget_total":18000.0}}


def test_estimator_variants_share_workload_and_return_finite_metrics():
    nominal = {"name":"nominal","estimation_multipliers":{"compute":1.0,"exposure":1.0,"debt":1.0,"rtt":1.0}}
    low = {"name":"exposure_under_25","estimation_multipliers":{"compute":1.0,"exposure":0.75,"debt":1.0,"rtt":1.0}}
    nrow, ntrace = simulate_estimator_variant(config(), config_dir=Path('.'), seed=1, regime="adversarial_explanation_flood", variant=nominal)
    lrow, ltrace = simulate_estimator_variant(config(), config_dir=Path('.'), seed=1, regime="adversarial_explanation_flood", variant=low)
    assert len(ntrace) == len(ltrace) == 25
    assert nrow["realization_profile_fixed"] and lrow["realization_profile_fixed"]
    assert 0.0 <= assignment_disagreement(ntrace, ltrace) <= 1.0
    assert lrow["estimate_exposure_multiplier"] == 0.75

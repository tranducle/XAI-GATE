"""Deterministic XAI-SurfaceBench simulation and reporting core.

The simulator is intentionally no-training by default. Optional calibration
files can replace the synthetic score-bucket profile, but they are treated as
input metadata rather than as a detector-learning contribution.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


MANDATORY_POLICIES = [
    "never_explain",
    "always_explain",
    "threshold_explain",
    "rate_limited",
    "fifo_explanation",
    "static_coarse_full",
    "static_offload",
    "budget_only_bexgov",
    "xai_gate",
]

SOTA_ADAPTED_POLICIES = [
    "selective_explanations_adapted",
    "resource_aware_offload_adapted",
]

MANDATORY_REGIMES = [
    "poisson",
    "bursty",
    "self_similar",
    "markov_modulated",
    "non_markovian",
    "transient_overload",
    "adversarial_explanation_flood",
    "rtt_uncertainty",
    "detection_matrix_perturbation",
]

ABLATIONS = [
    "no_debt",
    "no_exposure_budget",
    "no_offload",
    "no_suspicion",
    "no_fidelity_control",
    "threshold_only_scoring",
    "no_rtt_robustness",
]

PRIMARY_METRICS = [
    "packet_drop_rate",
    "mean_packet_delay",
    "mean_packet_queue",
    "explanation_coverage",
    "high_risk_explanation_coverage",
    "mean_explanation_delay",
    "mean_explanation_debt",
    "exposure_use",
]

SECONDARY_METRICS = [
    "offload_rate",
    "audit_rate",
    "redaction_rate",
    "local_compute_load",
    "attacker_trigger_gain",
    "budget_violation_rate",
    "exposure_budget_violation_rate",
]

BUCKETS: List[Tuple[str, float]] = [
    ("low", 0.25),
    ("medium", 0.55),
    ("high", 0.78),
    ("critical", 0.93),
]

HIGH_RISK_PROBABILITY = {
    "low": 0.04,
    "medium": 0.22,
    "high": 0.70,
    "critical": 0.93,
}

DEFAULT_BUCKET_PROBS = {
    "low": 0.45,
    "medium": 0.30,
    "high": 0.18,
    "critical": 0.07,
}

ACTION_PROFILES = {
    "none": {
        "coverage": 0.0,
        "high_risk_coverage": 0.0,
        "compute": 0.0,
        "exposure": 0.0,
        "delay": 0.0,
        "offload": 0.0,
        "audit": 0.0,
        "redaction": 0.0,
    },
    "coarse": {
        "coverage": 0.45,
        "high_risk_coverage": 0.38,
        "compute": 0.28,
        "exposure": 0.10,
        "delay": 0.25,
        "offload": 0.0,
        "audit": 0.0,
        "redaction": 0.0,
    },
    "full": {
        "coverage": 1.00,
        "high_risk_coverage": 1.00,
        "compute": 1.00,
        "exposure": 0.85,
        "delay": 0.85,
        "offload": 0.0,
        "audit": 0.0,
        "redaction": 0.0,
    },
    "offload": {
        "coverage": 0.90,
        "high_risk_coverage": 0.84,
        "compute": 0.16,
        "exposure": 1.00,
        "delay": 1.30,
        "offload": 1.0,
        "audit": 0.0,
        "redaction": 0.0,
    },
    "audit": {
        "coverage": 0.72,
        "high_risk_coverage": 0.80,
        "compute": 0.62,
        "exposure": 0.34,
        "delay": 0.70,
        "offload": 0.0,
        "audit": 1.0,
        "redaction": 0.0,
    },
    "redact": {
        "coverage": 0.58,
        "high_risk_coverage": 0.64,
        "compute": 0.46,
        "exposure": 0.08,
        "delay": 0.55,
        "offload": 0.0,
        "audit": 0.0,
        "redaction": 1.0,
    },
    "delay": {
        "coverage": 0.0,
        "high_risk_coverage": 0.0,
        "compute": 0.0,
        "exposure": 0.0,
        "delay": 1.0,
        "offload": 0.0,
        "audit": 0.0,
        "redaction": 0.0,
    },
}

DEFAULT_BASE = {
    "packet_arrival_rate": 45.0,
    "packet_service_rate": 52.0,
    "packet_buffer_capacity": 240.0,
    "packet_service_interference": 0.055,
    "alert_probability": 0.15,
    "local_explanation_budget": 18.0,
    "exposure_budget_total": 18000.0,
    "exposure_budget_per_slot": 0.55,
    "debt_service_rate": 3.5,
    "high_risk_threshold": 0.75,
    "threshold": 0.72,
    "static_high_threshold": 0.78,
    "static_medium_threshold": 0.45,
    "static_offload_threshold": 0.78,
    "static_offload_medium_threshold": 0.45,
    "rate_limit_quota": 10.0,
    "fifo_service_quota": 12.0,
    "bexgov_pressure_threshold": 0.72,
    "selective_alpha": 0.80,
    "resource_offload_pressure_threshold": 0.65,
    "resource_offload_rtt_max": 0.30,
    "resource_high_threshold": 0.68,
    "resource_medium_threshold": 0.42,
    "burstiness_scale": 1.0,
    "rtt_noise_scale": 1.0,
    "detection_matrix_noise": 0.0,
    "explanation_cost_scale": 1.0,
    "attack_arrival_multiplier": 1.0,
    "service_capacity_multiplier": 1.0,
    "debt_increment_scale": 1.0,
    "xai_gate_hard_exposure_cap": True,
}

DEFAULT_XAI_GATE_WEIGHTS = {
    "coverage": 2.25,
    "high_risk": 1.40,
    "compute": 0.62,
    "debt": 0.78,
    "exposure": 1.05,
    "suspicion": 0.90,
    "packet_pressure": 0.60,
    "rtt": 0.75,
}

DEFAULT_ESTIMATION_MULTIPLIERS = {
    "compute": 1.0,
    "exposure": 1.0,
    "debt": 1.0,
    "rtt": 1.0,
}


@dataclass
class SimulationState:
    packet_queue: float = 0.0
    explanation_debt: float = 0.0
    exposure_total: float = 0.0
    markov_high: bool = False
    self_similar_level: float = 1.0
    correlated_level: float = 1.0
    fifo_backlog: float = 0.0
    rate_tokens: float = 0.0
    rtt_belief: float = 1.0
    suspicion_level: float = 0.0
    slot_local_load: float = 0.0


@dataclass
class CalibrationProfile:
    bucket_probs: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_BUCKET_PROBS))
    high_risk_probs: Dict[str, float] = field(default_factory=lambda: dict(HIGH_RISK_PROBABILITY))
    status: str = "synthetic_default"
    rows_used: int = 0
    summary: Dict[str, Any] = field(default_factory=dict)


def stable_seed(base_seed: int, *parts: Any) -> int:
    """Return a deterministic 32-bit seed independent of Python hash randomization."""

    payload = "|".join(str(p) for p in (base_seed, *parts))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def deep_merge(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def action_profiles_for(config: Mapping[str, Any], variant: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    """Return action profiles after applying config-level and variant-level overrides."""

    profiles = {action: dict(profile) for action, profile in ACTION_PROFILES.items()}
    for source in (config.get("action_profile_overrides", {}), variant.get("action_profile_overrides", {})):
        if not source:
            continue
        if not isinstance(source, Mapping):
            raise ValueError("action_profile_overrides must be a mapping")
        for action, updates in source.items():
            if action not in profiles:
                raise ValueError(f"Unknown action in action_profile_overrides: {action}")
            if not isinstance(updates, Mapping):
                raise ValueError(f"Overrides for action {action} must be a mapping")
            for key, value in updates.items():
                if key not in profiles[action]:
                    raise ValueError(f"Unknown profile field {key} for action {action}")
                profiles[action][key] = float(value)
    return profiles


def estimation_multipliers_for(variant: Mapping[str, Any]) -> Dict[str, float]:
    """Return validated controller-estimation multipliers."""

    multipliers = dict(DEFAULT_ESTIMATION_MULTIPLIERS)
    supplied = variant.get("estimation_multipliers", {})
    if supplied:
        if not isinstance(supplied, Mapping):
            raise ValueError("estimation_multipliers must be a mapping")
        unknown = set(supplied) - set(multipliers)
        if unknown:
            raise ValueError(f"Unknown estimation multiplier(s): {sorted(unknown)}")
        for key, value in supplied.items():
            parsed = float(value)
            if not math.isfinite(parsed) or parsed <= 0.0:
                raise ValueError(f"Estimation multiplier {key} must be finite and positive")
            multipliers[key] = parsed
    return multipliers


def estimated_action_profiles(
    realization_profiles: Mapping[str, Mapping[str, float]],
    multipliers: Mapping[str, float],
) -> Dict[str, Dict[str, float]]:
    """Build controller-side action estimates without changing realization values."""

    compute_multiplier = float(multipliers["compute"])
    exposure_multiplier = float(multipliers["exposure"])
    estimated = {action: dict(profile) for action, profile in realization_profiles.items()}
    for profile in estimated.values():
        profile["compute"] = float(profile["compute"]) * compute_multiplier
        profile["exposure"] = float(profile["exposure"]) * exposure_multiplier
    return estimated


def budget_exceeded(value: float, budget: float) -> bool:
    """Compare a cumulative value with its budget using a tiny floating-point tolerance."""

    tolerance = max(1e-9, abs(float(budget)) * 1e-12)
    return float(value) > float(budget) + tolerance


def budget_overshoot(value: float, budget: float) -> float:
    """Return meaningful positive budget overshoot, ignoring machine-precision residue."""

    if not budget_exceeded(value, budget):
        return 0.0
    return max(0.0, float(value) - float(budget))


def normalize_probs(probs: Mapping[str, float]) -> Dict[str, float]:
    cleaned = {name: max(0.0, float(probs.get(name, 0.0))) for name, _ in BUCKETS}
    total = sum(cleaned.values())
    if total <= 0:
        return dict(DEFAULT_BUCKET_PROBS)
    return {name: value / total for name, value in cleaned.items()}


def shift_bucket_probs(probs: Mapping[str, float], severity_shift: float) -> Dict[str, float]:
    """Shift mass toward higher or lower buckets while preserving order and total mass."""

    weights = {}
    for index, (name, _) in enumerate(BUCKETS):
        multiplier = math.exp(severity_shift * (index - 1.5))
        weights[name] = probs.get(name, 0.0) * multiplier
    return normalize_probs(weights)


def sample_poisson(lam: float, rng: random.Random) -> int:
    lam = max(0.0, lam)
    if lam == 0:
        return 0
    if lam < 30.0:
        limit = math.exp(-lam)
        k = 0
        product = 1.0
        while product > limit:
            k += 1
            product *= rng.random()
        return k - 1
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def sample_binomial(n: int, p: float, rng: random.Random) -> int:
    if n <= 0:
        return 0
    p = min(1.0, max(0.0, p))
    if p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    if n < 80:
        return sum(1 for _ in range(n) if rng.random() < p)
    mean = n * p
    sd = math.sqrt(n * p * (1.0 - p))
    return max(0, min(n, int(round(rng.gauss(mean, sd)))))


def sample_bucket_counts(alerts: int, probs: Mapping[str, float], rng: random.Random) -> Dict[str, int]:
    remaining = alerts
    counts: Dict[str, int] = {}
    remaining_prob = 1.0
    normalized = normalize_probs(probs)
    for name, _ in BUCKETS[:-1]:
        if remaining <= 0:
            counts[name] = 0
            continue
        conditional = normalized[name] / max(remaining_prob, 1e-12)
        count = sample_binomial(remaining, conditional, rng)
        counts[name] = count
        remaining -= count
        remaining_prob -= normalized[name]
    counts[BUCKETS[-1][0]] = max(0, remaining)
    return counts


def load_calibration_profile(config: Mapping[str, Any], config_dir: Path) -> CalibrationProfile:
    calibration = config.get("calibration", {})
    score_stream = calibration.get("score_stream_path")
    summary_path = calibration.get("training_summary_path")
    max_rows = int(calibration.get("max_rows", 250000))
    if not score_stream:
        return CalibrationProfile()

    stream_path = Path(score_stream)
    if not stream_path.is_absolute():
        stream_path = (config_dir / stream_path).resolve()
    if not stream_path.exists():
        return CalibrationProfile(status=f"calibration_missing:{stream_path}")

    bucket_counts = {name: 0 for name, _ in BUCKETS}
    high_counts = {name: 0.0 for name, _ in BUCKETS}
    rows = 0
    with stream_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if rows >= max_rows:
                break
            try:
                score = float(row.get("score", row.get("calibrated_score", "")))
            except ValueError:
                continue
            label_raw = row.get("true_label", row.get("label", "0"))
            try:
                label = float(label_raw)
            except ValueError:
                label = 0.0
            bucket = score_to_bucket(score)
            bucket_counts[bucket] += 1
            high_counts[bucket] += 1.0 if label >= 0.5 else 0.0
            rows += 1

    if rows == 0:
        return CalibrationProfile(status=f"calibration_empty:{stream_path}")

    summary: Dict[str, Any] = {}
    if summary_path:
        summary_file = Path(summary_path)
        if not summary_file.is_absolute():
            summary_file = (config_dir / summary_file).resolve()
        if summary_file.exists():
            summary = load_json(summary_file)

    bucket_probs = normalize_probs(bucket_counts)
    high_risk_probs = {}
    for name, _ in BUCKETS:
        denom = max(bucket_counts[name], 1)
        high_risk_probs[name] = min(1.0, max(0.0, high_counts[name] / denom))
    return CalibrationProfile(
        bucket_probs=bucket_probs,
        high_risk_probs=high_risk_probs,
        status=f"calibrated:{stream_path}",
        rows_used=rows,
        summary=summary,
    )


def score_to_bucket(score: float) -> str:
    if score >= 0.86:
        return "critical"
    if score >= 0.68:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def regime_signals(
    regime: str,
    slot: int,
    slots: int,
    state: SimulationState,
    base: Mapping[str, float],
    calibration: CalibrationProfile,
    rng: random.Random,
) -> Dict[str, Any]:
    burstiness = float(base["burstiness_scale"])
    detection_noise = float(base["detection_matrix_noise"])
    attack_multiplier = float(base["attack_arrival_multiplier"])
    rtt_scale = float(base["rtt_noise_scale"])
    arrival_multiplier = 1.0
    alert_probability = float(base["alert_probability"])
    severity_shift = 0.0
    suspicion = 0.05
    rtt_uncertainty = 0.08 * rtt_scale

    if regime == "poisson":
        pass
    elif regime == "bursty":
        phase = slot % 90
        if phase < 18:
            arrival_multiplier = 1.0 + 1.35 * burstiness
            alert_probability *= 1.35
            severity_shift += 0.22
        else:
            arrival_multiplier = max(0.55, 0.92 - 0.10 * burstiness)
    elif regime == "self_similar":
        pareto = min(6.0, rng.paretovariate(1.45))
        state.self_similar_level = 0.93 * state.self_similar_level + 0.07 * pareto
        arrival_multiplier = max(0.55, min(3.8, 0.45 + 0.60 * state.self_similar_level * burstiness))
        alert_probability *= max(0.8, min(1.7, 0.9 + 0.18 * state.self_similar_level))
        severity_shift += 0.06 * state.self_similar_level
    elif regime == "markov_modulated":
        if state.markov_high:
            state.markov_high = rng.random() > 0.10
        else:
            state.markov_high = rng.random() < 0.045
        if state.markov_high:
            arrival_multiplier = 2.15
            alert_probability *= 1.55
            severity_shift += 0.38
            suspicion = 0.42
        else:
            arrival_multiplier = 0.78
    elif regime == "non_markovian":
        noise = rng.gauss(1.0, 0.42)
        shock = 2.1 if (slot % 260 in range(30, 56)) else 0.0
        state.correlated_level = 0.88 * state.correlated_level + 0.12 * max(0.25, noise + shock)
        arrival_multiplier = max(0.55, min(4.0, state.correlated_level * burstiness))
        alert_probability *= max(0.75, min(1.95, 0.78 + 0.24 * state.correlated_level))
        severity_shift += 0.18 * max(0.0, state.correlated_level - 1.0)
        suspicion = min(0.85, 0.10 + 0.18 * state.correlated_level)
    elif regime == "transient_overload":
        progress = slot / max(slots, 1)
        if 0.40 <= progress <= 0.62:
            arrival_multiplier = 2.55
            alert_probability *= 1.45
            severity_shift += 0.26
            suspicion = 0.55
        else:
            arrival_multiplier = 0.88
    elif regime == "adversarial_explanation_flood":
        arrival_multiplier = 1.00 + 0.28 * (attack_multiplier - 1.0)
        alert_probability *= 1.80 * attack_multiplier
        severity_shift += 0.48 + 0.22 * (attack_multiplier - 1.0)
        suspicion = min(0.95, 0.50 + 0.18 * attack_multiplier)
    elif regime == "rtt_uncertainty":
        rtt_uncertainty = 0.35 * rtt_scale + abs(rng.gauss(0.0, 0.08 * rtt_scale))
        state.rtt_belief = max(0.2, 0.80 * state.rtt_belief + 0.20 * (1.0 + rtt_uncertainty))
        alert_probability *= 1.08
        severity_shift += 0.08
    elif regime == "detection_matrix_perturbation":
        matrix_noise = max(detection_noise, 0.18)
        severity_shift += matrix_noise * rng.choice([-1.0, 1.0])
        alert_probability *= 1.0 + 0.35 * matrix_noise
        suspicion = 0.20 + 0.50 * matrix_noise
    else:
        raise ValueError(f"Unknown regime: {regime}")

    alert_probability = min(0.95, max(0.01, alert_probability))
    bucket_probs = shift_bucket_probs(calibration.bucket_probs, severity_shift)
    high_risk_probs = dict(calibration.high_risk_probs)
    if regime == "detection_matrix_perturbation":
        perturb = max(detection_noise, 0.18)
        for name in high_risk_probs:
            high_risk_probs[name] = min(1.0, max(0.0, high_risk_probs[name] + rng.gauss(0.0, 0.10 * perturb)))

    return {
        "arrival_multiplier": max(0.01, arrival_multiplier),
        "alert_probability": alert_probability,
        "bucket_probs": bucket_probs,
        "high_risk_probs": high_risk_probs,
        "suspicion": min(1.0, max(0.0, suspicion)),
        "rtt_uncertainty": max(0.0, rtt_uncertainty),
    }


def ablation_flags(ablation: str) -> Dict[str, bool]:
    flags = {
        "enable_debt": True,
        "enable_exposure_budget": True,
        "enable_offload": True,
        "enable_suspicion": True,
        "enable_fidelity_control": True,
        "threshold_only_scoring": False,
        "enable_rtt_robustness": True,
    }
    if ablation == "default":
        return flags
    if ablation == "no_debt":
        flags["enable_debt"] = False
    elif ablation == "no_exposure_budget":
        flags["enable_exposure_budget"] = False
    elif ablation == "no_offload":
        flags["enable_offload"] = False
    elif ablation == "no_suspicion":
        flags["enable_suspicion"] = False
    elif ablation == "no_fidelity_control":
        flags["enable_fidelity_control"] = False
    elif ablation == "threshold_only_scoring":
        flags["threshold_only_scoring"] = True
    elif ablation == "no_rtt_robustness":
        flags["enable_rtt_robustness"] = False
    else:
        raise ValueError(f"Unknown ablation: {ablation}")
    return flags


def choose_static_action(policy: str, score: float, state: SimulationState, base: Mapping[str, float]) -> str:
    threshold = float(base["threshold"])
    if policy == "never_explain":
        return "none"
    if policy == "always_explain":
        return "full"
    if policy == "threshold_explain":
        if score >= threshold:
            return "full"
        if score >= threshold - 0.20:
            return "coarse"
        return "none"
    if policy == "static_coarse_full":
        if score >= float(base["static_high_threshold"]):
            return "full"
        if score >= float(base["static_medium_threshold"]):
            return "coarse"
        return "none"
    if policy == "static_offload":
        if score >= float(base["static_offload_threshold"]):
            return "offload"
        if score >= float(base["static_offload_medium_threshold"]):
            return "coarse"
        return "none"
    if policy == "budget_only_bexgov":
        budget_pressure = state.slot_local_load / max(float(base["local_explanation_budget"]), 1e-9)
        exposure_pressure = state.exposure_total / max(float(base["exposure_budget_total"]), 1e-9)
        if budget_pressure > float(base["bexgov_pressure_threshold"]):
            return "delay" if score >= 0.70 else "none"
        if exposure_pressure > 0.88:
            return "redact" if score >= 0.55 else "none"
        if score >= 0.86:
            return "audit"
        if score >= 0.68:
            return "full"
        if score >= 0.45:
            return "coarse"
        return "none"
    raise ValueError(f"Static chooser cannot handle policy: {policy}")


def choose_resource_aware_action(
    score: float,
    state: SimulationState,
    base: Mapping[str, float],
    signals: Mapping[str, Any],
    count: float,
    action_profiles: Mapping[str, Mapping[str, float]],
) -> str:
    """Service-level edge/offload comparator adapted from resource-aware IDS literature.

    The comparator intentionally does not observe explanation debt, cumulative
    exposure, or adversarial suspicion. It uses only detector score, local
    explanation pressure, and current RTT uncertainty.
    """

    medium_threshold = float(base["resource_medium_threshold"])
    high_threshold = float(base["resource_high_threshold"])
    if score < medium_threshold:
        return "none"
    if score < high_threshold:
        return "coarse"

    local_budget = max(float(base["local_explanation_budget"]), 1e-9)
    full_local_cost = (
        count
        * float(action_profiles["full"]["compute"])
        * float(base["explanation_cost_scale"])
    )
    projected_pressure = (state.slot_local_load + full_local_cost) / local_budget
    rtt_uncertainty = float(signals["rtt_uncertainty"])
    if (
        projected_pressure >= float(base["resource_offload_pressure_threshold"])
        and rtt_uncertainty <= float(base["resource_offload_rtt_max"])
    ):
        return "offload"
    return "full"


def choose_xai_gate_action(
    score: float,
    state: SimulationState,
    base: Mapping[str, float],
    weights: Mapping[str, float],
    flags: Mapping[str, bool],
    signals: Mapping[str, Any],
    action_profiles: Mapping[str, Mapping[str, float]],
) -> str:
    threshold = float(base["threshold"])
    if flags["threshold_only_scoring"]:
        return "full" if score >= threshold else "none"

    actions = ["none", "coarse", "full", "audit", "redact", "delay"]
    if flags["enable_offload"]:
        actions.append("offload")
    if not flags["enable_fidelity_control"]:
        actions = [action for action in actions if action in {"none", "full", "offload", "delay"}]

    local_budget = max(float(base["local_explanation_budget"]), 1e-9)
    exposure_budget = max(float(base["exposure_budget_total"]), 1e-9)
    packet_pressure = state.packet_queue / max(float(base["packet_buffer_capacity"]), 1e-9)
    debt_pressure = state.explanation_debt / max(local_budget * 10.0, 1e-9)
    exposure_pressure = state.exposure_total / exposure_budget
    suspicion = float(signals["suspicion"]) if flags["enable_suspicion"] else 0.0
    rtt_uncertainty = float(signals["rtt_uncertainty"]) if flags["enable_rtt_robustness"] else 0.0

    if flags["enable_exposure_budget"]:
        if exposure_pressure >= 1.0:
            actions = [action for action in actions if action_profiles[action]["exposure"] <= 0.0]
        elif exposure_pressure >= 0.90:
            actions = [action for action in actions if action_profiles[action]["exposure"] <= 0.10]
        elif exposure_pressure >= 0.75:
            actions = [action for action in actions if action_profiles[action]["exposure"] <= 0.35]

    best_action = "none"
    best_score = -1e18
    for action in actions:
        profile = action_profiles[action]
        coverage_value = weights["coverage"] * profile["coverage"] * score
        high_risk_value = weights["high_risk"] * profile["high_risk_coverage"] * max(0.0, score - 0.62)
        compute_penalty = weights["compute"] * profile["compute"] * (1.0 + state.slot_local_load / local_budget)
        packet_penalty = weights["packet_pressure"] * profile["compute"] * packet_pressure
        exposure_penalty = 0.0
        if flags["enable_exposure_budget"]:
            projected_exposure = state.exposure_total + profile["exposure"]
            projected_pressure = projected_exposure / exposure_budget
            exposure_penalty = weights["exposure"] * profile["exposure"] * (0.30 + projected_pressure)
            if projected_pressure > 1.0:
                exposure_penalty += 4.0 * (projected_pressure - 1.0)
        suspicion_penalty = weights["suspicion"] * suspicion * profile["exposure"]
        debt_penalty = 0.0
        if flags["enable_debt"]:
            residual_debt = (1.0 - profile["coverage"]) * (0.5 + score)
            debt_penalty = weights["debt"] * residual_debt * (0.45 + debt_pressure)
            if action == "delay":
                debt_penalty += weights["debt"] * (1.0 + debt_pressure)
        rtt_penalty = weights["rtt"] * rtt_uncertainty if action == "offload" else 0.0
        utility = coverage_value + high_risk_value - compute_penalty - packet_penalty
        utility -= exposure_penalty + suspicion_penalty + debt_penalty + rtt_penalty
        if action == "none" and score >= 0.80:
            utility -= 1.8 + debt_pressure
        if action == "delay" and score < 0.60:
            utility -= 0.4
        if utility > best_score:
            best_score = utility
            best_action = action
    return best_action


def sorted_buckets_for_policy(policy: str) -> Iterable[Tuple[str, float]]:
    if policy == "fifo_explanation":
        return BUCKETS
    return reversed(BUCKETS)


def allocate_actions(
    policy: str,
    bucket_counts: Mapping[str, int],
    state: SimulationState,
    base: Mapping[str, float],
    weights: Mapping[str, float],
    flags: Mapping[str, bool],
    signals: Mapping[str, Any],
    action_profiles: Mapping[str, Mapping[str, float]],
    controller_state: Optional[SimulationState] = None,
    controller_action_profiles: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Dict[str, Dict[str, float]]:
    """Return nested action counts by bucket: {bucket: {action: count}}."""

    action_counts: Dict[str, Dict[str, float]] = {name: {} for name, _ in BUCKETS}
    decision_state = controller_state if controller_state is not None else state
    decision_profiles = controller_action_profiles if controller_action_profiles is not None else action_profiles
    if policy == "rate_limited":
        state.rate_tokens = min(float(base["rate_limit_quota"]) * 3.0, state.rate_tokens + float(base["rate_limit_quota"]))
    if policy == "fifo_explanation":
        state.fifo_backlog += sum(bucket_counts.values())
        available = min(state.fifo_backlog, float(base["fifo_service_quota"]))
    else:
        available = 0.0

    planned_exposure = decision_state.exposure_total
    exposure_budget = max(float(base["exposure_budget_total"]), 1e-9)
    hard_exposure_cap = bool(base.get("xai_gate_hard_exposure_cap", True)) and flags["enable_exposure_budget"]

    def add_action(bucket_name: str, action_name: str, count: float) -> None:
        if count <= 0:
            return
        action_counts[bucket_name][action_name] = action_counts[bucket_name].get(action_name, 0.0) + count
        state.slot_local_load += count * action_profiles[action_name]["compute"] * float(base["explanation_cost_scale"])
        if decision_state is not state:
            decision_state.slot_local_load += (
                count
                * decision_profiles[action_name]["compute"]
                * float(base["explanation_cost_scale"])
            )

    def fallback_actions(score_value: float, preferred: str) -> List[str]:
        if not flags["enable_fidelity_control"]:
            order = [preferred, "delay", "none"]
        elif score_value >= 0.68:
            order = [preferred, "redact", "coarse", "audit", "delay", "none"]
        elif score_value >= 0.42:
            order = [preferred, "coarse", "redact", "delay", "none"]
        else:
            order = [preferred, "none", "delay"]
        deduped: List[str] = []
        for action_name in order:
            if action_name in decision_profiles and action_name not in deduped:
                deduped.append(action_name)
        return deduped

    def add_xai_gate_action_with_cap(bucket_name: str, score_value: float, preferred: str, count: float) -> None:
        """Split an XAI-Gate bucket so cumulative exposure never exceeds budget."""

        nonlocal planned_exposure
        if not hard_exposure_cap:
            add_action(bucket_name, preferred, count)
            planned_exposure += count * decision_profiles[preferred]["exposure"]
            return

        remaining_count = count
        for action_name in fallback_actions(score_value, preferred):
            if remaining_count <= 1e-12:
                break
            exposure_per_unit = float(decision_profiles[action_name]["exposure"])
            if exposure_per_unit <= 0.0:
                take = remaining_count
            else:
                remaining_exposure = max(0.0, exposure_budget - planned_exposure)
                take = min(remaining_count, remaining_exposure / exposure_per_unit)
            if take <= 1e-12:
                continue
            add_action(bucket_name, action_name, take)
            planned_exposure += take * exposure_per_unit
            remaining_count -= take
        if remaining_count > 1e-9:
            add_action(bucket_name, "delay", remaining_count)

    for bucket, score in sorted_buckets_for_policy(policy):
        remaining = float(bucket_counts.get(bucket, 0))
        if remaining <= 0:
            continue
        if policy == "rate_limited":
            explain_now = min(remaining, state.rate_tokens)
            state.rate_tokens -= explain_now
            if explain_now > 0:
                action = "full" if score >= float(base["threshold"]) else "coarse"
                action_counts[bucket][action] = action_counts[bucket].get(action, 0.0) + explain_now
                state.slot_local_load += explain_now * action_profiles[action]["compute"] * float(base["explanation_cost_scale"])
            delayed = remaining - explain_now
            if delayed > 0:
                action_counts[bucket]["delay"] = action_counts[bucket].get("delay", 0.0) + delayed
            continue
        if policy == "fifo_explanation":
            explain_now = min(remaining, available)
            available -= explain_now
            state.fifo_backlog = max(0.0, state.fifo_backlog - explain_now)
            if explain_now > 0:
                action_counts[bucket]["full"] = action_counts[bucket].get("full", 0.0) + explain_now
                state.slot_local_load += explain_now * action_profiles["full"]["compute"] * float(base["explanation_cost_scale"])
            delayed = remaining - explain_now
            if delayed > 0:
                action_counts[bucket]["delay"] = action_counts[bucket].get("delay", 0.0) + delayed
            continue
        if policy == "xai_gate":
            action = choose_xai_gate_action(
                score,
                decision_state,
                base,
                weights,
                flags,
                signals,
                decision_profiles,
            )
            add_xai_gate_action_with_cap(bucket, score, action, remaining)
            continue
        if policy == "selective_explanations_adapted":
            alpha = min(1.0, max(0.0, float(base["selective_alpha"])))
            coarse_count = remaining * alpha
            full_count = remaining - coarse_count
            add_action(bucket, "coarse", coarse_count)
            add_action(bucket, "full", full_count)
            continue
        if policy == "resource_aware_offload_adapted":
            action = choose_resource_aware_action(
                score,
                state,
                base,
                signals,
                remaining,
                action_profiles,
            )
            add_action(bucket, action, remaining)
            continue
        action = choose_static_action(policy, score, state, base)
        add_action(bucket, action, remaining)
    if decision_state is not state and policy == "xai_gate":
        decision_state.exposure_total = planned_exposure
    return action_counts


def accumulate_action_metrics(
    acc: Dict[str, float],
    bucket: str,
    action: str,
    count: float,
    state: SimulationState,
    base: Mapping[str, float],
    high_risk_probs: Mapping[str, float],
    signals: Mapping[str, Any],
    action_profiles: Mapping[str, Mapping[str, float]],
) -> None:
    if count <= 0:
        return
    profile = action_profiles[action]
    cost_scale = float(base["explanation_cost_scale"])
    high_risk_count = count * float(high_risk_probs[bucket])
    acc["alerts"] += count
    acc["high_risk_alerts"] += high_risk_count
    acc["explained_units"] += count * profile["coverage"]
    acc["high_risk_explained_units"] += high_risk_count * profile["high_risk_coverage"]
    acc["explanation_delay_sum"] += count * profile["delay"]
    if action == "offload":
        acc["explanation_delay_sum"] += count * float(signals["rtt_uncertainty"])
    debt_increment = count * (1.0 - profile["coverage"]) * (0.65 + 0.70 * high_risk_probs[bucket])
    if action == "delay":
        debt_increment += 0.35 * count
    debt_increment *= float(base["debt_increment_scale"])
    state.explanation_debt += debt_increment
    state.exposure_total += count * profile["exposure"]
    acc["offload_count"] += count * profile["offload"]
    acc["audit_count"] += count * profile["audit"]
    acc["redaction_count"] += count * profile["redaction"]
    acc["local_compute_units"] += count * profile["compute"] * cost_scale


def simulate_run(
    config: Mapping[str, Any],
    seed: int,
    policy: str,
    regime: str,
    variant: Mapping[str, Any],
    calibration: CalibrationProfile,
    collect_action_trace: bool = False,
) -> Dict[str, Any]:
    base = deep_merge(DEFAULT_BASE, config.get("base", {}))
    base = deep_merge(base, variant.get("base", {}))
    weights = deep_merge(DEFAULT_XAI_GATE_WEIGHTS, config.get("xai_gate_weights", {}))
    weights = deep_merge(weights, variant.get("xai_gate_weights", {}))
    action_profiles = action_profiles_for(config, variant)
    estimation_enabled = "estimation_multipliers" in variant
    estimation_multipliers = estimation_multipliers_for(variant)
    decision_action_profiles = (
        estimated_action_profiles(action_profiles, estimation_multipliers)
        if estimation_enabled
        else action_profiles
    )
    ablation = str(variant.get("ablation", "default"))
    flags = ablation_flags(ablation)
    workload_seed_group = variant.get("workload_seed_group", variant.get("name", "default"))
    rng = random.Random(
        stable_seed(seed, config.get("name", "experiment"), policy, regime, workload_seed_group)
    )
    slots = int(config["slots"])
    state = SimulationState()
    controller_state = SimulationState() if estimation_enabled else state
    workload_hasher = hashlib.sha256()
    action_trace: List[Dict[str, Dict[str, float]]] = []
    acc: Dict[str, float] = {
        "arrivals": 0.0,
        "dropped": 0.0,
        "served": 0.0,
        "queue_sum": 0.0,
        "delay_sum": 0.0,
        "alerts": 0.0,
        "high_risk_alerts": 0.0,
        "explained_units": 0.0,
        "high_risk_explained_units": 0.0,
        "explanation_delay_sum": 0.0,
        "debt_sum": 0.0,
        "offload_count": 0.0,
        "audit_count": 0.0,
        "redaction_count": 0.0,
        "local_compute_units": 0.0,
        "budget_violation_slots": 0.0,
        "exposure_violation_slots": 0.0,
        "baseline_expected_alerts": 0.0,
    }

    for slot in range(slots):
        state.slot_local_load = 0.0
        if controller_state is not state:
            controller_state.packet_queue = state.packet_queue
            controller_state.explanation_debt = (
                state.explanation_debt * float(estimation_multipliers["debt"])
            )
            controller_state.slot_local_load = 0.0
        signals = regime_signals(regime, slot, slots, state, base, calibration, rng)
        packet_lambda = float(base["packet_arrival_rate"]) * float(signals["arrival_multiplier"])
        arrivals = sample_poisson(packet_lambda, rng)
        alerts = sample_binomial(arrivals, float(signals["alert_probability"]), rng)
        bucket_counts = sample_bucket_counts(alerts, signals["bucket_probs"], rng)

        workload_hasher.update(
            json.dumps(
                {
                    "slot": slot,
                    "arrivals": arrivals,
                    "alerts": alerts,
                    "bucket_counts": bucket_counts,
                    "suspicion": float(signals["suspicion"]),
                    "rtt_uncertainty": float(signals["rtt_uncertainty"]),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )

        decision_signals = signals
        if estimation_enabled:
            decision_signals = dict(signals)
            decision_signals["rtt_uncertainty"] = (
                float(signals["rtt_uncertainty"]) * float(estimation_multipliers["rtt"])
            )

        action_counts = allocate_actions(
            policy,
            bucket_counts,
            state,
            base,
            weights,
            flags,
            decision_signals,
            action_profiles,
            controller_state=controller_state if estimation_enabled else None,
            controller_action_profiles=decision_action_profiles if estimation_enabled else None,
        )
        if collect_action_trace:
            action_trace.append(
                {
                    bucket: {action: float(count) for action, count in sorted(actions.items())}
                    for bucket, actions in action_counts.items()
                }
            )
        for bucket, actions in action_counts.items():
            for action, count in actions.items():
                accumulate_action_metrics(
                    acc,
                    bucket,
                    action,
                    count,
                    state,
                    base,
                    signals["high_risk_probs"],
                    signals,
                    action_profiles,
                )

        service_rate = float(base["packet_service_rate"]) * float(base["service_capacity_multiplier"])
        service_rate -= float(base["packet_service_interference"]) * state.slot_local_load
        service_rate = max(1.0, service_rate)

        state.packet_queue += arrivals
        served = min(state.packet_queue, service_rate)
        state.packet_queue -= served
        if state.packet_queue > float(base["packet_buffer_capacity"]):
            overflow = state.packet_queue - float(base["packet_buffer_capacity"])
            acc["dropped"] += overflow
            state.packet_queue = float(base["packet_buffer_capacity"])

        spare_budget = max(0.0, float(base["local_explanation_budget"]) - state.slot_local_load)
        debt_service = min(state.explanation_debt, spare_budget * float(base["debt_service_rate"]) / max(float(base["local_explanation_budget"]), 1e-9))
        state.explanation_debt = max(0.0, state.explanation_debt - debt_service)

        acc["arrivals"] += arrivals
        acc["served"] += served
        acc["queue_sum"] += state.packet_queue
        acc["delay_sum"] += state.packet_queue / max(served, 1.0)
        acc["debt_sum"] += state.explanation_debt
        if state.slot_local_load > float(base["local_explanation_budget"]):
            acc["budget_violation_slots"] += 1.0
        if budget_exceeded(state.exposure_total, float(base["exposure_budget_total"])):
            acc["exposure_violation_slots"] += 1.0
        acc["baseline_expected_alerts"] += arrivals * float(base["alert_probability"])

        if state.packet_queue < -1e-9 or state.explanation_debt < -1e-9:
            raise AssertionError("Negative queue/debt state detected")

    alerts_total = max(acc["alerts"], 1.0)
    high_total = max(acc["high_risk_alerts"], 1.0)
    arrivals_total = max(acc["arrivals"], 1.0)
    exposure_budget = max(float(base["exposure_budget_total"]), 1e-9)
    metrics = {
        "stage": str(config.get("name", "experiment")),
        "variant": str(variant.get("name", "default")),
        "ablation": ablation,
        "policy": policy,
        "regime": regime,
        "seed": seed,
        "slots": slots,
        "packet_drop_rate": acc["dropped"] / arrivals_total,
        "mean_packet_delay": acc["delay_sum"] / slots,
        "mean_packet_queue": acc["queue_sum"] / slots,
        "explanation_coverage": acc["explained_units"] / alerts_total,
        "high_risk_explanation_coverage": acc["high_risk_explained_units"] / high_total,
        "mean_explanation_delay": acc["explanation_delay_sum"] / alerts_total,
        "mean_explanation_debt": acc["debt_sum"] / slots,
        "exposure_use": state.exposure_total / exposure_budget,
        "offload_rate": acc["offload_count"] / alerts_total,
        "audit_rate": acc["audit_count"] / alerts_total,
        "redaction_rate": acc["redaction_count"] / alerts_total,
        "local_compute_load": acc["local_compute_units"] / slots,
        "attacker_trigger_gain": max(0.0, (acc["alerts"] / max(acc["baseline_expected_alerts"], 1.0)) - 1.0),
        "budget_violation_rate": acc["budget_violation_slots"] / slots,
        "exposure_budget_violation_rate": acc["exposure_violation_slots"] / slots,
        "alerts_per_slot": acc["alerts"] / slots,
        "packets_per_slot": acc["arrivals"] / slots,
        "calibration_status": calibration.status,
        "workload_hash": workload_hasher.hexdigest(),
    }
    if estimation_enabled:
        metrics.update(
            {
                "estimate_compute_multiplier": float(estimation_multipliers["compute"]),
                "estimate_exposure_multiplier": float(estimation_multipliers["exposure"]),
                "estimate_debt_multiplier": float(estimation_multipliers["debt"]),
                "estimate_rtt_multiplier": float(estimation_multipliers["rtt"]),
                "estimated_exposure_use": controller_state.exposure_total / exposure_budget,
                "actual_exposure_overshoot": budget_overshoot(state.exposure_total, exposure_budget),
            }
        )
    if collect_action_trace:
        metrics["_action_trace"] = action_trace
    for key in PRIMARY_METRICS + SECONDARY_METRICS + ["alerts_per_slot", "packets_per_slot"]:
        value = metrics[key]
        if not math.isfinite(float(value)):
            raise AssertionError(f"Non-finite metric {key} in {policy}/{regime}/{seed}")
        if key not in {"attacker_trigger_gain"} and float(value) < -1e-10:
            raise AssertionError(f"Negative metric {key} in {policy}/{regime}/{seed}")
    return metrics


def expand_variants(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    experiment_type = str(config.get("experiment_type", "standard"))
    if experiment_type == "standard":
        return [{"name": "default", "ablation": "default"}]
    if experiment_type == "demand_sweep":
        return [
            {
                "name": f"attack_{value:.2f}",
                "ablation": "default",
                "base": {"attack_arrival_multiplier": float(value)},
            }
            for value in config.get("sweep", {}).get("attack_arrival_multiplier", [1.0])
        ]
    if experiment_type == "frontier":
        variants = []
        for budget in config.get("sweep", {}).get("local_explanation_budget", [18.0]):
            for exposure in config.get("sweep", {}).get("exposure_budget_total", [18000.0]):
                variants.append(
                    {
                        "name": f"budget_{float(budget):.1f}_exposure_{float(exposure):.0f}",
                        "ablation": "default",
                        "base": {
                            "local_explanation_budget": float(budget),
                            "exposure_budget_total": float(exposure),
                        },
                    }
                )
        return variants
    if experiment_type == "ablations":
        return [{"name": ablation, "ablation": ablation} for ablation in config.get("ablations", ABLATIONS)]
    if experiment_type == "robustness":
        variants = [{"name": "default", "ablation": "default"}]
        sweep = config.get("sweep", {})
        for value in sweep.get("rtt_noise_scale", []):
            variants.append({"name": f"rtt_{float(value):.2f}", "ablation": "default", "base": {"rtt_noise_scale": float(value)}})
        for value in sweep.get("explanation_cost_scale", []):
            variants.append({"name": f"cost_{float(value):.2f}", "ablation": "default", "base": {"explanation_cost_scale": float(value)}})
        for value in sweep.get("service_capacity_multiplier", []):
            variants.append(
                {
                    "name": f"service_{float(value):.2f}",
                    "ablation": "default",
                    "base": {"service_capacity_multiplier": float(value)},
                }
            )
        for value in sweep.get("detection_matrix_noise", []):
            variants.append(
                {
                    "name": f"detpert_{float(value):.2f}",
                    "ablation": "default",
                    "base": {"detection_matrix_noise": float(value)},
                }
            )
        for value in sweep.get("burstiness_scale", []):
            variants.append(
                {
                    "name": f"burst_{float(value):.2f}",
                    "ablation": "default",
                    "base": {"burstiness_scale": float(value)},
                }
            )
        return variants
    if experiment_type == "custom_variants":
        variants = []
        for variant in config.get("variants", [{"name": "default", "ablation": "default"}]):
            expanded = dict(variant)
            expanded.setdefault("ablation", "default")
            expanded.setdefault("name", "default")
            variants.append(expanded)
        return variants
    raise ValueError(f"Unknown experiment_type: {experiment_type}")


def run_experiment(config: Mapping[str, Any], config_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    if config_dir is None:
        config_dir = Path.cwd()
    calibration = load_calibration_profile(config, config_dir)
    policies = list(config.get("policies", MANDATORY_POLICIES))
    regimes = list(config.get("regimes", MANDATORY_REGIMES))
    seeds = [int(seed) for seed in config.get("seeds", [1])]
    variants = expand_variants(config)
    results: List[Dict[str, Any]] = []
    for variant in variants:
        variant_policies = list(variant.get("policies", policies))
        for seed in seeds:
            for regime in regimes:
                for policy in variant_policies:
                    results.append(simulate_run(config, seed, policy, regime, variant, calibration))
    return results


def numeric_metric_keys(rows: Iterable[Mapping[str, Any]]) -> List[str]:
    preferred = PRIMARY_METRICS + SECONDARY_METRICS + ["alerts_per_slot", "packets_per_slot"]
    return [key for key in preferred if any(key in row for row in rows)]


def aggregate_results(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for row in rows:
        key = (row["stage"], row["variant"], row["ablation"], row["regime"], row["policy"])
        groups.setdefault(key, []).append(row)
    metric_keys = numeric_metric_keys(rows)
    summary: List[Dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        out: Dict[str, Any] = {
            "stage": key[0],
            "variant": key[1],
            "ablation": key[2],
            "regime": key[3],
            "policy": key[4],
            "seed_count": len(group),
        }
        for metric in metric_keys:
            values = [float(row[metric]) for row in group]
            mean = sum(values) / len(values)
            if len(values) > 1:
                variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
                ci95 = 1.96 * math.sqrt(variance) / math.sqrt(len(values))
            else:
                ci95 = 0.0
            out[f"mean_{metric}"] = mean
            out[f"ci95_{metric}"] = ci95
        summary.append(out)
    return summary


def ordered_fieldnames(rows: List[Mapping[str, Any]]) -> List[str]:
    preferred = [
        "stage",
        "variant",
        "ablation",
        "regime",
        "policy",
        "seed",
        "seed_count",
        "slots",
        *PRIMARY_METRICS,
        *SECONDARY_METRICS,
        "alerts_per_slot",
        "packets_per_slot",
        "calibration_status",
    ]
    all_keys = sorted({key for row in rows for key in row.keys()})
    return [key for key in preferred if key in all_keys] + [key for key in all_keys if key not in preferred]


def write_csv(path: Path, rows: List[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = ordered_fieldnames(rows)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def tex_escape(value: Any) -> str:
    text = str(value)
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
    ]:
        text = text.replace(old, new)
    return text


def write_latex_table(path: Path, summary: List[Mapping[str, Any]], max_rows: int = 60) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "regime",
        "policy",
        "variant",
        "seed_count",
        "mean_packet_drop_rate",
        "mean_explanation_coverage",
        "mean_high_risk_explanation_coverage",
        "mean_mean_explanation_debt",
        "mean_exposure_use",
    ]
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\caption{XAI-SurfaceBench summary metrics. Each row reports the seed mean; confidence intervals are available in the CSV artifacts.}",
        r"\begin{tabular}{lllrrrrrr}",
        r"\toprule",
        r"Regime & Policy & Variant & Seeds & Drop & Cov. & HR Cov. & Debt & Exposure \\",
        r"\midrule",
    ]
    for row in summary[:max_rows]:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(tex_escape(value))
        lines.append(" & ".join(values) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(results: List[Dict[str, Any]], config: Mapping[str, Any], output_root: Path) -> Dict[str, Path]:
    name = str(config.get("name", "experiment"))
    output_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "runs_csv": output_root / "results" / f"{name}_runs.csv",
        "summary_csv": output_root / "results" / f"{name}_summary.csv",
        "summary_json": output_root / "results" / f"{name}_summary.json",
        "log_jsonl": output_root / "logs" / f"{name}.jsonl",
        "table_tex": output_root / "tables" / f"{name}_main_metrics.tex",
    }
    summary = aggregate_results(results)
    write_csv(paths["runs_csv"], results)
    write_csv(paths["summary_csv"], summary)
    with paths["summary_json"].open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "config_name": name,
                "config": config,
                "primary_metrics": PRIMARY_METRICS,
                "secondary_metrics": SECONDARY_METRICS,
                "summary": summary,
            },
            fh,
            indent=2,
            sort_keys=True,
        )
        fh.write("\n")
    paths["log_jsonl"].parent.mkdir(parents=True, exist_ok=True)
    with paths["log_jsonl"].open("w", encoding="utf-8") as fh:
        for row in results:
            payload = {key: row[key] for key in ["stage", "variant", "ablation", "policy", "regime", "seed"]}
            for metric in PRIMARY_METRICS + SECONDARY_METRICS:
                payload[metric] = row[metric]
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
    write_latex_table(paths["table_tex"], summary)
    return paths


def validate_required_coverage(config: Mapping[str, Any], require_all: bool = False) -> None:
    policies = set(config.get("policies", []))
    regimes = set(config.get("regimes", []))
    if require_all:
        missing_policies = [policy for policy in MANDATORY_POLICIES if policy not in policies]
        missing_regimes = [regime for regime in MANDATORY_REGIMES if regime not in regimes]
        if missing_policies or missing_regimes:
            raise AssertionError(f"Missing policies={missing_policies}; missing regimes={missing_regimes}")

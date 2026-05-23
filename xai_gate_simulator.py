#!/usr/bin/env python3
"""Discrete-event style simulator for XAI-Gate policies.

This simulator is intentionally detector-agnostic. It models alert-score streams,
explanation demand, local explanation costs, offloading, and leakage exposure
without training an IDS. Optional calibration outputs from
`calibration_training_pipeline.py` can later replace the synthetic alert stream.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


POLICIES = [
    "never_explain",
    "always_explain",
    "threshold_explain",
    "rate_limited",
    "fifo_explanation",
    "static_offload",
    "budget_only_bexgov",
    "xai_gate",
]


REGIMES = [
    "poisson",
    "bursty",
    "non_markovian",
    "adversarial_explanation_flood",
]


@dataclass
class Config:
    slots: int = 5000
    seed: int = 7
    packet_buffer_capacity: int = 120
    standard_service_rate: float = 80.0
    base_arrival_rate: float = 58.0
    attack_arrival_multiplier: float = 1.35
    alert_probability: float = 0.18
    borderline_alert_boost: float = 0.22
    local_explanation_budget: float = 18.0
    offload_rtt_penalty: float = 4.0
    leakage_budget: float = 750.0
    traffic_regimes: Tuple[str, ...] = tuple(REGIMES)
    policies: Tuple[str, ...] = tuple(POLICIES)


@dataclass
class Metrics:
    policy: str
    regime: str
    slots: int
    arrivals: int
    alerts: int
    packet_drop_rate: float
    mean_packet_queue: float
    explanation_coverage: float
    mean_explanation_debt: float
    final_explanation_debt: float
    leakage_used: float
    leakage_violation_rate: float
    offload_rate: float
    audit_rate: float
    redaction_rate: float
    attacker_trigger_gain: float


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    data = json.loads(path.read_text())
    cfg = Config()
    for key, value in data.items():
        if hasattr(cfg, key):
            setattr(cfg, key, tuple(value) if key in {"traffic_regimes", "policies"} else value)
    return cfg


def sample_poisson(rate: float, rng: random.Random) -> int:
    if rate <= 0:
        return 0
    if rate < 50:
        limit = math.exp(-rate)
        count = 0
        product = 1.0
        while product > limit:
            count += 1
            product *= rng.random()
        return count - 1
    # Normal approximation is stable for the high-rate traffic regimes used here.
    return max(0, int(round(rng.gauss(rate, math.sqrt(rate)))))


def arrival_rate(slot: int, regime: str, cfg: Config, rng: random.Random, burst_state: Dict[str, float]) -> float:
    base = cfg.base_arrival_rate
    if regime == "poisson":
        return base
    if regime == "bursty":
        burst = 1.0 + 0.75 * (1.0 if (slot // 250) % 4 == 1 else 0.0)
        return base * burst
    if regime == "non_markovian":
        previous = burst_state.get("level", 1.0)
        shock = 1.0 if rng.random() > 0.025 else rng.uniform(1.8, 2.7)
        level = 0.92 * previous + 0.08 * shock
        burst_state["level"] = min(3.0, max(0.6, level))
        return base * burst_state["level"]
    if regime == "adversarial_explanation_flood":
        periodic_pressure = 1.0 + 0.65 * (1.0 if (slot // 180) % 3 == 1 else 0.0)
        return base * cfg.attack_arrival_multiplier * periodic_pressure
    raise ValueError(f"Unknown regime: {regime}")


def alert_probability(regime: str, cfg: Config, queue_pressure: float, rng: random.Random) -> float:
    p = cfg.alert_probability
    if regime == "adversarial_explanation_flood":
        p += cfg.borderline_alert_boost
    if queue_pressure > 0.75:
        p += 0.05
    # Small jitter prevents all policies from seeing identical thresholds every slot.
    p += rng.uniform(-0.015, 0.015)
    return min(0.95, max(0.01, p))


def explanation_action(policy: str, score: float, q: float, e: float, cfg: Config, slot: int) -> str:
    pressure = q / cfg.packet_buffer_capacity
    debt_pressure = min(1.0, e / max(1.0, cfg.local_explanation_budget * 8.0))

    if policy == "never_explain":
        return "none"
    if policy == "always_explain":
        return "full"
    if policy == "threshold_explain":
        return "full" if score >= 0.65 else "none"
    if policy == "rate_limited":
        return "coarse" if slot % 4 == 0 and score >= 0.45 else "none"
    if policy == "fifo_explanation":
        return "delay" if pressure > 0.65 else "full"
    if policy == "static_offload":
        return "offload" if score >= 0.45 else "none"
    if policy == "budget_only_bexgov":
        if pressure > 0.80:
            return "none"
        if pressure > 0.55 or debt_pressure > 0.55:
            return "delay"
        return "full" if score >= 0.50 else "none"
    if policy == "xai_gate":
        if pressure > 0.88:
            return "audit" if score >= 0.75 else "none"
        if debt_pressure > 0.75 and score < 0.85:
            return "audit"
        if score >= 0.90 and pressure < 0.70:
            return "full"
        if score >= 0.75 and pressure < 0.82:
            return "redact" if debt_pressure > 0.45 else "coarse"
        if score >= 0.55 and pressure < 0.65:
            return "coarse"
        if score >= 0.55 and pressure >= 0.65:
            return "offload"
        return "none"
    raise ValueError(f"Unknown policy: {policy}")


ACTION_PROFILE = {
    "none": {"local_cost": 0.0, "coverage": 0.0, "leakage": 0.0, "offload": 0.0, "audit": 0.0, "redact": 0.0},
    "coarse": {"local_cost": 1.25, "coverage": 0.55, "leakage": 0.22, "offload": 0.0, "audit": 0.0, "redact": 0.0},
    "delay": {"local_cost": 0.20, "coverage": 0.25, "leakage": 0.05, "offload": 0.0, "audit": 0.0, "redact": 0.0},
    "full": {"local_cost": 4.50, "coverage": 1.00, "leakage": 1.00, "offload": 0.0, "audit": 0.0, "redact": 0.0},
    "offload": {"local_cost": 0.55, "coverage": 0.80, "leakage": 0.65, "offload": 1.0, "audit": 0.0, "redact": 0.0},
    "audit": {"local_cost": 0.45, "coverage": 0.35, "leakage": 0.08, "offload": 0.0, "audit": 1.0, "redact": 0.0},
    "redact": {"local_cost": 1.75, "coverage": 0.65, "leakage": 0.12, "offload": 0.0, "audit": 0.0, "redact": 1.0},
}


def simulate(policy: str, regime: str, cfg: Config) -> Metrics:
    seed = cfg.seed + hash((policy, regime)) % 100000
    rng = random.Random(seed)
    burst_state: Dict[str, float] = {}

    q = 0.0
    e = 0.0
    leakage = 0.0
    arrivals_total = 0
    dropped_total = 0.0
    alerts_total = 0
    coverage_total = 0.0
    alert_demand_total = 0
    q_sum = 0.0
    e_sum = 0.0
    offloads = 0
    audits = 0
    redactions = 0
    leakage_violations = 0
    adversarial_alerts = 0

    for slot in range(cfg.slots):
        pressure = q / cfg.packet_buffer_capacity
        lam = arrival_rate(slot, regime, cfg, rng, burst_state)
        arrivals = sample_poisson(lam, rng)
        arrivals_total += arrivals

        p_alert = alert_probability(regime, cfg, pressure, rng)
        alerts = sum(1 for _ in range(arrivals) if rng.random() < p_alert)
        alerts_total += alerts
        if regime == "adversarial_explanation_flood":
            adversarial_alerts += alerts

        local_load = 0.0
        for _ in range(alerts):
            score = rng.betavariate(2.5, 2.0)
            if regime == "adversarial_explanation_flood":
                score = min(1.0, score + rng.uniform(0.05, 0.25))
            action = explanation_action(policy, score, q, e, cfg, slot)
            profile = ACTION_PROFILE[action]
            local_load += profile["local_cost"]
            coverage_total += profile["coverage"]
            leakage += profile["leakage"]
            offloads += int(profile["offload"])
            audits += int(profile["audit"])
            redactions += int(profile["redact"])
            alert_demand_total += 1
            if action == "delay":
                e += 1.0

        # Debt draining uses leftover explanation budget after immediate local work.
        debt_service = max(0.0, cfg.local_explanation_budget - local_load) / 2.5
        e = max(0.0, e - debt_service)

        # Explanation work steals service from packet forwarding.
        service_penalty = min(cfg.standard_service_rate * 0.90, local_load)
        served = max(0.0, cfg.standard_service_rate - service_penalty)
        q = max(0.0, q + arrivals - served)
        if q > cfg.packet_buffer_capacity:
            dropped_total += q - cfg.packet_buffer_capacity
            q = float(cfg.packet_buffer_capacity)

        if leakage > cfg.leakage_budget:
            leakage_violations += 1

        q_sum += q
        e_sum += e

    alerts_den = max(1, alert_demand_total)
    return Metrics(
        policy=policy,
        regime=regime,
        slots=cfg.slots,
        arrivals=arrivals_total,
        alerts=alerts_total,
        packet_drop_rate=dropped_total / max(1, arrivals_total),
        mean_packet_queue=q_sum / cfg.slots,
        explanation_coverage=coverage_total / alerts_den,
        mean_explanation_debt=e_sum / cfg.slots,
        final_explanation_debt=e,
        leakage_used=leakage,
        leakage_violation_rate=leakage_violations / cfg.slots,
        offload_rate=offloads / alerts_den,
        audit_rate=audits / alerts_den,
        redaction_rate=redactions / alerts_den,
        attacker_trigger_gain=adversarial_alerts / max(1, arrivals_total),
    )


def write_outputs(metrics: List[Metrics], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "xai_gate_summary.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(metrics[0]).keys()))
        writer.writeheader()
        for row in metrics:
            writer.writerow(asdict(row))

    md_path = out_dir / "xai_gate_summary.md"
    lines = [
        "# XAI-Gate Simulation Summary",
        "",
        "Lower packet-drop, lower debt, and bounded leakage are better. Explanation coverage should be interpreted jointly with packet QoS.",
        "",
        "| Regime | Policy | Drop rate | Coverage | Mean debt | Leakage used | Offload | Audit | Redact |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in sorted(metrics, key=lambda x: (x.regime, x.packet_drop_rate, -x.explanation_coverage)):
        lines.append(
            f"| {m.regime} | {m.policy} | {m.packet_drop_rate:.4f} | "
            f"{m.explanation_coverage:.3f} | {m.mean_explanation_debt:.2f} | "
            f"{m.leakage_used:.1f} | {m.offload_rate:.3f} | {m.audit_rate:.3f} | {m.redaction_rate:.3f} |"
        )
    md_path.write_text("\n".join(lines) + "\n")


def run(cfg: Config) -> List[Metrics]:
    metrics: List[Metrics] = []
    for regime in cfg.traffic_regimes:
        for policy in cfg.policies:
            metrics.append(simulate(policy, regime, cfg))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run XAI-Gate explanation service simulations.")
    parser.add_argument("--config", type=Path, default=None, help="Path to JSON config.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Output directory.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    metrics = run(cfg)
    write_outputs(metrics, args.output_dir)
    print(f"Wrote {len(metrics)} policy/regime results to {args.output_dir}")


if __name__ == "__main__":
    main()


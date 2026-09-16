#!/usr/bin/env python3
"""Demonstrate that explanation debt is risk/obligation weighted, not raw queue count."""

from __future__ import annotations

import json
from pathlib import Path

SCENARIOS = [
    {"name":"ten_low_risk_unexplained","count":10,"risk":0.25,"satisfied":0.0},
    {"name":"ten_high_risk_unexplained","count":10,"risk":0.93,"satisfied":0.0},
    {"name":"ten_high_risk_audited","count":10,"risk":0.93,"satisfied":0.80},
    {"name":"ten_medium_risk_coarse","count":10,"risk":0.55,"satisfied":0.45},
]


def debt(count: float, risk: float, satisfied: float) -> float:
    return float(count) * (1.0 - float(satisfied)) * (0.65 + 0.70 * float(risk))


def main() -> int:
    rows = [{**scenario, "explanation_debt": debt(scenario["count"], scenario["risk"], scenario["satisfied"])} for scenario in SCENARIOS]
    out = Path("results/debt_backlog_diagnostic.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())

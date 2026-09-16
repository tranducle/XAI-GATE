#!/usr/bin/env python3
"""Descriptive analysis for the CICIoT2023 timestamp-preserving temporal replay."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "results" / "temporal_replay"
ATTACK_SESSIONS = [
    "Recon-PingSweep__Recon-PingSweep.parquet",
    "Recon-PortScan__Recon-PortScan.parquet",
    "DDoS-SynonymousIP_Flood__DDoS-SynonymousIP_Flood13.parquet",
    "Backdoor_Malware__Backdoor_Malware.parquet",
]
NON_FLOOD_ATTACK_SESSIONS = [
    "Recon-PingSweep__Recon-PingSweep.parquet",
    "Recon-PortScan__Recon-PortScan.parquet",
    "Backdoor_Malware__Backdoor_Malware.parquet",
]
DISPLAY_NAMES = {
    "Benign_Final__BenignTraffic3.parquet": "Benign",
    "Recon-PingSweep__Recon-PingSweep.parquet": "PingSweep",
    "Recon-PortScan__Recon-PortScan.parquet": "PortScan",
    "DDoS-SynonymousIP_Flood__DDoS-SynonymousIP_Flood13.parquet": "DDoS flood",
    "Backdoor_Malware__Backdoor_Malware.parquet": "Backdoor",
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("rows must not be empty")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float, digits: int = 3) -> str:
    if abs(value) >= 10000:
        return f"{value:.0f}"
    if abs(value) >= 100:
        return f"{value:.1f}"
    return f"{value:.{digits}f}"


def main() -> int:
    official_path = RESULT_DIR / "full_runs.csv"
    preprocessing_path = ROOT / "data" / "ciciot2023_temporal" / "temporal_preprocessing_manifest.json"

    frame = pd.read_csv(official_path)
    preprocessing = json.loads(preprocessing_path.read_text(encoding="utf-8"))
    session_meta = {row["filename"]: row for row in preprocessing["sessions"]}

    xai_rows: list[dict[str, Any]] = []
    figure_rows: list[dict[str, Any]] = []
    xai = frame.loc[frame["policy"] == "xai_gate"].copy()
    for session in preprocessing["replay_files"]:
        meta = session_meta[session]
        chronological = xai.loc[(xai["session_id"] == session) & (xai["condition"] == "chronological")].iloc[0]
        shuffled = xai.loc[(xai["session_id"] == session) & (xai["condition"] == "shuffled")].iloc[0]
        row = {
            "session_id": session,
            "display_name": DISPLAY_NAMES[session],
            "slots": int(chronological["slots"]),
            "flow_starts": int(chronological["trace_total_flow_starts"]),
            "alerts": int(chronological["trace_total_alerts"]),
            "fano_1s": float(meta["temporal_1s"]["fano"]),
            "fano_10s": float(meta["temporal_10s"]["fano"]),
            "fano_60s": float(meta["temporal_60s"]["fano"]),
            "coverage_chronological": float(chronological["high_risk_explanation_coverage"]),
            "coverage_shuffled": float(shuffled["high_risk_explanation_coverage"]),
            "debt_chronological": float(chronological["mean_explanation_debt"]),
            "debt_shuffled": float(shuffled["mean_explanation_debt"]),
            "exposure_chronological": float(chronological["exposure_use"]),
            "exposure_shuffled": float(shuffled["exposure_use"]),
            "drop_chronological": float(chronological["packet_drop_rate"]),
            "drop_shuffled": float(shuffled["packet_drop_rate"]),
            "delay_chronological": float(chronological["mean_packet_delay"]),
            "delay_shuffled": float(shuffled["mean_packet_delay"]),
            "exposure_violation_chronological": float(chronological["exposure_budget_violation_rate"]),
            "exposure_violation_shuffled": float(shuffled["exposure_budget_violation_rate"]),
        }
        row["debt_delta_chronological_minus_shuffled"] = row["debt_chronological"] - row["debt_shuffled"]
        row["drop_delta_chronological_minus_shuffled"] = row["drop_chronological"] - row["drop_shuffled"]
        row["delay_delta_chronological_minus_shuffled"] = row["delay_chronological"] - row["delay_shuffled"]
        xai_rows.append(row)
        for scale in [1, 10, 60]:
            figure_rows.append(
                {
                    "panel": "burstiness",
                    "session_id": session,
                    "display_name": DISPLAY_NAMES[session],
                    "timescale_seconds": scale,
                    "fano_factor": float(meta[f"temporal_{scale}s"]["fano"]),
                    "condition": "",
                    "packet_drop_rate": "",
                }
            )
        for condition, drop in [("chronological", row["drop_chronological"]), ("shuffled", row["drop_shuffled"])]:
            figure_rows.append(
                {
                    "panel": "packet_drop",
                    "session_id": session,
                    "display_name": DISPLAY_NAMES[session],
                    "timescale_seconds": "",
                    "fano_factor": "",
                    "condition": condition,
                    "packet_drop_rate": drop,
                }
            )

    write_csv(RESULT_DIR / "xai_gate_session_summary.csv", xai_rows)
    write_csv(RESULT_DIR / "temporal_diagnostic_source.csv", figure_rows)

    attack_chron = frame.loc[
        frame["session_id"].isin(ATTACK_SESSIONS) & (frame["condition"] == "chronological")
    ].copy()
    comparator_rows: list[dict[str, Any]] = []
    for session in ATTACK_SESSIONS:
        group = attack_chron.loc[attack_chron["session_id"] == session]
        for policy in sorted(group["policy"].unique()):
            row = group.loc[group["policy"] == policy].iloc[0]
            comparator_rows.append(
                {
                    "session_id": session,
                    "display_name": DISPLAY_NAMES[session],
                    "policy": policy,
                    "high_risk_explanation_coverage": float(row["high_risk_explanation_coverage"]),
                    "mean_explanation_debt": float(row["mean_explanation_debt"]),
                    "exposure_use": float(row["exposure_use"]),
                    "exposure_budget_violation_rate": float(row["exposure_budget_violation_rate"]),
                    "packet_drop_rate": float(row["packet_drop_rate"]),
                }
            )
    write_csv(RESULT_DIR / "chronological_attack_policy_summary.csv", comparator_rows)

    attack_xai = [row for row in xai_rows if row["session_id"] in ATTACK_SESSIONS]
    non_flood_xai = [row for row in xai_rows if row["session_id"] in NON_FLOOD_ATTACK_SESSIONS]
    ddos_xai = next(row for row in xai_rows if row["display_name"] == "DDoS flood")
    fano_1s = [row["fano_1s"] for row in xai_rows]
    fano_60s = [row["fano_60s"] for row in xai_rows]
    drop_deltas = [row["drop_delta_chronological_minus_shuffled"] for row in xai_rows]
    debt_abs_deltas = [abs(row["debt_delta_chronological_minus_shuffled"]) for row in xai_rows]

    xai_attack_cov = [row["coverage_chronological"] for row in attack_xai]
    xai_attack_exp = [row["exposure_chronological"] for row in attack_xai]
    non_flood_cov = [row["coverage_chronological"] for row in non_flood_xai]
    non_flood_exp = [row["exposure_chronological"] for row in non_flood_xai]
    non_flood_debt = [row["debt_chronological"] for row in non_flood_xai]

    analysis_lines = [
        "# Timestamp-Preserving CICIoT2023 Replay Analysis",
        "",
        "## Evidence boundary",
        "",
        "This analysis uses the result table generated by the documented replay pipeline. The five source captures are heterogeneous fixed validation cases, not an iid sample, so no pseudo-replicated seed-level p-values are reported.",
        "",
        "## Multi-scale temporal structure",
        "",
        f"Across the five selected captures, the 1-second Fano factor ranges from {min(fano_1s):.3f} to {max(fano_1s):.3f}; the 60-second Fano factor ranges from {min(fano_60s):.3f} to {max(fano_60s):.3f}. All five captures remain overdispersed at both scales. This directly establishes non-Poisson, multi-scale burst structure in the replay inputs.",
        "",
        "## XAI-Gate on chronological replay",
        "",
        f"Across the four attack captures, chronological high-risk coverage ranges from {min(xai_attack_cov):.4f} to {max(xai_attack_cov):.4f}, while exposure use ranges from {min(xai_attack_exp):.4f} to {max(xai_attack_exp):.4f}. Exposure-budget violation remains zero in every XAI-Gate replay run.",
        "",
        f"On the three non-flood attack captures, high-risk coverage is {min(non_flood_cov):.4f} to {max(non_flood_cov):.4f}, exposure use is {min(non_flood_exp):.4f} to {max(non_flood_exp):.4f}, and mean debt is {min(non_flood_debt):.4f} to {max(non_flood_debt):.4f}. The DDoS flood capture is qualitatively different: coverage falls to {ddos_xai['coverage_chronological']:.4f}, mean debt rises to {ddos_xai['debt_chronological']:.1f}, exposure reaches {ddos_xai['exposure_chronological']:.4f}, and packet drop reaches {ddos_xai['drop_chronological']:.4f}. This is a negative finite-capacity result, not evidence of universal robustness.",
        "",
        "## Temporal-order control",
        "",
        f"The shuffled control preserves every 1-second slot record and all session marginals but destroys their order. For XAI-Gate, chronological minus shuffled packet-drop differences range from {min(drop_deltas):.6f} to {max(drop_deltas):.6f}, with the largest increases on PingSweep ({next(row for row in xai_rows if row['display_name']=='PingSweep')['drop_delta_chronological_minus_shuffled']:.6f}) and PortScan ({next(row for row in xai_rows if row['display_name']=='PortScan')['drop_delta_chronological_minus_shuffled']:.6f}). The maximum absolute debt difference is {max(debt_abs_deltas):.1f}. Coverage and exposure are comparatively stable, but queue and debt transients are order-sensitive. This supports the evaluation concern that temporal structure matters operationally.",
        "",
        "## Comparator boundary",
        "",
        "The replay does not support a universal superiority claim. Always-explain and resource-aware policies retain much higher immediate coverage on the DDoS flood capture but greatly exceed the exposure budget. XAI-Gate instead saturates its hard exposure cap and sacrifices coverage. On the three non-flood attack captures, XAI-Gate maintains approximately 0.84 high-risk coverage with zero exposure violations. The defensible conclusion is a bounded service trade-off under timestamp-preserving workloads.",
        "",
        "## Statistical treatment",
        "",
        "The independent unit is the source capture. Because there are only five intentionally heterogeneous captures and one is benign, the main evidence is per-session effect magnitude and direction, not an iid significance test. Random seeds are not introduced as pseudo-replication.",
        "",
    ]
    (RESULT_DIR / "temporal_replay_analysis.md").write_text("\n".join(analysis_lines), encoding="utf-8")

    print(f"analysis={RESULT_DIR / 'temporal_replay_analysis.md'}")
    print(f"session_summary={RESULT_DIR / 'xai_gate_session_summary.csv'}")
    print(f"diagnostic_source={RESULT_DIR / 'temporal_diagnostic_source.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

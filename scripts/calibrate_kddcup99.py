#!/usr/bin/env python3
"""Create a public no-training calibration anchor from KDDCup99.

The generated score stream is not a detector contribution. It is a transparent
score proxy over a public IDS dataset, used only to replace the simulator's
default score-bucket priors with externally anchored label/score metadata.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List


BUCKETS = [
    ("low", 0.0, 0.40),
    ("medium", 0.40, 0.65),
    ("high", 0.65, 0.85),
    ("critical", 0.85, 1.01),
]


def decode_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def robust01(series: Any) -> Any:
    q05 = float(series.quantile(0.05))
    q95 = float(series.quantile(0.95))
    if not math.isfinite(q05) or not math.isfinite(q95) or q95 <= q05:
        return series.astype(float) * 0.0
    return ((series.astype(float) - q05) / (q95 - q05)).clip(0.0, 1.0)


def bucket_name(score: float) -> str:
    for name, low, high in BUCKETS:
        if low <= score < high:
            return name
    return "critical"


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    labels = [int(row["true_label"]) for row in rows]
    scores = [float(row["score"]) for row in rows]
    by_bucket: Dict[str, Dict[str, float]] = {
        name: {"rows": 0.0, "positives": 0.0, "score_sum": 0.0} for name, _, _ in BUCKETS
    }
    for row in rows:
        bucket = bucket_name(float(row["score"]))
        by_bucket[bucket]["rows"] += 1.0
        by_bucket[bucket]["positives"] += float(row["true_label"])
        by_bucket[bucket]["score_sum"] += float(row["score"])
    bucket_summary = {}
    for name, stats in by_bucket.items():
        count = max(stats["rows"], 1.0)
        bucket_summary[name] = {
            "rows": int(stats["rows"]),
            "share": stats["rows"] / max(len(rows), 1),
            "attack_rate": stats["positives"] / count,
            "mean_score": stats["score_sum"] / count,
        }
    auc = None
    try:
        from sklearn.metrics import roc_auc_score

        auc = float(roc_auc_score(labels, scores))
    except Exception:
        auc = None
    return {
        "source": "sklearn.datasets.fetch_kddcup99(subset='SA', percent10=True)",
        "rows": len(rows),
        "positive_rate": sum(labels) / max(len(labels), 1),
        "mean_score": sum(scores) / max(len(scores), 1),
        "score_auc_metadata": auc,
        "score_generation": "Transparent no-training heuristic over KDDCup99 traffic features; used only for score-bucket calibration metadata.",
        "bucket_summary": bucket_summary,
        "not_claimed": [
            "No new IDS is trained.",
            "No detector accuracy contribution is claimed.",
            "KDDCup99 is used only as an external score/label realism anchor.",
        ],
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["score", "true_label", "attack_family", "cost_proxy", "score_source"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, summary: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_config(path: Path) -> None:
    config = {
        "name": "calibrated_anchor",
        "experiment_type": "standard",
        "slots": 5000,
        "seeds": list(range(1, 21)),
        "policies": [
            "never_explain",
            "always_explain",
            "threshold_explain",
            "rate_limited",
            "fifo_explanation",
            "static_coarse_full",
            "static_offload",
            "budget_only_bexgov",
            "xai_gate",
        ],
        "regimes": [
            "adversarial_explanation_flood",
            "transient_overload",
            "non_markovian",
            "rtt_uncertainty",
        ],
        "base": {
            "packet_arrival_rate": 45.0,
            "packet_service_rate": 52.0,
            "packet_buffer_capacity": 240.0,
            "alert_probability": 0.15,
            "local_explanation_budget": 18.0,
            "exposure_budget_total": 18000.0,
            "threshold": 0.72,
        },
        "calibration": {
            "score_stream_path": "../data/kddcup99_sa_score_stream.csv",
            "training_summary_path": "../data/kddcup99_sa_calibration_summary.json",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_rows(max_rows: int) -> List[Dict[str, Any]]:
    from sklearn.datasets import fetch_kddcup99

    data = fetch_kddcup99(subset="SA", percent10=True, as_frame=True, shuffle=True, random_state=7)
    frame = data.data.copy()
    labels = [decode_value(value) for value in data.target]
    for column in ["protocol_type", "service", "flag"]:
        if column in frame.columns:
            frame[column] = frame[column].map(decode_value)

    # The score proxy is intentionally fixed and transparent. It uses common
    # KDDCup99 traffic/error indicators without fitting parameters to labels.
    n = min(max_rows, len(frame))
    frame = frame.iloc[:n].copy()
    labels = labels[:n]
    features = {}
    for column in [
        "serror_rate",
        "srv_serror_rate",
        "rerror_rate",
        "dst_host_srv_serror_rate",
        "dst_host_srv_rerror_rate",
        "count",
        "srv_count",
        "duration",
        "src_bytes",
        "dst_bytes",
    ]:
        if column in frame.columns:
            features[column] = robust01(frame[column])

    def feature_value(column: str, position: int) -> float:
        series = features.get(column)
        if series is None:
            return 0.0
        return float(series.iloc[position])

    risky_services = {"private", "eco_i", "ecr_i", "finger", "ftp_data", "telnet", "other"}
    rows: List[Dict[str, Any]] = []
    for idx, (_, row) in enumerate(frame.iterrows()):
        flag_not_sf = 1.0 if decode_value(row.get("flag", "SF")) != "SF" else 0.0
        risky_service = 1.0 if decode_value(row.get("service", "")) in risky_services else 0.0
        same_srv_low = 0.0
        if "same_srv_rate" in frame.columns:
            same_srv_low = 1.0 if float(row.get("same_srv_rate", 1.0)) < 0.20 else 0.0
        logged_in_absent = 0.0
        if "logged_in" in frame.columns:
            logged_in_absent = 1.0 if float(row.get("logged_in", 1.0)) <= 0.0 else 0.0
        score = (
            0.06
            + 0.16 * feature_value("serror_rate", idx)
            + 0.10 * feature_value("srv_serror_rate", idx)
            + 0.11 * feature_value("rerror_rate", idx)
            + 0.14 * feature_value("dst_host_srv_serror_rate", idx)
            + 0.10 * feature_value("dst_host_srv_rerror_rate", idx)
            + 0.10 * feature_value("count", idx)
            + 0.05 * feature_value("srv_count", idx)
            + 0.04 * feature_value("duration", idx)
            + 0.11 * flag_not_sf
            + 0.08 * risky_service
            + 0.06 * same_srv_low
            + 0.05 * logged_in_absent
        )
        score = clamp(score)
        cost_proxy = clamp(0.20 + 0.65 * score + 0.10 * flag_not_sf + 0.05 * risky_service)
        label = 0 if labels[idx] == "normal." else 1
        rows.append(
            {
                "score": f"{score:.6f}",
                "true_label": label,
                "attack_family": labels[idx].rstrip("."),
                "cost_proxy": f"{cost_proxy:.6f}",
                "score_source": "kddcup99_no_training_proxy",
            }
        )
    return rows


def write_markdown(path: Path, summary: Dict[str, Any], csv_path: Path, config_path: Path) -> None:
    bucket_lines = []
    for name, stats in summary["bucket_summary"].items():
        bucket_lines.append(
            f"| {name} | {stats['rows']} | {stats['share']:.3f} | {stats['attack_rate']:.3f} | {stats['mean_score']:.3f} |"
        )
    auc = summary["score_auc_metadata"]
    auc_text = "not computed" if auc is None else f"{auc:.3f}"
    text = f"""# KDDCup99 Calibration Anchor

This artifact adds an externally anchored, no-training calibration run for XAI-SurfaceBench.
It uses `sklearn.datasets.fetch_kddcup99(subset='SA', percent10=True)` and generates a
transparent score proxy from public traffic/error features. The proxy is used only to
instantiate score-bucket and high-risk priors; it is not a detector contribution.

## Files

- Score stream: `{csv_path.relative_to(path.parent)}`
- Benchmark config: `{config_path.relative_to(path.parent)}`
- Summary JSON: `data/kddcup99_sa_calibration_summary.json`

## Metadata

- Rows used: {summary['rows']}
- Attack-label rate: {summary['positive_rate']:.3f}
- Mean proxy score: {summary['mean_score']:.3f}
- AUC metadata: {auc_text}
- Training: none

## Bucket Summary

| Bucket | Rows | Share | Attack rate | Mean score |
|---|---:|---:|---:|---:|
{chr(10).join(bucket_lines)}

## Claim Boundary

This run addresses the reviewer risk that the evaluation was purely synthetic. It does
not establish deployment readiness, hardware timing, or detector novelty. Detector
accuracy should be interpreted only as calibration metadata.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-rows", type=int, default=50000)
    args = parser.parse_args()
    root = args.root.resolve()
    rows = make_rows(args.max_rows)
    summary = summarize_rows(rows)
    csv_path = root / "data" / "kddcup99_sa_score_stream.csv"
    summary_path = root / "data" / "kddcup99_sa_calibration_summary.json"
    config_path = root / "configs" / "calibrated_anchor.json"
    report_path = root / "CALIBRATION_ANCHOR_REPORT.md"
    write_csv(csv_path, rows)
    write_summary(summary_path, summary)
    write_config(config_path)
    write_markdown(report_path, summary, csv_path, config_path)
    print(f"rows={len(rows)}")
    print(f"score_stream={csv_path}")
    print(f"summary={summary_path}")
    print(f"config={config_path}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

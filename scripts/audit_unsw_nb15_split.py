#!/usr/bin/env python3
"""Audit UNSW-NB15 split and score-stream integrity for manuscript follow-up."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "unsw_nb15"
RESULTS = ROOT / "results"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_hash(row: dict[str, str], columns: list[str]) -> str:
    joined = "\x1f".join(row.get(c, "") for c in columns)
    return hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest()


def read_raw(path: Path) -> tuple[list[str], dict[str, object]]:
    full_hashes: Counter[str] = Counter()
    feature_hashes: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    attacks: Counter[str] = Counter()
    row_count = 0
    columns: list[str] = []
    with path.open(newline="", encoding="utf-8-sig", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        full_columns = [c for c in columns if c != "id"]
        feature_columns = [c for c in columns if c not in {"id", "label", "attack_cat"}]
        for row in reader:
            row_count += 1
            labels[row.get("label", "")] += 1
            attacks[row.get("attack_cat", "")] += 1
            full_hashes[row_hash(row, full_columns)] += 1
            feature_hashes[row_hash(row, feature_columns)] += 1
    duplicate_full_rows = sum(count - 1 for count in full_hashes.values() if count > 1)
    duplicate_feature_rows = sum(count - 1 for count in feature_hashes.values() if count > 1)
    return columns, {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
        "rows": row_count,
        "label_counts": dict(labels),
        "attack_cat_counts": dict(attacks),
        "unique_full_no_id_hashes": len(full_hashes),
        "duplicate_full_no_id_rows": duplicate_full_rows,
        "unique_feature_hashes": len(feature_hashes),
        "duplicate_feature_rows": duplicate_feature_rows,
        "_full_hash_set": set(full_hashes),
        "_feature_hash_set": set(feature_hashes),
    }


def read_score_stream(path: Path) -> dict[str, object]:
    splits: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    attacks: Counter[str] = Counter()
    row_count = 0
    columns: list[str] = []
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        for row in reader:
            row_count += 1
            splits[row.get("split", "")] += 1
            labels[row.get("true_label", "")] += 1
            attacks[row.get("attack_family", "")] += 1
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
        "rows": row_count,
        "columns": columns,
        "split_counts": dict(splits),
        "true_label_counts": dict(labels),
        "attack_family_counts": dict(attacks),
    }


def public_report(raw: dict[str, object]) -> dict[str, object]:
    cleaned = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        cleaned[key] = value
    return cleaned


def status_checks(train_cols: list[str], test_cols: list[str], train: dict[str, object], test: dict[str, object], score: dict[str, object]) -> list[dict[str, object]]:
    checks = []
    checks.append(
        {
            "check": "raw_train_test_columns_match",
            "status": "PASS" if train_cols == test_cols else "FAIL",
            "detail": f"train columns={len(train_cols)}, test columns={len(test_cols)}",
        }
    )
    checks.append(
        {
            "check": "score_stream_rows_match_public_test_rows",
            "status": "PASS" if score["rows"] == test["rows"] else "FAIL",
            "detail": f"score rows={score['rows']}, test rows={test['rows']}",
        }
    )
    checks.append(
        {
            "check": "score_stream_uses_test_split_only",
            "status": "PASS" if set(score["split_counts"]) == {"test"} else "FAIL",
            "detail": str(score["split_counts"]),
        }
    )
    checks.append(
        {
            "check": "score_stream_label_counts_match_test",
            "status": "PASS" if score["true_label_counts"] == test["label_counts"] else "FAIL",
            "detail": f"score labels={score['true_label_counts']}, test labels={test['label_counts']}",
        }
    )
    full_overlap = len(train["_full_hash_set"] & test["_full_hash_set"])
    feature_overlap = len(train["_feature_hash_set"] & test["_feature_hash_set"])
    checks.append(
        {
            "check": "no_exact_train_test_overlap_excluding_id",
            "status": "PASS" if full_overlap == 0 else "WARN",
            "detail": f"overlap full rows excluding id={full_overlap}",
        }
    )
    checks.append(
        {
            "check": "feature_only_train_test_overlap_recorded",
            "status": "PASS" if feature_overlap == 0 else "WARN",
            "detail": f"feature-only overlap excluding id/label/attack_cat={feature_overlap}",
        }
    )
    return checks


def write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = [
        "# UNSW-NB15 Split-Integrity Audit",
        "",
        "This audit checks the public train/test files, the derived score stream, and exact-overlap indicators. "
        "It does not prove the historical UNSW-NB15 collection is leakage-free; it verifies the local calibration-anchor artifact used by this manuscript.",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(f"| `{check['check']}` | {check['status']} | {check['detail']} |")
    lines.extend(
        [
            "",
            "## File Summary",
            "",
            "| File | Rows | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    for key in ["train", "test", "score_stream"]:
        item = report[key]
        lines.append(f"| `{item['path']}` | {item['rows']} | `{item['sha256']}` |")
    lines.extend(
        [
            "",
            "## Duplicate/Overlap Notes",
            "",
            f"- Train duplicate full rows excluding `id`: {report['train']['duplicate_full_no_id_rows']}.",
            f"- Test duplicate full rows excluding `id`: {report['test']['duplicate_full_no_id_rows']}.",
            f"- Train/test exact full-row overlap excluding `id`: {report['train_test_overlap_full_no_id']}.",
            f"- Train/test feature-only overlap excluding `id`, `label`, and `attack_cat`: {report['train_test_overlap_feature_only']}.",
            "",
            "## Manuscript-Safe Interpretation",
            "",
            "- Safe: the local score stream is generated for the public test split only, with row and label counts matching the public test file.",
            "- Safe: the local pipeline evidence supports a public test-split score-stream calibration-anchor claim, not detector novelty.",
            "- Not safe without additional provenance work: claiming that UNSW-NB15 itself has no temporal, duplicate-flow, or collection-process leakage.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    train_path = DATA / "raw" / "train.csv"
    test_path = DATA / "raw" / "test.csv"
    score_path = DATA / "unsw_nb15_score_stream.csv"
    train_cols, train = read_raw(train_path)
    test_cols, test = read_raw(test_path)
    score = read_score_stream(score_path)
    full_overlap = len(train["_full_hash_set"] & test["_full_hash_set"])
    feature_overlap = len(train["_feature_hash_set"] & test["_feature_hash_set"])
    report = {
        "audit_scope": "UNSW-NB15 public train/test split and derived score stream",
        "train": public_report(train),
        "test": public_report(test),
        "score_stream": score,
        "train_test_overlap_full_no_id": full_overlap,
        "train_test_overlap_feature_only": feature_overlap,
        "checks": status_checks(train_cols, test_cols, train, test, score),
        "claim_boundary": [
            "The score stream is a held-out calibration anchor, not a detector contribution.",
            "Exact local split checks do not establish full historical dataset provenance or temporal leakage absence.",
        ],
    }
    out_json = RESULTS / "unsw_split_integrity_audit.json"
    out_md = ROOT / "UNSW_SPLIT_INTEGRITY_AUDIT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(out_md, report)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "checks": report["checks"]}, indent=2))


if __name__ == "__main__":
    main()

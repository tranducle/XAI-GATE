#!/usr/bin/env python3
"""Acquire and fingerprint the documented CICIoT2023 temporal replay subset.

This script downloads only the files selected for the published temporal replay protocol. It
records source sizes, local SHA256 digests, schema, labels, source-capture
identity, and timestamp integrity. It does not run any policy experiment.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DATASET_REPO = "Lystea/CICIOT2023-PARQUET"
HF_TREE_URL = f"https://huggingface.co/api/datasets/{DATASET_REPO}/tree/main?recursive=false&expand=false&limit=1000"
HF_RESOLVE_BASE = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main"
MIRROR_README_URL = f"{HF_RESOLVE_BASE}/README.md"
OFFICIAL_DATASET_PAGE = "https://www.unb.ca/cic/datasets/iotdataset-2023.html"
ORIGINAL_PCAP_MIRROR = "bencorn/CIC-IoT-2023"
DATASET_DOI = "10.3390/s23135941"

CALIBRATION_FILES = [
    "Benign_Final__BenignTraffic.parquet",
    "BrowserHijacking__BrowserHijacking.parquet",
    "CommandInjection__CommandInjection.parquet",
    "DDoS-UDP_Fragmentation__DDoS-UDP_Fragmentation9.parquet",
    "DNS_Spoofing__DNS_Spoofing.parquet",
    "DictionaryBruteForce__DictionaryBruteForce.parquet",
    "DoS-TCP_Flood__DoS-TCP_Flood10.parquet",
    "MITM-ArpSpoofing__MITM-ArpSpoofing1.parquet",
    "Mirai-greeth_flood__Mirai-greeth_flood24.parquet",
    "SqlInjection__SqlInjection.parquet",
    "Uploading_Attack__Uploading_Attack.parquet",
    "XSS__XSS.parquet",
]

REPLAY_FILES = [
    "Benign_Final__BenignTraffic3.parquet",
    "Recon-PingSweep__Recon-PingSweep.parquet",
    "Recon-PortScan__Recon-PortScan.parquet",
    "DDoS-SynonymousIP_Flood__DDoS-SynonymousIP_Flood13.parquet",
    "Backdoor_Malware__Backdoor_Malware.parquet",
]

REQUIRED_COLUMNS = {
    "protocol",
    "src_port",
    "dst_port",
    "packets",
    "packets_rev",
    "bytes",
    "bytes_rev",
    "tcp_flags",
    "tcp_flags_rev",
    "ts_start",
    "ts_end",
    "duration",
    "source_dataset",
    "source_file",
    "label_class",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "xai-gate-temporal-replay/1.0"})
    tmp = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=180) as response, tmp.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(destination)


def load_tree() -> dict[str, dict[str, Any]]:
    request = urllib.request.Request(HF_TREE_URL, headers={"User-Agent": "xai-gate-temporal-replay/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return {str(row["path"]): row for row in payload if row.get("type") == "file"}


def expected_source_file(filename: str) -> str:
    class_name, stem = filename.removesuffix(".parquet").split("__", 1)
    return f"{class_name}/{stem}.pcap"


def inspect_parquet(path: Path, expected_name: str) -> dict[str, Any]:
    frame = pd.read_parquet(path)
    columns = [str(c) for c in frame.columns]
    missing = sorted(REQUIRED_COLUMNS - set(columns))

    start = pd.to_numeric(frame.get("ts_start"), errors="coerce")
    end = pd.to_numeric(frame.get("ts_end"), errors="coerce")
    start_finite = start.map(math.isfinite) if len(start) else pd.Series([], dtype=bool)
    end_finite = end.map(math.isfinite) if len(end) else pd.Series([], dtype=bool)
    both = start_finite & end_finite
    invalid_order = int(((end < start) & both).sum()) if len(frame) else 0

    source_values = sorted(str(x) for x in frame["source_file"].dropna().unique()) if "source_file" in frame else []
    label_values = sorted(str(x) for x in frame["label_class"].dropna().unique()) if "label_class" in frame else []
    dataset_values = sorted(str(x) for x in frame["source_dataset"].dropna().unique()) if "source_dataset" in frame else []

    ts_min = float(start[both].min()) if bool(both.any()) else None
    ts_max = float(end[both].max()) if bool(both.any()) else None
    observed_span = (ts_max - ts_min) if ts_min is not None and ts_max is not None else None
    row_order_non_decreasing = bool(start.dropna().is_monotonic_increasing) if len(frame) else True

    expected_source = expected_source_file(expected_name)
    expected_label = expected_name.split("__", 1)[0]

    return {
        "rows": int(len(frame)),
        "columns": columns,
        "missing_required_columns": missing,
        "source_file_values": source_values,
        "expected_source_file": expected_source,
        "source_file_matches_expected": source_values == [expected_source],
        "label_class_values": label_values,
        "expected_label_class": expected_label,
        "label_class_matches_expected": label_values == [expected_label],
        "source_dataset_values": dataset_values,
        "finite_ts_start_rows": int(start_finite.sum()),
        "finite_ts_end_rows": int(end_finite.sum()),
        "invalid_timestamp_order_rows": invalid_order,
        "ts_start_min": ts_min,
        "ts_end_max": ts_max,
        "observed_span_seconds": observed_span,
        "stored_row_order_non_decreasing_ts_start": row_order_non_decreasing,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_root = root / "data" / "ciciot2023_temporal"
    calibration_dir = data_root / "calibration"
    replay_dir = data_root / "replay"
    manifest_path = data_root / "ciciot2023_acquisition_manifest.json"
    readme_path = data_root / "SOURCE_README.md"

    tree = load_tree()
    selected = [("calibration", f) for f in CALIBRATION_FILES] + [("replay", f) for f in REPLAY_FILES]
    missing_remote = [name for _, name in selected if name not in tree]
    if missing_remote:
        raise RuntimeError(f"Missing selected files in remote tree: {missing_remote}")

    if not readme_path.exists():
        download(MIRROR_README_URL, readme_path)

    records: list[dict[str, Any]] = []
    for role, filename in selected:
        destination = (calibration_dir if role == "calibration" else replay_dir) / filename
        expected_size = int(tree[filename].get("size", 0))
        if not destination.exists() or destination.stat().st_size != expected_size:
            encoded = urllib.parse.quote(filename)
            download(f"{HF_RESOLVE_BASE}/{encoded}", destination)
        actual_size = destination.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(f"Size mismatch for {filename}: local={actual_size}, expected={expected_size}")
        inspection = inspect_parquet(destination, filename)
        records.append(
            {
                "role": role,
                "filename": filename,
                "remote_url": f"{HF_RESOLVE_BASE}/{urllib.parse.quote(filename)}",
                "remote_size_bytes": expected_size,
                "local_size_bytes": actual_size,
                "sha256": sha256_file(destination),
                "inspection": inspection,
            }
        )
        print(f"{role:11s} {filename:78s} rows={inspection['rows']:8d} span_s={inspection['observed_span_seconds']}")

    payload = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "CICIoT2023",
        "dataset_doi": DATASET_DOI,
        "official_dataset_page": OFFICIAL_DATASET_PAGE,
        "compact_mirror_repo": DATASET_REPO,
        "compact_mirror_tree_api": HF_TREE_URL,
        "compact_mirror_readme_url": MIRROR_README_URL,
        "original_pcap_mirror_repo": ORIGINAL_PCAP_MIRROR,
        "selection_rule": "exactly the calibration and replay files listed in this public script",
        "records": records,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest={manifest_path}")
    print(f"records={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

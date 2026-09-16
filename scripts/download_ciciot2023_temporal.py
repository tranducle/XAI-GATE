#!/usr/bin/env python3
"""Acquire the selected CICIoT2023 files for timestamp-preserving replay.

The script accepts an optional HTTPS base URL so the public protocol remains usable
if the dataset host changes. Without a base URL it writes the selection manifest and
prints the required filenames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ciciot2023_temporal" / "raw"

REPLAY_FILES = [
    "BenignTraffic.parquet",
    "Recon-PingSweep.parquet",
    "Recon-PortScan.parquet",
    "DDoS-SynonymousIP_Flood13.parquet",
    "Backdoor_Malware.parquet",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="", help="HTTPS directory containing the selected parquet files.")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name in REPLAY_FILES:
        path = OUT / name
        if args.base_url and not path.exists():
            url = args.base_url.rstrip("/") + "/" + name
            urllib.request.urlretrieve(url, path)
        records.append({"filename": name, "present": path.exists(), "sha256": sha256(path) if path.exists() else None})
    manifest = ROOT / "data" / "ciciot2023_temporal" / "acquisition_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"selected_replay_files": REPLAY_FILES, "files": records}, indent=2) + "\n")
    print(manifest)
    for record in records:
        print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

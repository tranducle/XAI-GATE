#!/usr/bin/env python3
"""Fail CI if the public tree contains excluded artifacts or development-only identifiers."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_SUFFIXES = {".tex",".pdf",".png",".jpg",".jpeg",".svg",".tif",".tiff",".docx",".csv",".tsv",".parquet",".feather",".joblib",".pkl",".pickle",".npz",".npy",".pt",".pth",".onnx"}
PATH_TOKENS = re.compile(r"(^|/)(r[12]c[0-9]+|stage_[0-9]+|session_handoff|project_management)(/|$)", re.I)
TEXT_TOKENS = re.compile("(" + "|".join(["/" + "Users/", "C:" + r"\\Users\\", "/home/" + r"[^/]+/", "SESSION_" + "STATE", "8_Project_" + "Management", "6_Analysis_" + "Results", "R1_" + "C2", "R2_" + r"C[0-9]+" ]) + ")", re.I)
SKIP_DIRS = {".git",".venv","venv","env","__pycache__","data","results","logs","tables","figures"}


def main() -> int:
    problems = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if PATH_TOKENS.search(rel): problems.append(f"development-only path: {rel}")
        if path.suffix.lower() in EXCLUDED_SUFFIXES: problems.append(f"excluded artifact type: {rel}")
        if rel != "scripts/release_audit.py" and path.suffix.lower() in {".py",".json",".md",".txt",".toml",".yml",".yaml",""}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if TEXT_TOKENS.search(text): problems.append(f"workspace-specific token in: {rel}")
    if problems:
        for problem in problems: print(problem)
        return 1
    print("release_audit=pass")
    return 0


if __name__ == "__main__": raise SystemExit(main())

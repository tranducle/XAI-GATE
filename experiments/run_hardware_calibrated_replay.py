#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from xai_surfacebench.hardware_benchmark import capacity_overlay  # noqa: E402
from xai_surfacebench.temporal_replay import simulate_trace_policy  # noqa: E402

POLICIES=['always_explain','threshold_explain','budget_only_bexgov','selective_explanations_adapted','resource_aware_offload_adapted','xai_gate']
DATA=ROOT/'data'/'ciciot2023_temporal'
RESULT=ROOT/'results'/'hardware_validation'/'replay'
TIMING=ROOT/'results'/'hardware_validation'/'measurements'


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main() -> int:
    RESULT.mkdir(parents=True,exist_ok=True)
    prep=json.loads((DATA/'temporal_preprocessing_manifest.json').read_text())
    measured=json.loads((TIMING/'measured_profiles.json').read_text())
    profiles={'proxy-original':None, **measured}
    rows=[]
    metadata={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'policies':POLICIES,'profile_ids':list(profiles),'sessions':[]}
    for session in prep['sessions']:
        slot_path=ROOT/session['slot_path']
        slots=pd.read_csv(slot_path)
        trace_sha=sha256_file(slot_path)
        metadata['sessions'].append({'filename':session['filename'],'source_file':session['source_file'],'slot_path':session['slot_path'],'slot_sha256':trace_sha,'slots':len(slots)})
        for profile_id,profile in profiles.items():
            overrides=None if profile is None else profile['compute_overrides']
            p95=None if profile is None else profile['absolute_p95_ms']
            for policy in POLICIES:
                result=simulate_trace_policy(
                    slots,
                    policy=policy,
                    session_id=session['filename'],
                    condition='chronological',
                    action_profile_overrides=overrides,
                    collect_action_trace=profile is not None,
                )
                action_trace=result.pop('_action_trace',None)
                result['stage']='hardware_calibrated_replay'
                result['hardware_profile']=profile_id
                result['source_file']=session['source_file']
                result['slot_file_sha256']=trace_sha
                result['compute_profile_sha256']=digest_json(overrides or {'default':'ACTION_PROFILES'})
                if profile is not None:
                    overlay=capacity_overlay(action_trace,p95,capacity_ms=1000.0)
                    for k,v in overlay.items(): result[f'hw_{k}']=v
                    result['hw_p95_profile_sha256']=digest_json(p95)
                    result['full_measurement']=profile['full_measurement']
                else:
                    result['hw_slots']=''
                    result['hw_total_demand_ms']=''
                    result['hw_mean_demand_ms_per_slot']=''
                    result['hw_overload_slots']=''
                    result['hw_overload_slot_fraction']=''
                    result['hw_max_consecutive_overload_slots']=''
                    result['hw_final_work_backlog_ms']=''
                    result['hw_max_work_backlog_ms']=''
                    result['hw_p95_profile_sha256']=''
                    result['full_measurement']='proxy'
                rows.append(result)
                print(f"{session['filename']:60s} {profile_id:12s} {policy:36s} cov={result['high_risk_explanation_coverage']:.4f} debt={result['mean_explanation_debt']:.1f} exp={result['exposure_use']:.4f} overload={result['hw_overload_slot_fraction']}")
    fieldnames=[]
    for row in rows:
        for key in row:
            if key not in fieldnames: fieldnames.append(key)
    with (RESULT/'full_runs.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    metadata['expected_run_count']=len(prep['sessions'])*len(profiles)*len(POLICIES)
    metadata['actual_run_count']=len(rows)
    metadata['timing_profiles_sha256']=sha256_file(TIMING/'measured_profiles.json')
    (RESULT/'full_metadata.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
    print(f"runs={len(rows)}")
    return 0

if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xai_surfacebench.hardware_benchmark import build_measured_compute_profile  # noqa: E402

BASE = ROOT / 'results' / 'hardware_validation' / 'measurements'
ACTIONS = ['none','coarse','full_lime','full_kernelshap','offload','audit','redact','delay']
CONDITIONS = ['physical_m2','arm64_2cpu_4gib','arm64_1cpu_2gib','arm64_0_5cpu_1gib']


def parse_cpu_stat(text: str) -> dict[str, int]:
    out={}
    for line in text.splitlines():
        parts=line.split()
        if len(parts)==2 and parts[1].lstrip('-').isdigit(): out[parts[0]]=int(parts[1])
    return out


def q(s: pd.Series, p: float) -> float:
    return float(np.quantile(s.to_numpy(float), p, method='linear'))


def main() -> int:
    raws=[]; process=[]
    for c in CONDITIONS:
        for action in ACTIONS:
            for rep in range(3):
                csvp=BASE/c/f'{c}__{action}__r{rep}.csv'
                jsonp=BASE/c/f'{c}__{action}__r{rep}.json'
                if not csvp.exists() or not jsonp.exists(): raise RuntimeError(f'missing {c}/{action}/r{rep}')
                raws.append(pd.read_csv(csvp))
                d=json.loads(jsonp.read_text())
                cg=d.get('cgroup',{})
                stat=parse_cpu_stat(cg.get('cpu.stat',''))
                events=parse_cpu_stat(cg.get('memory.events',''))
                process.append({
                    'condition':c,'action':action,'repeat':rep,'peak_rss_mb':d['peak_rss_mb'],
                    'cpu_max':cg.get('cpu.max','host'),'memory_max':cg.get('memory.max','host'),
                    'memory_peak_bytes':int(cg.get('memory.peak','0')) if str(cg.get('memory.peak','0')).isdigit() else 0,
                    'nr_periods':stat.get('nr_periods',0),'nr_throttled':stat.get('nr_throttled',0),
                    'throttled_usec':stat.get('throttled_usec',0),'oom':events.get('oom',0),'oom_kill':events.get('oom_kill',0),
                })
    raw=pd.concat(raws,ignore_index=True)
    proc=pd.DataFrame(process)
    raw.to_csv(BASE/'raw_combined.csv',index=False)
    proc.to_csv(BASE/'process_resources.csv',index=False)

    rows=[]
    for (c,a),g in raw.groupby(['condition','action'],sort=False):
        good=g[g.success==1]
        p=proc[(proc.condition==c)&(proc.action==a)]
        periods=int(p.nr_periods.sum()); throttled=int(p.nr_throttled.sum())
        rows.append({
            'condition':c,'action':a,'observations':len(g),'success_rate':float(g.success.mean()),
            'median_ms':float(good.latency_ms.median()),'p95_ms':q(good.latency_ms,.95),'p99_ms':q(good.latency_ms,.99),
            'q25_ms':q(good.latency_ms,.25),'q75_ms':q(good.latency_ms,.75),'iqr_ms':q(good.latency_ms,.75)-q(good.latency_ms,.25),
            'max_peak_rss_mb':float(p.peak_rss_mb.max()),'max_cgroup_memory_peak_mb':float(p.memory_peak_bytes.max()/1024**2),
            'nr_periods':periods,'nr_throttled':throttled,'throttle_period_fraction':throttled/periods if periods else 0.0,
            'throttled_seconds':float(p.throttled_usec.sum()/1e6),'oom':int(p.oom.sum()),'oom_kill':int(p.oom_kill.sum()),
            'single_worker_capacity_per_s_p95':1000.0/q(good.latency_ms,.95) if q(good.latency_ms,.95)>0 else None,
        })
    summary=pd.DataFrame(rows)
    summary.to_csv(BASE/'timing_summary.csv',index=False)

    effects=[]
    for action in ACTIONS:
        ref=raw[(raw.condition=='arm64_2cpu_4gib')&(raw.action==action)][['repeat','record_id','latency_ms']].rename(columns={'latency_ms':'reference_ms'})
        for c in ['arm64_1cpu_2gib','arm64_0_5cpu_1gib']:
            other=raw[(raw.condition==c)&(raw.action==action)][['repeat','record_id','latency_ms']].rename(columns={'latency_ms':'test_ms'})
            paired=ref.merge(other,on=['repeat','record_id'],validate='one_to_one')
            ratio=paired.test_ms/paired.reference_ms.clip(lower=1e-12)
            effects.append({'condition':c,'action':action,'pairs':len(paired),'median_latency_ratio_vs_2cpu_4gib':float(ratio.median()),'p95_latency_ratio_vs_2cpu_4gib':q(ratio,.95),'median_delta_ms':float((paired.test_ms-paired.reference_ms).median())})
    pd.DataFrame(effects).to_csv(BASE/'resource_effects.csv',index=False)

    profiles={}
    for c in ['physical_m2','arm64_1cpu_2gib','arm64_0_5cpu_1gib']:
        med={row.action:float(row.median_ms) for row in summary[summary.condition==c].itertuples()}
        p95={row.action:float(row.p95_ms) for row in summary[summary.condition==c].itertuples()}
        for explainer,measurement in [('LIME','full_lime'),('SHAP','full_kernelshap')]:
            compute=build_measured_compute_profile(med,full_measurement=measurement)
            abs_p95={
                'none':p95['none'],'coarse':p95['coarse'],'full':p95[measurement],
                'offload':p95['offload'],'audit':p95['audit'],'redact':p95['redact'],'delay':p95['delay'],
            }
            profiles[f'{c}-{explainer}']={'condition':c,'full_measurement':measurement,'compute_overrides':compute,'absolute_p95_ms':abs_p95,'absolute_median_ms':med}
    (BASE/'measured_profiles.json').write_text(json.dumps(profiles,indent=2,sort_keys=True)+'\n')

    print(summary.to_string(index=False))
    print('\nRESOURCE EFFECTS')
    print(pd.DataFrame(effects).to_string(index=False))
    return 0

if __name__=='__main__': raise SystemExit(main())

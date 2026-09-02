#!/usr/bin/env python3
from __future__ import annotations
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=json.loads((ROOT/'config/performance_resilience_policy.json').read_text()); values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text(); hpa=(ROOT/'infra/helm/medclaimiq/templates/hpa.yaml').read_text(); keda=(ROOT/'infra/helm/medclaimiq/templates/keda-scaledobject.yaml').read_text()
    assert f"cpuUtilization: {p['autoscaling']['api_cpu_target_percent']}" in values
    assert 'HorizontalPodAutoscaler' in hpa and 'maxReplicas' in hpa
    assert 'ScaledObject' in keda and 'lagThreshold' in keda
    assert str(p['autoscaling']['kafka_lag_scale_threshold']) in values
    assert f"max_inflight: int = {p['worker_backpressure']['max_inflight']}" in (ROOT/'backend/app/core/config.py').read_text()
    assert f"pause_threshold: int = {p['worker_backpressure']['pause_threshold']}" in (ROOT/'backend/app/core/config.py').read_text()
    print('autoscaling/capacity contract: PASS')
if __name__=='__main__': main()

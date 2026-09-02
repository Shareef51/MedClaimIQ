from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.domain.performance_resilience import MetricBudget, percentile, regression_fraction, summarize_latencies
from app.resilience.degradation import Dependency, plan_for
from app.resilience.fault_injection import ControlledFaultInjector, FaultMode, FaultProfile
from app.realtime.consumer import BoundedWorkerPool
from app.mcp.circuit import CircuitBreakerRegistry
from app.domain.mcp import MCPCircuitState, MCPPolicyError

ROOT=Path(__file__).resolve().parents[2]


def test_performance_resilience_model_is_public_and_safety_first():
    r=TestClient(app).get('/api/v1/performance-resilience-model')
    assert r.status_code==200
    b=r.json()
    assert b['quality_model']=='measured-load-plus-failure-injection-with-release-regression-gates'
    assert b['safety']['synthetic_data_only'] is True
    assert b['safety']['production_chaos_requires_human_approval'] is True
    assert b['resilience']['dependency_failure_must_not_bypass_authorization'] is True


def test_percentile_and_metric_budget_are_deterministic():
    values=[10,20,30,40,50,60,70,80,90,100]
    assert percentile(values,.95)==100
    summary=summarize_latencies(values)
    assert summary['p50_ms']==50
    assert summary['p95_ms']==100
    assert MetricBudget('x',100).passes(99.9)
    assert not MetricBudget('x',100).passes(100.1)
    assert MetricBudget('throughput',100,'gte').passes(120)


def test_regression_fraction_handles_zero_baseline_fail_safe():
    assert regression_fraction(0,0)==0
    assert regression_fraction(1,0)==1
    assert round(regression_fraction(110,100),3)==0.1


def test_every_dependency_degradation_plan_preserves_authorization_and_no_partial_write():
    for dep in Dependency:
        plan=plan_for(dep)
        assert plan.preserves_authorization is True
        assert plan.allows_partial_write is False
    assert plan_for('kafka').fallback=='transactional-outbox-retains-events'
    assert plan_for('qdrant').fallback=='structured-authoritative-evidence-or-human-review'
    assert plan_for('postgresql').fallback=='fail-request-no-unsafe-partial-write'


def test_worker_pool_pauses_and_saturates_at_bounded_capacity():
    pool=BoundedWorkerPool(max_inflight=4,pause_threshold=3)
    pool.acquire(); pool.acquire(); assert pool.paused is False
    pool.acquire(); assert pool.paused is True
    pool.acquire()
    try:
        pool.acquire(); raise AssertionError('saturation should fail')
    except RuntimeError as exc:
        assert 'saturated' in str(exc)
    pool.release(); pool.release(); assert pool.paused is False


def test_mcp_circuit_breaker_opens_and_fast_fails():
    circuit=CircuitBreakerRegistry(failure_threshold=2,recovery_seconds=60)
    circuit.failure('synthetic.tool'); circuit.failure('synthetic.tool')
    assert circuit.state('synthetic.tool') is MCPCircuitState.OPEN
    try:
        circuit.before_call('synthetic.tool'); raise AssertionError('open circuit should fail')
    except MCPPolicyError as exc:
        assert 'circuit is open' in str(exc)
    circuit.success('synthetic.tool')
    assert circuit.state('synthetic.tool') is MCPCircuitState.CLOSED


def test_checked_in_performance_and_resilience_gates_pass(tmp_path):
    perf=subprocess.run([sys.executable,str(ROOT/'scripts/run_performance_gate.py'),'--candidate','test','--gate','--report-dir',str(tmp_path)],cwd=ROOT,text=True,capture_output=True)
    assert perf.returncode==0, perf.stdout+perf.stderr
    res=subprocess.run([sys.executable,str(ROOT/'scripts/run_resilience_gate.py'),'--gate','--report-dir',str(tmp_path)],cwd=ROOT,text=True,capture_output=True)
    assert res.returncode==0, res.stdout+res.stderr
    assert json.loads((tmp_path/'performance-gate.json').read_text())['decision']=='pass'
    assert json.loads((tmp_path/'resilience-gate.json').read_text())['decision']=='pass'


def test_performance_gate_blocks_latency_regression(tmp_path):
    candidate=json.loads((ROOT/'sample-data/performance_results_v1.json').read_text())
    candidate['metrics']['rag_hybrid_p95_ms']=1700.0  # still under hard 1800 budget, but >10% baseline regression
    path=tmp_path/'candidate.json'; path.write_text(json.dumps(candidate))
    proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_performance_gate.py'),'--results',str(path),'--gate','--report-dir',str(tmp_path/'out')],cwd=ROOT,text=True,capture_output=True)
    assert proc.returncode==1
    report=json.loads((tmp_path/'out/performance-gate.json').read_text())
    assert report['decision']=='block' and 'rag_hybrid_p95_ms' in report['blocked_by']


def test_kafka_backlog_model_recovers_with_positive_drain_rate():
    proc=subprocess.run([sys.executable,str(ROOT/'performance/kafka/backlog_stress.py'),'--backlog','5000','--producer-eps','50','--consumer-eps','150','--max-minutes','15'],cwd=ROOT,text=True,capture_output=True)
    assert proc.returncode==0
    b=json.loads(proc.stdout); assert b['recovered'] is True and b['recovery_seconds']<=900


def test_release_policy_includes_performance_resilience_gate():
    policy=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
    assert 'performance-resilience' in policy['gates']['required']
    workflow=(ROOT/'.github/workflows/release-promotion.yml').read_text()
    assert 'performance_run_id' in workflow and 'performance_report_sha256' in workflow
    assert '--gate performance-resilience=pass' in workflow


def test_controlled_fault_injection_is_staging_only_and_explicit():
    try:
        ControlledFaultInjector(environment='production', explicitly_authorized=True)
        raise AssertionError('production fault injector must be disabled')
    except RuntimeError as exc:
        assert 'forbidden in production' in str(exc)
    try:
        ControlledFaultInjector(environment='staging', explicitly_authorized=False)
        raise AssertionError('staging fault injection still requires approval')
    except RuntimeError as exc:
        assert 'explicit authorization' in str(exc)
    injector=ControlledFaultInjector(environment='staging', explicitly_authorized=True)
    try:
        injector.call(FaultProfile('openai',FaultMode.TIMEOUT,error_message='synthetic timeout'),lambda:'ok')
        raise AssertionError('timeout fault expected')
    except TimeoutError as exc:
        assert 'synthetic timeout' in str(exc)


def test_availability_report_is_generated_after_gates(tmp_path):
    subprocess.run([sys.executable,str(ROOT/'scripts/run_performance_gate.py'),'--gate','--report-dir',str(tmp_path)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/run_resilience_gate.py'),'--gate','--report-dir',str(tmp_path)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/generate_capacity_model.py'),'--output',str(tmp_path/'capacity-model.json')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/generate_availability_resilience_report.py'),'--report-dir',str(tmp_path)],cwd=ROOT,check=True)
    r=json.loads((tmp_path/'availability-resilience-report.json').read_text())
    assert r['release_recommendation']=='pass' and r['availability_target']==0.999

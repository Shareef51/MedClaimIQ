from pathlib import Path

def test_regulatory_supervision_frontend_bff_sse_worker_and_ui_contracts():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/regulatory-supervision/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text()
    for token in ['Regulatory Supervisory Control','Authority boundary','Supervisory reconciliation queue','Compliance exceptions','Regulatory calendar']:assert token in page
    for token in ['regulatorySupervisionDashboard','refreshRegulatorySupervisionCases','prepareRegulatorySupervisionAttestation','certifyRegulatorySupervision','regulatorySupervisionTraceability']:assert token in api
    assert 'regulatory-supervision' in bff and 'regulatory_supervision.' in sse and 'regulatory-supervisory-control' in runtime and 'regulatory-supervisory-control:' in helm and 'Regulatory Supervision' in shell

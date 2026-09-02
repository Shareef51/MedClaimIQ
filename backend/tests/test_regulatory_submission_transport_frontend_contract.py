from pathlib import Path

def test_regulatory_transport_frontend_bff_sse_worker_and_ui_contracts():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/regulatory-transport/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text()
    for token in ['Regulatory Submission Transport','one-time human release','Authority boundary','Transmission operations']:assert token in page
    for token in ['regulatoryTransportDashboard','registerRegulatoryDestination','releaseRegulatoryPackage','recoverRegulatoryTransmission','regulatoryTransmissionTraceability']:assert token in api
    assert 'regulatory-transport' in bff and 'regulatory_transport.' in sse and 'regulatory-submission-transport' in runtime and 'regulatory-submission-transport:' in helm and 'Regulatory Transport' in shell

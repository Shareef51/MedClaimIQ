from pathlib import Path

def test_release49_frontend_bff_sse_worker_and_ui_contracts():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/recovery-control-assurance/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text()
    for token in ['Recovery Portfolio Control Assurance','Lock report version','Independent human certify','Human stage submission','Authority boundary']:assert token in page
    for token in ['recoveryControlAssuranceDashboard','createRegulatorySubmissionPackage','certifyRegulatorySubmissionPackage','stageRegulatorySubmissionPackage','recordRegulatorySubmissionReceipt']:assert token in api
    assert 'recovery-control-assurance' in bff and 'recovery_control_assurance.' in sse and 'recovery-control-assurance' in runtime and 'recovery-control-assurance:' in helm and 'Control Assurance' in shell

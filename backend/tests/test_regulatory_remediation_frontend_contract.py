from pathlib import Path

def test_regulatory_remediation_frontend_bff_runtime_and_navigation_contract():
    root=Path(__file__).resolve().parents[2]
    page=(root/'frontend/app/review/regulatory-remediation/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text()
    for token in ['Regulatory Findings Remediation','AI authority','Independent approve','Independent certify closure','regulatoryRemediationTraceability']:assert token in page+api
    assert 'regulatory-remediation' in bff and '/review/regulatory-remediation' in shell
    assert 'regulatory-remediation' in runtime and 'regulatory-remediation' in helm

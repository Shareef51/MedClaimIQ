from pathlib import Path
def test_release43_frontend_and_bff_contract():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/financial-investigations/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text()
    for token in ['Payment Integrity Investigations','Immutable evidence pack','Root cause','Remediation','SLA','AI authority: recommendation only']:assert token in page
    for token in ['financialInvestigationQueue','financialInvestigationWorkbench','acquireFinancialInvestigationLease','proposeFinancialRemediation']:assert token in api
    assert 'financial-investigations' in bff and '/review/financial-investigations' in shell

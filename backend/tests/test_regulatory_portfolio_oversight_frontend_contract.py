from pathlib import Path

def test_regulatory_portfolio_frontend_bff_runtime_navigation_and_api_contract():
    root=Path(__file__).resolve().parents[2];page=(root/'frontend/app/review/regulatory-portfolio-oversight/page.tsx').read_text();api=(root/'frontend/lib/api.ts').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();shell=(root/'frontend/components/review/app-shell.tsx').read_text();runtime=(root/'backend/app/workers/production_runtime.py').read_text();helm=(root/'infra/helm/medclaimiq/values.yaml').read_text()
    for token in ['Regulatory Remediation Portfolio Oversight','Systemic control / recurrence clusters','Management attestation','Independent certify portfolio','Board / regulatory package']:assert token in page
    for token in ['regulatoryPortfolioDashboard','createRegulatoryPortfolioSnapshot','certifyRegulatoryPortfolio','regulatoryPortfolioBoardPackage']:assert token in api
    assert 'regulatory-portfolio-oversight' in bff and '/review/regulatory-portfolio-oversight' in shell and 'regulatory-portfolio-oversight' in runtime and 'regulatory-portfolio-oversight' in helm

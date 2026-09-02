from app.db.session import SessionLocal
from app.services.regulatory_portfolio_oversight import RegulatoryPortfolioOversightService

def run_tenant(tenant_id:str):
    # Monitoring only: portfolio aging/systemic-risk telemetry. It never prepares or approves remediation,
    # performs authoritative testing, accepts risk, attests management, certifies controls, posts journals,
    # authorizes payments, represents a regulator, collects funds, or moves money.
    with SessionLocal() as db:
        result=RegulatoryPortfolioOversightService(db,tenant_id).monitor_portfolio(actor_id="regulatory-portfolio-worker",actor_type="monitoring_worker")
        db.commit();return result
def run_all_tenants(tenant_ids):return sum(run_tenant(t) for t in tenant_ids)

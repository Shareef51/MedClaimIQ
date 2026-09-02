from app.db.session import SessionLocal
from app.repositories.regulatory_reopened_outcome_validation import RegulatoryReopenedOutcomeRepository


def run_tenant(tenant_id: str) -> dict:
    with SessionLocal() as session:
        repo = RegulatoryReopenedOutcomeRepository(session, tenant_id)
        assurances = repo.assurances()
        return {
            "tenant_id": tenant_id,
            "assurance_versions": len(assurances),
            "blocked": sum(a.status == "blocked" for a in assurances),
            "second_recurrence_escalations": sum(a.second_recurrence_escalated for a in assurances),
            "write_authority": "monitoring_only",
        }


def run_all_tenants(tenant_ids: list[str]): return [run_tenant(t) for t in tenant_ids]

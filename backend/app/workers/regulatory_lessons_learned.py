from app.db.session import SessionLocal
from app.repositories.regulatory_lessons_learned import RegulatoryLessonsLearnedRepository


def run_tenant(tenant_id: str) -> dict:
    with SessionLocal() as session:
        repo = RegulatoryLessonsLearnedRepository(session, tenant_id)
        lessons, proposals, feedback = repo.lessons(), repo.proposals(), repo.feedback()
        return {
            "tenant_id": tenant_id,
            "candidate_lessons": sum(x.status == "candidate_human_review" for x in lessons),
            "pending_improvements": sum(x.status == "proposed" for x in proposals),
            "regulatory_feedback_observations": len(feedback),
            "write_authority": "monitoring_and_recommendation_only",
        }


def run_all_tenants(tenant_ids: list[str]): return [run_tenant(t) for t in tenant_ids]

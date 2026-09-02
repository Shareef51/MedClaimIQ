"""Read-only outcome refresh / case bootstrap worker for Release 44.

The worker may discover executed Release 43 remediation referrals and create durable
recovery tracking cases. It intentionally has no dispute-resolution, recovery amount,
accounting approval, payment authorization, journal posting, settlement or fund movement calls.
"""
from sqlalchemy import select
from app.db.session import get_session_factory
from app.models.financial_investigation import FinancialRemediationProposalModel
from app.services.recovery_operations import RecoveryOperationsService

def run_tenant(tenant_id:str)->dict[str,int]:
    created=0;factory=get_session_factory()
    with factory() as db:
        proposals=list(db.scalars(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==tenant_id,FinancialRemediationProposalModel.status=="executed",FinancialRemediationProposalModel.referral_id.is_not(None))))
        svc=RecoveryOperationsService(db,tenant_id)
        for p in proposals:
            if p.remediation_type=="no_financial_action":continue
            if svc.repo.source_case(p.proposal_id):continue
            svc.create_from_remediation(p.proposal_id,None,actor_type="system",idempotency_key=f"worker:{p.proposal_id}");created+=1
        db.commit()
    return {"created":created}
def run_all_tenants(tenant_ids:list[str])->dict[str,dict[str,int]]:return {t:run_tenant(t) for t in tenant_ids}

"""Release 45 provider-dispute evidence processing worker.

Only processes evidence rows that were previously registered through an authorized
human/provider API path. It cannot register evidence, resolve disputes, post journals,
authorize payments, collect funds, or move money.
"""
from sqlalchemy import select
from app.db.session import get_session_factory
from app.models.provider_dispute_intelligence import DisputeEvidenceReingestionModel
from app.services.provider_dispute_intelligence import ProviderDisputeIntelligenceService

def run_tenant(tenant_id:str,limit:int=25)->dict[str,int]:
    processed=0;factory=get_session_factory()
    with factory() as db:
        rows=list(db.scalars(select(DisputeEvidenceReingestionModel).where(DisputeEvidenceReingestionModel.tenant_id==tenant_id,DisputeEvidenceReingestionModel.source_kind=="evidence",DisputeEvidenceReingestionModel.status=="pending").limit(limit)))
        svc=ProviderDisputeIntelligenceService(db,tenant_id)
        for row in rows:
            svc.process_evidence(row.recovery_case_id,row.dispute_id,row.source_id,None,trace_id=row.trace_id);processed+=1
        db.commit()
    return {"processed":processed}
def run_all_tenants(tenant_ids:list[str])->dict[str,dict[str,int]]:return {t:run_tenant(t) for t in tenant_ids}

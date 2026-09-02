from __future__ import annotations

from datetime import datetime
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.communication_delivery import (
    CommunicationDispatchModel, CommunicationEndpointModel, CommunicationIncidentModel,
    CommunicationLegalHoldModel, CommunicationReceiptModel, CommunicationReconciliationModel,
    CommunicationTemplateModel,
)


class CommunicationDeliveryRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)

    def add(self,row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def endpoint(self, endpoint_id:str):
        return self.session.scalar(select(CommunicationEndpointModel).where(CommunicationEndpointModel.tenant_id==self.tenant_id,CommunicationEndpointModel.endpoint_id==endpoint_id))

    def endpoints(self, claim_id:str, audience:str):
        return list(self.session.scalars(select(CommunicationEndpointModel).where(CommunicationEndpointModel.tenant_id==self.tenant_id,CommunicationEndpointModel.claim_id==claim_id,CommunicationEndpointModel.audience==audience,CommunicationEndpointModel.active.is_(True))))

    def approved_template(self,template_key:str,locale:str,channel:str):
        return self.session.scalar(select(CommunicationTemplateModel).where(CommunicationTemplateModel.tenant_id==self.tenant_id,CommunicationTemplateModel.template_key==template_key,CommunicationTemplateModel.locale==locale,CommunicationTemplateModel.channel==channel,CommunicationTemplateModel.status=="approved").order_by(CommunicationTemplateModel.approved_at.desc()).limit(1))

    def dispatch(self,dispatch_id:str,*,for_update:bool=False):
        stmt=select(CommunicationDispatchModel).where(CommunicationDispatchModel.tenant_id==self.tenant_id,CommunicationDispatchModel.dispatch_id==dispatch_id)
        if for_update: stmt=stmt.with_for_update()
        return self.session.scalar(stmt)

    def dispatches(self,claim_id:str|None=None,notice_id:str|None=None):
        stmt=select(CommunicationDispatchModel).where(CommunicationDispatchModel.tenant_id==self.tenant_id)
        if claim_id: stmt=stmt.where(CommunicationDispatchModel.claim_id==claim_id)
        if notice_id: stmt=stmt.where(CommunicationDispatchModel.notice_id==notice_id)
        return list(self.session.scalars(stmt.order_by(CommunicationDispatchModel.created_at)))

    def lease_candidates(self,now:datetime,limit:int):
        stmt=select(CommunicationDispatchModel).where(
            CommunicationDispatchModel.tenant_id==self.tenant_id,
            CommunicationDispatchModel.status.in_(["queued","retry_pending","leased"]),
            CommunicationDispatchModel.next_attempt_at<=now,
            or_(CommunicationDispatchModel.lease_until.is_(None),CommunicationDispatchModel.lease_until<=now),
        ).order_by(CommunicationDispatchModel.regulatory_deadline_at,CommunicationDispatchModel.next_attempt_at).limit(limit).with_for_update()
        return list(self.session.scalars(stmt))

    def receipt_by_event(self,provider_name:str,provider_event_id:str):
        return self.session.scalar(select(CommunicationReceiptModel).where(CommunicationReceiptModel.tenant_id==self.tenant_id,CommunicationReceiptModel.provider_name==provider_name,CommunicationReceiptModel.provider_event_id==provider_event_id))

    def receipts(self,dispatch_id:str):
        return list(self.session.scalars(select(CommunicationReceiptModel).where(CommunicationReceiptModel.tenant_id==self.tenant_id,CommunicationReceiptModel.dispatch_id==dispatch_id).order_by(CommunicationReceiptModel.occurred_at)))

    def active_holds(self,claim_id:str):
        return list(self.session.scalars(select(CommunicationLegalHoldModel).where(CommunicationLegalHoldModel.tenant_id==self.tenant_id,CommunicationLegalHoldModel.claim_id==claim_id,CommunicationLegalHoldModel.released_at.is_(None))))

    def incidents(self,status:str|None=None):
        stmt=select(CommunicationIncidentModel).where(CommunicationIncidentModel.tenant_id==self.tenant_id)
        if status: stmt=stmt.where(CommunicationIncidentModel.status==status)
        return list(self.session.scalars(stmt.order_by(CommunicationIncidentModel.created_at.desc())))

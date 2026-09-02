from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_submission_transport import *

class RegulatorySubmissionTransportRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def destination(self,destination_id):return self.session.scalar(select(RegulatoryDestinationModel).where(RegulatoryDestinationModel.tenant_id==self.tenant_id,RegulatoryDestinationModel.destination_id==destination_id))
    def destinations(self):return list(self.session.scalars(select(RegulatoryDestinationModel).where(RegulatoryDestinationModel.tenant_id==self.tenant_id).order_by(RegulatoryDestinationModel.regulator_name)))
    def release(self,release_id):return self.session.scalar(select(RegulatorySubmissionReleaseModel).where(RegulatorySubmissionReleaseModel.tenant_id==self.tenant_id,RegulatorySubmissionReleaseModel.release_id==release_id))
    def release_for_package(self,package_id):return self.session.scalar(select(RegulatorySubmissionReleaseModel).where(RegulatorySubmissionReleaseModel.tenant_id==self.tenant_id,RegulatorySubmissionReleaseModel.package_id==package_id))
    def transmission(self,transmission_id,for_update=False):
        q=select(RegulatoryTransmissionModel).where(RegulatoryTransmissionModel.tenant_id==self.tenant_id,RegulatoryTransmissionModel.transmission_id==transmission_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def transmission_for_release(self,release_id):return self.session.scalar(select(RegulatoryTransmissionModel).where(RegulatoryTransmissionModel.tenant_id==self.tenant_id,RegulatoryTransmissionModel.release_id==release_id))
    def transmissions(self):return list(self.session.scalars(select(RegulatoryTransmissionModel).where(RegulatoryTransmissionModel.tenant_id==self.tenant_id).order_by(RegulatoryTransmissionModel.created_at.desc())))
    def attempts(self,transmission_id):return list(self.session.scalars(select(RegulatoryDeliveryAttemptModel).where(RegulatoryDeliveryAttemptModel.tenant_id==self.tenant_id,RegulatoryDeliveryAttemptModel.transmission_id==transmission_id).order_by(RegulatoryDeliveryAttemptModel.attempt_sequence)))
    def acknowledgments(self,transmission_id):return list(self.session.scalars(select(RegulatoryAcknowledgmentModel).where(RegulatoryAcknowledgmentModel.tenant_id==self.tenant_id,RegulatoryAcknowledgmentModel.transmission_id==transmission_id).order_by(RegulatoryAcknowledgmentModel.received_at)))
    def ack_by_event(self,destination_id,event_id):return self.session.scalar(select(RegulatoryAcknowledgmentModel).where(RegulatoryAcknowledgmentModel.tenant_id==self.tenant_id,RegulatoryAcknowledgmentModel.destination_id==destination_id,RegulatoryAcknowledgmentModel.external_event_id==event_id))
    def incidents(self):return list(self.session.scalars(select(RegulatoryTransportIncidentModel).where(RegulatoryTransportIncidentModel.tenant_id==self.tenant_id).order_by(RegulatoryTransportIncidentModel.created_at.desc())))
    def audit(self,transmission_id):return list(self.session.scalars(select(RegulatoryTransmissionAuditEventModel).where(RegulatoryTransmissionAuditEventModel.tenant_id==self.tenant_id,RegulatoryTransmissionAuditEventModel.transmission_id==transmission_id).order_by(RegulatoryTransmissionAuditEventModel.sequence)))

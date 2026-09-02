from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RegulatoryDestinationModel(Base):
    __tablename__="regulatory_destinations"
    __table_args__=(UniqueConstraint("tenant_id","destination_key","registry_version",name="uq_reg_destination_version"),Index("ix_reg_destination_active","tenant_id","active"),)
    destination_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    destination_key:Mapped[str]=mapped_column(String(100),nullable=False)
    regulator_name:Mapped[str]=mapped_column(String(180),nullable=False)
    transport_type:Mapped[str]=mapped_column(String(40),nullable=False)
    endpoint_reference:Mapped[str]=mapped_column(String(240),nullable=False)
    schema_name:Mapped[str]=mapped_column(String(120),nullable=False)
    schema_version:Mapped[str]=mapped_column(String(40),nullable=False)
    registry_version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    failure_streak:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    circuit_open_until:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    last_failure_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class RegulatorySubmissionReleaseModel(Base):
    __tablename__="regulatory_submission_releases"
    __table_args__=(UniqueConstraint("tenant_id","package_id",name="uq_reg_release_package"),UniqueConstraint("tenant_id","idempotency_key",name="uq_reg_release_idem"),)
    release_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    package_id:Mapped[str]=mapped_column(ForeignKey("regulatory_submission_packages.package_id",ondelete="RESTRICT"),nullable=False)
    certification_id:Mapped[str]=mapped_column(ForeignKey("regulatory_certifications.certification_id",ondelete="RESTRICT"),nullable=False)
    destination_id:Mapped[str]=mapped_column(ForeignKey("regulatory_destinations.destination_id",ondelete="RESTRICT"),nullable=False)
    package_version:Mapped[int]=mapped_column(Integer,nullable=False)
    locked_manifest_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    certification_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    schema_name:Mapped[str]=mapped_column(String(120),nullable=False)
    schema_version:Mapped[str]=mapped_column(String(40),nullable=False)
    release_reason:Mapped[str]=mapped_column(Text,nullable=False)
    released_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    release_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    idempotency_key:Mapped[str]=mapped_column(String(180),nullable=False)
    released_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class RegulatoryTransmissionModel(Base):
    __tablename__="regulatory_transmissions"
    __table_args__=(UniqueConstraint("tenant_id","release_id",name="uq_reg_transmission_release"),UniqueConstraint("tenant_id","dispatch_key",name="uq_reg_transmission_dispatch"),Index("ix_reg_transmission_status","tenant_id","status","next_attempt_at"),)
    transmission_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    release_id:Mapped[str]=mapped_column(ForeignKey("regulatory_submission_releases.release_id",ondelete="RESTRICT"),nullable=False)
    package_id:Mapped[str]=mapped_column(ForeignKey("regulatory_submission_packages.package_id",ondelete="RESTRICT"),nullable=False)
    destination_id:Mapped[str]=mapped_column(ForeignKey("regulatory_destinations.destination_id",ondelete="RESTRICT"),nullable=False)
    supersedes_transmission_id:Mapped[str|None]=mapped_column(ForeignKey("regulatory_transmissions.transmission_id",ondelete="RESTRICT"))
    dispatch_key:Mapped[str]=mapped_column(String(180),nullable=False)
    encrypted_envelope:Mapped[str]=mapped_column(Text,nullable=False)
    nonce_b64:Mapped[str]=mapped_column(String(128),nullable=False)
    envelope_signature:Mapped[str]=mapped_column(String(128),nullable=False)
    envelope_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    status:Mapped[str]=mapped_column(String(40),nullable=False,default="queued")
    attempt_count:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    max_attempts:Mapped[int]=mapped_column(Integer,nullable=False,default=5)
    next_attempt_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    lease_owner:Mapped[str|None]=mapped_column(String(128))
    lease_expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    provider_message_id:Mapped[str|None]=mapped_column(String(240))
    external_submission_reference:Mapped[str|None]=mapped_column(String(240))
    deadline_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class RegulatoryDeliveryAttemptModel(Base):
    __tablename__="regulatory_delivery_attempts"
    __table_args__=(UniqueConstraint("tenant_id","transmission_id","attempt_sequence",name="uq_reg_delivery_attempt_sequence"),Index("ix_reg_delivery_attempt_tx","tenant_id","transmission_id","attempt_sequence"),)
    attempt_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    transmission_id:Mapped[str]=mapped_column(ForeignKey("regulatory_transmissions.transmission_id",ondelete="CASCADE"),nullable=False)
    attempt_sequence:Mapped[int]=mapped_column(Integer,nullable=False)
    worker_id:Mapped[str]=mapped_column(String(128),nullable=False)
    status:Mapped[str]=mapped_column(String(40),nullable=False)
    provider_message_id:Mapped[str|None]=mapped_column(String(240))
    external_submission_reference:Mapped[str|None]=mapped_column(String(240))
    error_code:Mapped[str|None]=mapped_column(String(120))
    error_message:Mapped[str|None]=mapped_column(Text)
    next_retry_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    payload_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    attempted_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class RegulatoryAcknowledgmentModel(Base):
    __tablename__="regulatory_acknowledgments"
    __table_args__=(UniqueConstraint("tenant_id","destination_id","external_event_id",name="uq_reg_ack_external_event"),Index("ix_reg_ack_transmission","tenant_id","transmission_id","received_at"),)
    acknowledgment_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    transmission_id:Mapped[str]=mapped_column(ForeignKey("regulatory_transmissions.transmission_id",ondelete="RESTRICT"),nullable=False)
    destination_id:Mapped[str]=mapped_column(ForeignKey("regulatory_destinations.destination_id",ondelete="RESTRICT"),nullable=False)
    external_event_id:Mapped[str]=mapped_column(String(180),nullable=False)
    external_submission_reference:Mapped[str]=mapped_column(String(240),nullable=False)
    acknowledgment_status:Mapped[str]=mapped_column(String(40),nullable=False)
    rejection_code:Mapped[str|None]=mapped_column(String(120))
    rejection_reason:Mapped[str|None]=mapped_column(Text)
    receipt_payload:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    signature_verified:Mapped[bool]=mapped_column(Boolean,nullable=False)
    receipt_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    received_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class RegulatoryTransportIncidentModel(Base):
    __tablename__="regulatory_transport_incidents"
    __table_args__=(Index("ix_reg_transport_incident_status","tenant_id","status","created_at"),)
    incident_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    transmission_id:Mapped[str]=mapped_column(ForeignKey("regulatory_transmissions.transmission_id",ondelete="CASCADE"),nullable=False)
    incident_type:Mapped[str]=mapped_column(String(80),nullable=False)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="open")
    details:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    resolved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))


class RegulatoryTransmissionAuditEventModel(Base):
    __tablename__="regulatory_transmission_audit_events"
    __table_args__=(UniqueConstraint("tenant_id","transmission_id","sequence",name="uq_reg_transmission_audit_sequence"),)
    audit_event_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    transmission_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    sequence:Mapped[int]=mapped_column(Integer,nullable=False)
    event_type:Mapped[str]=mapped_column(String(100),nullable=False)
    actor_type:Mapped[str]=mapped_column(String(60),nullable=False)
    actor_id:Mapped[str]=mapped_column(String(128),nullable=False)
    details:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    previous_event_sha256:Mapped[str|None]=mapped_column(String(64))
    event_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

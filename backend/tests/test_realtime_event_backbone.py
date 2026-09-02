from __future__ import annotations
import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.claims import ClaimModel
from app.models.realtime import RealtimeOutboxModel, RealtimeStreamEventModel, EventDeadLetterModel
from app.models.tenancy import OrganizationModel, TenantModel
from app.realtime.broker import MemoryEventProducer
from app.realtime.consumer import BoundedWorkerPool, DurableEventProcessor, RetryableEventError, dead_letter_topic, retry_topic
from app.realtime.events import enqueue_realtime_event
from app.realtime.fhir_subscription import FHIRSubscriptionValidator
from app.realtime.outbox import OutboxRelay


def factory():
    engine=create_engine('sqlite+pysqlite:///:memory:',future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id='tenant-a',slug='tenant-a',display_name='Tenant A',tenant_type='payer',status='active',data_region='local'))
        db.add(OrganizationModel(organization_id='org-a',tenant_id='tenant-a',slug='org-a',display_name='Org A',organization_type='payer',external_identifiers={},is_active=True))
        db.flush()
        db.add(ClaimModel(claim_id='claim-1',tenant_id='tenant-a',external_claim_ref='EXT-1',patient_subject_id='patient-1',provider_organization_id='org-a',payer_organization_id='org-a',claim_type='medical',status='submitted',status_version=1,total_amount=Decimal('10'),currency='USD',service_from=date(2026,8,1)))
        db.commit()
    return f


def envelope(event_id='evt-1'):
    return EventEnvelope(event_id=event_id,event_type='claim.status_changed',tenant_id='tenant-a',claim_id='claim-1',aggregate_type='claim',aggregate_id='claim-1',occurred_at=datetime.now(UTC),producer='test',payload={'status':'verifying'})


def test_envelope_partitions_by_claim_id():
    assert envelope().partition_key() == 'claim-1'


def test_enqueue_creates_outbox_and_realtime_projection_transactionally():
    f=factory()
    with f() as db:
        enqueue_realtime_event(db,envelope=envelope(),topic=EventTopic.CLAIMS.value); db.commit()
    with f() as db:
        assert db.scalar(select(RealtimeOutboxModel)).partition_key == 'claim-1'
        assert db.scalar(select(RealtimeStreamEventModel)).event_type == 'claim.status_changed'


def test_outbox_relay_publishes_and_marks_row():
    f=factory(); producer=MemoryEventProducer()
    with f() as db:
        enqueue_realtime_event(db,envelope=envelope(),topic=EventTopic.CLAIMS.value); db.commit()
    relay=OutboxRelay(f,producer)
    assert asyncio.run(relay.relay_once()) == 1
    assert producer.messages[0][0] == EventTopic.CLAIMS.value
    assert producer.messages[0][1] == 'claim-1'
    with f() as db:
        assert db.scalar(select(RealtimeOutboxModel)).status == 'published'


def test_durable_consumer_is_idempotent_for_same_group_and_event():
    f=factory(); calls=[]
    p=DurableEventProcessor(f,consumer_group='worker-a')
    assert p.process(envelope=envelope(),topic=EventTopic.CLAIMS.value,handler=lambda db,e:calls.append(e.event_id)) == 'completed'
    assert p.process(envelope=envelope(),topic=EventTopic.CLAIMS.value,handler=lambda db,e:calls.append('duplicate-call')) == 'duplicate'
    assert calls == ['evt-1']


def test_retryable_failure_returns_retry_before_attempt_ceiling():
    f=factory(); p=DurableEventProcessor(f,consumer_group='worker-a',max_attempts=3)
    def fail(db,e): raise RetryableEventError('temporary')
    assert p.process(envelope=envelope(),topic='x',handler=fail,attempt=1) == 'retry'


def test_retry_exhaustion_persists_dlq_record():
    f=factory(); p=DurableEventProcessor(f,consumer_group='worker-a',max_attempts=2)
    def fail(db,e): raise RetryableEventError('temporary')
    assert p.process(envelope=envelope(),topic='x',handler=fail,attempt=2) == 'dlq'
    with f() as db:
        row=db.scalar(select(EventDeadLetterModel)); assert row.event_id == 'evt-1'; assert row.replay_envelope['claim_id']=='claim-1'


def test_retry_and_dlq_topic_names_are_version_preserving():
    assert retry_topic('medclaimiq.claim.events.v1',2).endswith('.retry.2')
    assert dead_letter_topic('medclaimiq.claim.events.v1').endswith('.dlq')


def test_backpressure_pool_pauses_and_rejects_saturation():
    pool=BoundedWorkerPool(max_inflight=2,pause_threshold=1)
    assert pool.paused is False
    pool.acquire(); assert pool.paused is True
    pool.acquire()
    with pytest.raises(RuntimeError): pool.acquire()
    pool.release(); pool.release(); assert pool.inflight == 0


def test_fhir_subscription_validator_requires_supported_versioned_resource():
    note=FHIRSubscriptionValidator().validate({'resourceType':'ExplanationOfBenefit','id':'eob-1','meta':{'versionId':'2'},'subscriptionId':'s1'})
    assert note.resource_id=='eob-1' and note.version_id=='2'
    with pytest.raises(ValueError): FHIRSubscriptionValidator().validate({'resourceType':'Binary','id':'x'})


def test_realtime_migration_has_rls_and_immutable_contracts():
    text=Path('alembic/versions/0015_realtime_event_backbone.py').read_text()
    assert 'FORCE ROW LEVEL SECURITY' in text
    assert 'event_consumer_receipts' in text and 'event_dead_letters' in text
    assert 'medclaimiq_reject_immutable_change' in text


def test_compose_contains_redpanda_and_console():
    text=Path('../docker-compose.yml').read_text()
    assert 'redpanda:v26.2.1' in text
    assert 'redpanda-console' in text
    assert '19092:19092' in text


def test_aiokafka_runtime_dependency_is_pinned():
    text=Path('pyproject.toml').read_text(); assert 'aiokafka>=0.14,<1.0' in text

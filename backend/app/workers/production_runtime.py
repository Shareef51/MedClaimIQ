from __future__ import annotations
import argparse, asyncio, time
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import get_session_factory, set_tenant_context
from app.domain.realtime import EventTopic
from app.models.tenancy import TenantModel
from app.realtime.broker import KafkaEventProducer
from app.realtime.consumer import DurableEventProcessor, KafkaConsumerWorker
from app.workers.outbox_relay import run_forever as run_outbox_relay
from app.workers.event_replay import run_forever as run_event_replay
from app.workers.sla_event_scheduler import handle_sla_source_event
from app.workers.sla_timers import SLATimerWorker
from app.core.rag_factory import build_cached_embedder, build_vector_store
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository
from app.repositories.rag import RAGRepository
from app.services.knowledge_governance import KnowledgeGovernanceService
from app.workers.knowledge_reindex import KnowledgeReindexWorker
from app.workers.communication_delivery import run_all_tenants as run_communication_delivery_all_tenants
from app.workers.financial_handoff import run_all_tenants as run_financial_handoff_all_tenants
from app.workers.accounting_reconciliation import run_all_tenants as run_accounting_reconciliation_all_tenants
from app.workers.financial_intelligence import run_all_tenants as run_financial_intelligence_all_tenants
from app.workers.financial_investigation import run_all_tenants as run_financial_investigation_all_tenants
from app.workers.recovery_operations import run_all_tenants as run_recovery_operations_all_tenants
from app.workers.provider_dispute_intelligence import run_all_tenants as run_provider_dispute_intelligence_all_tenants
from app.workers.recovery_settlement import run_all_tenants as run_recovery_settlement_all_tenants
from app.workers.recovery_settlement_intelligence import run_all_tenants as run_recovery_settlement_intelligence_all_tenants
from app.workers.recovery_control_assurance import run_all_tenants as run_recovery_control_assurance_all_tenants
from app.workers.regulatory_submission_transport import run_all_tenants as run_regulatory_submission_transport_all_tenants
from app.workers.regulatory_supervisory_control import run_all_tenants as run_regulatory_supervisory_control_all_tenants
from app.workers.regulatory_examination import run_all_tenants as run_regulatory_examination_all_tenants
from app.workers.regulatory_remediation import run_all_tenants as run_regulatory_remediation_all_tenants
from app.workers.regulatory_portfolio_oversight import run_all_tenants as run_regulatory_portfolio_all_tenants
from app.workers.regulatory_predictive_assurance import run_all_tenants as run_regulatory_predictive_all_tenants
from app.workers.regulatory_continuous_assurance import run_all_tenants as run_regulatory_continuous_all_tenants
from app.workers.regulatory_control_testing import run_all_tenants as run_regulatory_control_testing_all_tenants
from app.workers.regulatory_assurance_deficiencies import run_all_tenants as run_regulatory_assurance_deficiencies_all_tenants
from app.workers.regulatory_deficiency_lifecycle import run_all_tenants as run_regulatory_deficiency_lifecycle_all_tenants
from app.workers.regulatory_closure_governance import run_all_tenants as run_regulatory_closure_governance_all_tenants
from app.workers.regulatory_post_closure_surveillance import run_all_tenants as run_regulatory_post_closure_surveillance_all_tenants
from app.workers.regulatory_reopened_outcome_validation import run_all_tenants as run_regulatory_reopened_outcome_validation_all_tenants
from app.workers.regulatory_lessons_learned import run_all_tenants as run_regulatory_lessons_learned_all_tenants

async def run_sla_scheduler() -> None:
    settings=get_settings()
    processor=DurableEventProcessor(get_session_factory(), consumer_group="medclaimiq-sla-scheduler-v1", max_attempts=settings.event_consumer_max_attempts)
    producer=KafkaEventProducer(settings.kafka_bootstrap_servers, client_id="medclaimiq-sla-scheduler")
    worker=KafkaConsumerWorker(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=[EventTopic.CLAIMS.value, EventTopic.HEALTHCARE.value, EventTopic.MCP.value],
        consumer_group="medclaimiq-sla-scheduler-v1", processor=processor, producer=producer,
        handler=handle_sla_source_event, max_inflight=settings.event_worker_max_inflight,
        pause_threshold=settings.event_worker_pause_threshold,
    )
    await worker.run_forever()

def active_tenant_ids() -> list[str]:
    with get_session_factory()() as db:
        return list(db.scalars(select(TenantModel.tenant_id).where(TenantModel.status == "active")).all())

def run_sla_timer_all_tenants() -> None:
    settings=get_settings(); worker=SLATimerWorker(get_session_factory(), settings=settings)
    while True:
        for tenant_id in active_tenant_ids():
            worker.run_tenant_once(tenant_id)
        time.sleep(max(0.5, settings.sla_timer_poll_seconds))

def run_knowledge_reindex_all_tenants() -> None:
    settings = get_settings()
    embedder = build_cached_embedder(settings)
    vector_store = build_vector_store(settings)
    last_scan: dict[str, float] = {}
    while True:
        now = time.monotonic()
        for tenant_id in active_tenant_ids():
            with get_session_factory()() as db:
                set_tenant_context(db, tenant_id)
                governance = KnowledgeGovernanceRepository(db, tenant_id)
                if now - last_scan.get(tenant_id, 0.0) >= settings.knowledge_stale_scan_seconds:
                    KnowledgeGovernanceService(governance).scan_stale_vectors(
                        actor="system:knowledge-projection-scanner",
                        embedding_model=settings.rag_embedding_model,
                        embedding_dimensions=settings.rag_embedding_dimensions,
                        index_version=settings.rag_index_version,
                    )
                    last_scan[tenant_id] = now
                worker = KnowledgeReindexWorker(
                    governance=governance, rag_repository=RAGRepository(db, tenant_id=tenant_id),
                    embedder=embedder, vector_store=vector_store,
                )
                for job in governance.pending_reindex_jobs(25):
                    worker.process(job)
                db.commit()
        time.sleep(max(0.5, settings.knowledge_reindex_poll_seconds))

def main() -> None:
    parser=argparse.ArgumentParser(description="MedClaimIQ production worker runtime")
    parser.add_argument("worker", choices=["outbox-relay","event-replay","sla-event-scheduler","sla-timer","knowledge-reindex","communication-delivery","financial-handoff","accounting-reconciliation","financial-intelligence","financial-investigation","recovery-operations","provider-dispute-intelligence","recovery-settlement","recovery-settlement-intelligence","recovery-control-assurance","regulatory-submission-transport","regulatory-supervisory-control","regulatory-examination","regulatory-remediation","regulatory-portfolio-oversight","regulatory-predictive-assurance","regulatory-continuous-assurance","regulatory-control-testing","regulatory-assurance-deficiencies","regulatory-deficiency-lifecycle","regulatory-closure-governance"])
    args=parser.parse_args()
    if args.worker == "outbox-relay": asyncio.run(run_outbox_relay())
    elif args.worker == "event-replay": asyncio.run(run_event_replay())
    elif args.worker == "sla-event-scheduler": asyncio.run(run_sla_scheduler())
    elif args.worker == "sla-timer": run_sla_timer_all_tenants()
    elif args.worker == "communication-delivery": run_communication_delivery_all_tenants(active_tenant_ids)
    elif args.worker == "financial-handoff": run_financial_handoff_all_tenants(active_tenant_ids)
    elif args.worker == "accounting-reconciliation": run_accounting_reconciliation_all_tenants(active_tenant_ids)
    elif args.worker == "financial-intelligence": run_financial_intelligence_all_tenants(active_tenant_ids)
    elif args.worker == "financial-investigation": run_financial_investigation_all_tenants(active_tenant_ids)
    elif args.worker == "recovery-operations": run_recovery_operations_all_tenants(active_tenant_ids)
    elif args.worker == "provider-dispute-intelligence": run_provider_dispute_intelligence_all_tenants(active_tenant_ids)
    elif args.worker == "recovery-settlement": run_recovery_settlement_all_tenants(active_tenant_ids)
    elif args.worker == "recovery-settlement-intelligence": run_recovery_settlement_intelligence_all_tenants(active_tenant_ids)
    elif args.worker == "recovery-control-assurance": run_recovery_control_assurance_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-submission-transport": run_regulatory_submission_transport_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-supervisory-control": run_regulatory_supervisory_control_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-examination": run_regulatory_examination_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-remediation": run_regulatory_remediation_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-portfolio-oversight": run_regulatory_portfolio_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-predictive-assurance": run_regulatory_predictive_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-continuous-assurance": run_regulatory_continuous_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-control-testing": run_regulatory_control_testing_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-assurance-deficiencies": run_regulatory_assurance_deficiencies_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-deficiency-lifecycle": run_regulatory_deficiency_lifecycle_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-closure-governance": run_regulatory_closure_governance_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-post-closure-surveillance": run_regulatory_post_closure_surveillance_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-reopened-outcome-validation": run_regulatory_reopened_outcome_validation_all_tenants(active_tenant_ids)
    elif args.worker == "regulatory-lessons-learned": run_regulatory_lessons_learned_all_tenants(active_tenant_ids)
    else: run_knowledge_reindex_all_tenants()

if __name__ == "__main__": main()

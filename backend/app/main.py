from functools import lru_cache
from fastapi import FastAPI

from app.api.v1.access_model import router as access_model_router
from app.api.v1.authentication import router as authentication_router
from app.api.v1.claim_domain_model import router as claim_domain_model_router
from app.api.v1.health import router as health_router
from app.api.v1.document_intelligence import router as document_intelligence_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.fhir import router as fhir_router, mock_router as mock_fhir_router
from app.api.v1.evidence_graph import router as evidence_graph_router
from app.api.v1.rag import router as rag_router
from app.api.v1.cross_source_rag import router as cross_source_rag_router
from app.api.v1.grounding import router as grounding_router
from app.api.v1.orchestration import router as orchestration_router
from app.api.v1.specialist_agents import router as specialist_agents_router
from app.api.v1.mcp import router as mcp_router, protocol_router as mcp_protocol_router
from app.api.v1.tenancy_model import router as tenancy_model_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.fhir_subscription import router as fhir_subscription_router
from app.api.v1.sla import router as sla_router
from app.api.v1.review_workbench import router as review_workbench_router
from app.api.v1.portal import router as portal_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.llmops import router as llmops_router
from app.api.v1.security_governance import router as security_governance_router
from app.api.v1.cloud_infrastructure import router as cloud_infrastructure_router
from app.api.v1.release_engineering import router as release_engineering_router
from app.api.v1.performance_resilience import router as performance_resilience_router
from app.api.v1.ai_change_management import router as ai_change_management_router
from app.api.v1.knowledge_governance import router as knowledge_governance_router
from app.api.v1.advanced_rag import router as advanced_rag_router
from app.api.v1.multimodal_rag import router as multimodal_rag_router
from app.api.v1.multimodal_agent_orchestration import router as multimodal_agent_orchestration_router
from app.api.v1.multimodal_review import router as multimodal_review_router
from app.api.v1.governed_closure import router as governed_closure_router
from app.api.v1.post_decision import router as post_decision_router
from app.api.v1.communication_delivery import router as communication_delivery_router
from app.api.v1.appeal_reconsideration import router as appeal_reconsideration_router
from app.api.v1.appeal_resolution import router as appeal_resolution_router
from app.api.v1.financial_handoff import router as financial_handoff_router
from app.api.v1.accounting_ledger import router as accounting_ledger_router
from app.api.v1.financial_intelligence import router as financial_intelligence_router
from app.api.v1.financial_investigation import router as financial_investigation_router
from app.api.v1.recovery_operations import router as recovery_operations_router
from app.api.v1.provider_dispute_intelligence import router as provider_dispute_intelligence_router
from app.api.v1.provider_dispute_resolution import router as provider_dispute_resolution_router
from app.api.v1.recovery_settlement import router as recovery_settlement_router
from app.api.v1.recovery_settlement_intelligence import router as recovery_settlement_intelligence_router
from app.api.v1.recovery_control_assurance import router as recovery_control_assurance_router
from app.api.v1.regulatory_submission_transport import router as regulatory_submission_transport_router
from app.api.v1.regulatory_supervisory_control import router as regulatory_supervisory_control_router
from app.api.v1.regulatory_examination import router as regulatory_examination_router
from app.api.v1.regulatory_remediation import router as regulatory_remediation_router
from app.api.v1.regulatory_portfolio_oversight import router as regulatory_portfolio_oversight_router
from app.api.v1.regulatory_predictive_assurance import router as regulatory_predictive_assurance_router
from app.api.v1.regulatory_continuous_assurance import router as regulatory_continuous_assurance_router
from app.api.v1.regulatory_control_testing import router as regulatory_control_testing_router
from app.api.v1.regulatory_assurance_deficiencies import router as regulatory_assurance_deficiencies_router
from app.api.v1.regulatory_deficiency_lifecycle import router as regulatory_deficiency_lifecycle_router
from app.api.v1.regulatory_closure_governance import router as regulatory_closure_governance_router
from app.api.v1.regulatory_post_closure_surveillance import router as regulatory_post_closure_surveillance_router
from app.api.v1.regulatory_reopened_outcome_validation import router as regulatory_reopened_outcome_validation_router
from app.api.v1.regulatory_lessons_learned import router as regulatory_lessons_learned_router
from app.api.v1.regulatory_knowledge_governance import router as regulatory_knowledge_governance_router
from app.api.v1.regulatory_examination_readiness import router as regulatory_examination_readiness_router
from app.api.v1.regulatory_examination_response import router as regulatory_examination_response_router
from app.api.v1.regulatory_examination_interaction import router as regulatory_examination_interaction_router
from app.api.v1.regulatory_examination_commitment_lifecycle import router as regulatory_examination_commitment_lifecycle_router
from app.api.v1.regulatory_examination_commitment_effectiveness import router as regulatory_examination_commitment_effectiveness_router
from app.api.v1.regulatory_examination_post_commitment_surveillance import router as regulatory_examination_post_commitment_surveillance_router
from app.api.v1.regulatory_examination_reopened_commitment_reclosure import router as regulatory_examination_reopened_commitment_reclosure_router
from app.api.v1.regulatory_examination_reclosure_sustainability import router as regulatory_examination_reclosure_sustainability_router
from app.api.v1.regulatory_examination_systemic_recurrence_portfolio import router as regulatory_examination_systemic_recurrence_portfolio_router
from app.api.v1.regulatory_examination_enterprise_intervention_execution import router as regulatory_examination_enterprise_intervention_execution_router
from app.api.v1.regulatory_examination_enterprise_intervention_sustainability import router as regulatory_examination_enterprise_intervention_sustainability_router
from app.api.v1.regulatory_examination_post_intervention_surveillance import router as regulatory_examination_post_intervention_surveillance_router
from app.api.v1.regulatory_examination_reopened_enterprise_intervention import router as regulatory_examination_reopened_enterprise_intervention_router
from app.api.v1.regulatory_examination_reclosed_intervention_sustainability import router as regulatory_examination_reclosed_intervention_sustainability_router
from app.api.v1.regulatory_examination_systemic_failure_investigation import router as regulatory_examination_systemic_failure_investigation_router
from app.api.v1.regulatory_examination_renewed_enterprise_remediation_execution import router as regulatory_examination_renewed_enterprise_remediation_execution_router
from app.api.v1.regulatory_examination_renewed_remediation_outcome_validation import router as regulatory_examination_renewed_remediation_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_recovery_surveillance import router as regulatory_examination_reclosed_recovery_surveillance_router
from app.api.v1.regulatory_examination_reopened_recovery_investigation import router as regulatory_examination_reopened_recovery_investigation_router
from app.api.v1.regulatory_examination_renewed_recovery_execution import router as regulatory_examination_renewed_recovery_execution_router
from app.api.v1.regulatory_examination_renewed_recovery_outcome_validation import router as regulatory_examination_renewed_recovery_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_recovery_sustainability import router as regulatory_examination_reclosed_recovery_sustainability_router
from app.api.v1.regulatory_examination_repeated_recovery_failure_investigation import router as regulatory_examination_repeated_recovery_failure_investigation_router
from app.api.v1.regulatory_examination_reauthorized_recovery_execution import router as regulatory_examination_reauthorized_recovery_execution_router
from app.api.v1.regulatory_examination_reauthorized_recovery_outcome_validation import router as regulatory_examination_reauthorized_recovery_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_reauthorized_recovery_surveillance import router as regulatory_examination_reclosed_reauthorized_recovery_surveillance_router
from app.api.v1.regulatory_examination_reopened_reauthorized_recovery_investigation import router as regulatory_examination_reopened_reauthorized_recovery_investigation_router
from app.api.v1.regulatory_examination_supervisory_reauthorized_recovery_execution import router as regulatory_examination_supervisory_reauthorized_recovery_execution_router
from app.api.v1.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import router as regulatory_examination_supervisory_reauthorized_recovery_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_supervisory_recovery_surveillance import router as regulatory_examination_reclosed_supervisory_recovery_surveillance_router
from app.api.v1.regulatory_examination_reopened_supervisory_recovery_investigation import router as regulatory_examination_reopened_supervisory_recovery_investigation_router
from app.api.v1.regulatory_examination_enterprise_reauthorized_recovery_execution import router as regulatory_examination_enterprise_reauthorized_recovery_execution_router
from app.api.v1.regulatory_examination_enterprise_recovery_outcome_validation import router as regulatory_examination_enterprise_recovery_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_enterprise_recovery_surveillance import router as regulatory_examination_reclosed_enterprise_recovery_surveillance_router
from app.api.v1.regulatory_examination_reopened_enterprise_recovery_investigation import router as regulatory_examination_reopened_enterprise_recovery_investigation_router
from app.api.v1.regulatory_examination_reauthorized_enterprise_remediation_execution import router as regulatory_examination_reauthorized_enterprise_remediation_execution_router
from app.api.v1.regulatory_examination_reauthorized_enterprise_remediation_outcome_validation import router as regulatory_examination_reauthorized_enterprise_remediation_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance import router as regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_router
from app.api.v1.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import router as regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_router
from app.api.v1.regulatory_examination_reauthorized_enterprise_remediation_reexecution import router as regulatory_examination_reauthorized_enterprise_remediation_reexecution_router
from app.api.v1.regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation import router as regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_router
from app.api.v1.regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance import router as regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_router
from app.api.v1.production_end_to_end_system_integration import router as production_end_to_end_system_integration_router
from app.api.v1.production_security_privacy_compliance_red_team import router as production_security_privacy_compliance_red_team_router
from app.api.v1.production_performance_resilience_disaster_recovery_operational_readiness import router as production_performance_resilience_disaster_recovery_operational_readiness_router
from app.core.auth_factory import build_authentication_service
from app.core.config import get_settings
from app.core.ingestion_factory import build_object_storage
from app.core.rag_factory import build_cached_embedder, build_vector_store
from app.core.agent_factory import build_production_specialist_registry
from app.core.multimodal_agent_factory import build_multimodal_agent_investigation_service
from app.orchestration.runner import LangGraphWorkflowRunner
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware, RedisSlidingWindowLimiter
from app.observability.middleware import ObservabilityMiddleware
from app.observability.tracing import configure_observability
from app.observability.logging import configure_logging
from app.db.session import get_session_factory

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Production-style API foundation for MedClaimIQ medical-claims "
        "verification and evidence intelligence."
    ),
)

app.state.observability = configure_observability(app, settings)
app.state.authentication_service = build_authentication_service(settings)
app.state.session_factory_provider = get_session_factory
app.state.object_storage_provider = lambda: build_object_storage(settings)
if settings.security_rate_limit_backend.lower() == "redis":
    app.state.rate_limiter = RedisSlidingWindowLimiter(settings.redis_url)

@lru_cache(maxsize=1)
def _rag_embedder():
    return build_cached_embedder(settings)

@lru_cache(maxsize=1)
def _rag_vector_store():
    return build_vector_store(settings)

app.state.rag_embedder_provider = _rag_embedder
app.state.rag_vector_store_provider = _rag_vector_store

@lru_cache(maxsize=1)
def _agent_workflow_runner():
    session_factory = get_session_factory()
    return LangGraphWorkflowRunner(
        session_factory=session_factory,
        settings=settings,
        registry_factory=lambda db, tenant_id: build_production_specialist_registry(db, tenant_id, settings),
        multimodal_investigation_factory=(lambda db, tenant_id: build_multimodal_agent_investigation_service(session=db, tenant_id=tenant_id, settings=settings, embedder=_rag_embedder(), vector_store=_rag_vector_store())) if settings.multimodal_agent_orchestration_enabled else None,
    )

app.state.agent_workflow_runner_provider = _agent_workflow_runner

app.add_middleware(
    AuthenticationMiddleware,
    public_paths={
        f"{settings.api_v1_prefix}/health",
        f"{settings.api_v1_prefix}/access-model",
        f"{settings.api_v1_prefix}/tenancy-model",
        f"{settings.api_v1_prefix}/claim-domain-model",
        f"{settings.api_v1_prefix}/ingestion-model",
        f"{settings.api_v1_prefix}/document-intelligence-model",
        f"{settings.api_v1_prefix}/healthcare-fhir-model",
        f"{settings.api_v1_prefix}/evidence-graph-model",
        f"{settings.api_v1_prefix}/rag-model",
        f"{settings.api_v1_prefix}/cross-source-rag-model",
        f"{settings.api_v1_prefix}/rag-grounding-model",
        f"{settings.api_v1_prefix}/agent-orchestration-model",
        f"{settings.api_v1_prefix}/specialist-agent-model",
        f"{settings.api_v1_prefix}/mcp-model",
        f"{settings.api_v1_prefix}/realtime-model",
        f"{settings.api_v1_prefix}/sla-model",
        f"{settings.api_v1_prefix}/review-model",
        f"{settings.api_v1_prefix}/financial-intelligence-model",
        f"{settings.api_v1_prefix}/financial-investigation-model",
        f"{settings.api_v1_prefix}/recovery-operations-model",
        f"{settings.api_v1_prefix}/portal-model",
        f"{settings.api_v1_prefix}/evaluation-model",
        f"{settings.api_v1_prefix}/llmops-model",
        f"{settings.api_v1_prefix}/security-model",
        f"{settings.api_v1_prefix}/cloud-infrastructure-model",
        f"{settings.api_v1_prefix}/release-engineering-model",
        f"{settings.api_v1_prefix}/performance-resilience-model",
        f"{settings.api_v1_prefix}/ai-change-management-model",
        f"{settings.api_v1_prefix}/knowledge-governance-model",
        f"{settings.api_v1_prefix}/advanced-rag-model",
        f"{settings.api_v1_prefix}/multimodal-rag-model",
        f"{settings.api_v1_prefix}/multimodal-agent-orchestration-model",
        f"{settings.api_v1_prefix}/multimodal-review-model",
        f"{settings.api_v1_prefix}/governed-closure-model",
        f"{settings.api_v1_prefix}/communication-delivery-model",
        f"{settings.api_v1_prefix}/appeal-reconsideration-model",
        f"{settings.api_v1_prefix}/appeal-resolution-model",
        f"{settings.api_v1_prefix}/financial-handoff-model",
        f"{settings.api_v1_prefix}/communications/webhooks/*",
        f"{settings.api_v1_prefix}/financial/webhooks/*",
        f"{settings.api_v1_prefix}/regulatory/webhooks/*",
        "/openapi.json",
        f"{settings.api_v1_prefix}/fhir/subscriptions/events",
    },
    tenant_header=settings.auth_tenant_header,
)


app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.security_rate_limit_requests_per_minute,
    mutation_requests_per_minute=settings.security_rate_limit_mutations_per_minute,
)
app.add_middleware(SecurityHeadersMiddleware, production=settings.environment.lower() in {"prod", "production"})
app.add_middleware(ObservabilityMiddleware)

from app.api.v1.production_go_live_governance_final_release_certification import router as production_go_live_governance_final_release_certification_router

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(access_model_router, prefix=settings.api_v1_prefix)
app.include_router(tenancy_model_router, prefix=settings.api_v1_prefix)
app.include_router(claim_domain_model_router, prefix=settings.api_v1_prefix)
app.include_router(ingestion_router, prefix=settings.api_v1_prefix)
app.include_router(document_intelligence_router, prefix=settings.api_v1_prefix)
app.include_router(fhir_router, prefix=settings.api_v1_prefix)
app.include_router(evidence_graph_router, prefix=settings.api_v1_prefix)
app.include_router(rag_router, prefix=settings.api_v1_prefix)
app.include_router(cross_source_rag_router, prefix=settings.api_v1_prefix)
app.include_router(grounding_router, prefix=settings.api_v1_prefix)
app.include_router(orchestration_router, prefix=settings.api_v1_prefix)
app.include_router(specialist_agents_router, prefix=settings.api_v1_prefix)
app.include_router(mcp_router, prefix=settings.api_v1_prefix)
app.include_router(realtime_router, prefix=settings.api_v1_prefix)
app.include_router(fhir_subscription_router, prefix=settings.api_v1_prefix)
app.include_router(sla_router, prefix=settings.api_v1_prefix)
app.include_router(review_workbench_router, prefix=settings.api_v1_prefix)
app.include_router(portal_router, prefix=settings.api_v1_prefix)
app.include_router(evaluation_router, prefix=settings.api_v1_prefix)
app.include_router(llmops_router, prefix=settings.api_v1_prefix)
app.include_router(security_governance_router, prefix=settings.api_v1_prefix)
app.include_router(cloud_infrastructure_router, prefix=settings.api_v1_prefix)
app.include_router(release_engineering_router, prefix=settings.api_v1_prefix)
app.include_router(performance_resilience_router, prefix=settings.api_v1_prefix)
app.include_router(ai_change_management_router, prefix=settings.api_v1_prefix)
app.include_router(knowledge_governance_router, prefix=settings.api_v1_prefix)
app.include_router(advanced_rag_router, prefix=settings.api_v1_prefix)
app.include_router(multimodal_rag_router, prefix=settings.api_v1_prefix)
app.include_router(multimodal_agent_orchestration_router, prefix=settings.api_v1_prefix)
app.include_router(multimodal_review_router, prefix=settings.api_v1_prefix)
app.include_router(governed_closure_router, prefix=settings.api_v1_prefix)
app.include_router(post_decision_router, prefix=settings.api_v1_prefix)
app.include_router(communication_delivery_router, prefix=settings.api_v1_prefix)
app.include_router(appeal_reconsideration_router, prefix=settings.api_v1_prefix)
app.include_router(appeal_resolution_router, prefix=settings.api_v1_prefix)
app.include_router(financial_handoff_router, prefix=settings.api_v1_prefix)
app.include_router(accounting_ledger_router, prefix=settings.api_v1_prefix)
app.include_router(financial_intelligence_router, prefix=settings.api_v1_prefix)
app.include_router(financial_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(recovery_operations_router, prefix=settings.api_v1_prefix)
app.include_router(provider_dispute_intelligence_router, prefix=settings.api_v1_prefix)
app.include_router(provider_dispute_resolution_router, prefix=settings.api_v1_prefix)
app.include_router(recovery_settlement_router, prefix=settings.api_v1_prefix)
app.include_router(recovery_settlement_intelligence_router, prefix=settings.api_v1_prefix)
app.include_router(recovery_control_assurance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_submission_transport_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_supervisory_control_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_remediation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_portfolio_oversight_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_predictive_assurance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_continuous_assurance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_control_testing_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_assurance_deficiencies_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_deficiency_lifecycle_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_closure_governance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_post_closure_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_reopened_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_lessons_learned_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_knowledge_governance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_readiness_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_response_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_interaction_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_commitment_lifecycle_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_commitment_effectiveness_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_post_commitment_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_commitment_reclosure_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosure_sustainability_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_systemic_recurrence_portfolio_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_enterprise_intervention_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_enterprise_intervention_sustainability_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_post_intervention_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_enterprise_intervention_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_intervention_sustainability_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_systemic_failure_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_renewed_enterprise_remediation_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_renewed_remediation_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_recovery_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_recovery_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_renewed_recovery_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_renewed_recovery_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_recovery_sustainability_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_repeated_recovery_failure_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_recovery_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_recovery_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_reauthorized_recovery_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_reauthorized_recovery_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_supervisory_reauthorized_recovery_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_supervisory_reauthorized_recovery_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_supervisory_recovery_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_supervisory_recovery_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_enterprise_reauthorized_recovery_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_enterprise_recovery_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_enterprise_recovery_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_enterprise_recovery_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_enterprise_remediation_execution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_enterprise_remediation_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_enterprise_remediation_reexecution_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_router, prefix=settings.api_v1_prefix)
app.include_router(regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_router, prefix=settings.api_v1_prefix)
app.include_router(production_end_to_end_system_integration_router, prefix=settings.api_v1_prefix)
app.include_router(production_security_privacy_compliance_red_team_router, prefix=settings.api_v1_prefix)
app.include_router(production_performance_resilience_disaster_recovery_operational_readiness_router, prefix=settings.api_v1_prefix)
app.include_router(mcp_protocol_router)
app.include_router(mock_fhir_router)
app.include_router(authentication_router, prefix=settings.api_v1_prefix)

app.include_router(production_go_live_governance_final_release_certification_router, prefix=settings.api_v1_prefix)

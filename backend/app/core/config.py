from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "MedClaimIQ API"
    service_name: str = "medclaimiq-api"
    environment: str = Field(default="local", validation_alias="APP_ENV")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # LLMOps / OpenTelemetry / observability
    otel_trace_sample_ratio: float = 0.10
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str = ""
    phoenix_enabled: bool = False
    phoenix_collector_endpoint: str = "http://localhost:6006"
    phoenix_project: str = "medclaimiq"
    phoenix_api_key: SecretStr | None = None
    langsmith_enabled: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_otel_endpoint: str = "https://api.smith.langchain.com/otel/v1/traces"
    langsmith_project: str = "medclaimiq"
    llmops_model_pricing_json: str = "{}"

    # Security / privacy / DevSecOps runtime controls
    security_rate_limit_backend: str = "memory"
    security_rate_limit_requests_per_minute: int = 120
    security_rate_limit_mutations_per_minute: int = 40
    security_audit_export_hmac_secret: SecretStr = SecretStr("local-only-change-this-audit-export-signing-secret-123456")
    security_kms_key_id: str = ""
    security_secret_provider: str = "environment"
    security_retention_default_days: int = 2555

    # Release 37 post-decision communication delivery and compliance
    communication_destination_encryption_secret: SecretStr = SecretStr(
        "local-only-change-this-communication-destination-secret-123456"
    )
    communication_destination_key_version: str = "v1"
    communication_provider_webhook_secret: SecretStr = SecretStr(
        "local-only-change-this-provider-webhook-secret-123456789"
    )
    communication_worker_token: SecretStr = SecretStr(
        "local-only-change-this-communication-worker-token-123456"
    )
    communication_worker_lease_seconds: int = 60
    communication_worker_poll_seconds: float = 1.0
    communication_max_delivery_attempts: int = 5
    communication_retry_base_seconds: int = 30
    communication_retry_max_seconds: int = 3600
    communication_retention_days: int = 2555
    communication_delivery_slo_percent: float = 99.0

    database_url: str = "postgresql+psycopg://medclaimiq:medclaimiq@localhost:5432/medclaimiq"
    redis_url: str = "redis://localhost:6379/0"

    # Real-time event fabric / Kafka API (Redpanda locally)
    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_client_id: str = "medclaimiq"
    event_outbox_batch_size: int = 100
    event_outbox_poll_seconds: float = 0.5
    event_outbox_max_attempts: int = 10
    event_retry_base_seconds: int = 5
    event_consumer_max_attempts: int = 3
    event_worker_max_inflight: int = 32
    event_worker_pause_threshold: int = 24

    # SLA / deadline engine
    sla_worker_batch_size: int = 100
    sla_worker_recovery_batch_size: int = 500
    sla_worker_max_attempts: int = 5
    sla_worker_retry_base_seconds: int = 15
    sla_worker_retry_max_seconds: int = 900
    sla_timer_poll_seconds: float = 1.0

    # RAG / embeddings / vector projection
    rag_embedding_model: str = "text-embedding-3-large"
    rag_embedding_dimensions: int = 1536
    rag_embedding_batch_size: int = 64
    rag_embedding_cache_ttl_seconds: int = 7 * 24 * 3600
    rag_parent_chunk_tokens: int = 1200
    rag_child_chunk_tokens: int = 350
    rag_chunk_overlap_tokens: int = 60
    rag_index_version: str = "rag-v2-hybrid"
    rag_rrf_k: int = 60
    rag_candidate_multiplier: int = 4
    rag_minimum_retrieval_confidence: float = 0.35
    rag_default_minimum_authority_rank: int = 0
    cross_source_graph_max_depth: int = 3
    cross_source_graph_max_edges: int = 100
    cross_source_evidence_pack_limit: int = 20
    rag_prompt_injection_suspicious_threshold: float = 0.35
    rag_prompt_injection_block_threshold: float = 0.65
    rag_guardrail_minimum_item_confidence: float = 0.55
    rag_guardrail_minimum_authority_rank: int = 60
    rag_guardrail_minimum_quality_score: float = 0.50
    rag_guardrail_minimum_pack_coverage: float = 0.50
    rag_guardrail_max_repairs: int = 2
    # Advanced Agentic RAG
    rag_advanced_model_assisted_rewriting_enabled: bool = False
    rag_advanced_query_model: str = "gpt-5.6-terra"
    rag_advanced_max_rewrites: int = 5
    rag_advanced_max_rounds: int = 2
    rag_advanced_gap_confidence: float = 0.55
    rag_advanced_min_citation_coverage: float = 0.80
    # Read-only financial intelligence copilot
    financial_intelligence_copilot_model_enabled: bool = False
    financial_intelligence_copilot_model: str = "gpt-5.6-terra"
    regulatory_examination_response_model_enabled: bool = False
    regulatory_examination_response_model: str = "gpt-5.6-terra"
    regulatory_examination_interaction_model_enabled: bool = False
    regulatory_examination_interaction_model: str = "gpt-5.6-terra"
    regulatory_examination_commitment_lifecycle_model_enabled: bool = False
    regulatory_examination_commitment_lifecycle_model: str = "gpt-5.6-terra"
    regulatory_examination_commitment_effectiveness_model_enabled: bool = False
    regulatory_examination_commitment_effectiveness_model: str = "gpt-5.6-terra"
    regulatory_examination_post_commitment_surveillance_model_enabled: bool = False
    regulatory_examination_post_commitment_surveillance_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_commitment_reclosure_model_enabled: bool = False
    regulatory_examination_reopened_commitment_reclosure_model: str = "gpt-5.6-terra"
    regulatory_examination_reclosure_sustainability_model_enabled: bool = False
    regulatory_examination_reclosure_sustainability_model: str = "gpt-5.6-terra"
    regulatory_examination_systemic_recurrence_portfolio_model_enabled: bool = False
    regulatory_examination_systemic_recurrence_portfolio_model: str = "gpt-5.6-terra"
    regulatory_examination_enterprise_intervention_execution_model_enabled: bool = False
    regulatory_examination_enterprise_intervention_execution_model: str = "gpt-5.6-terra"
    regulatory_examination_enterprise_intervention_sustainability_model_enabled: bool = False
    regulatory_examination_enterprise_intervention_sustainability_model: str = "gpt-5.6-terra"
    regulatory_examination_post_intervention_surveillance_model_enabled: bool = False
    regulatory_examination_post_intervention_surveillance_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_enterprise_intervention_model_enabled: bool = False
    regulatory_examination_reopened_enterprise_intervention_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_recovery_investigation_model_enabled: bool = False
    regulatory_examination_reopened_recovery_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_renewed_recovery_execution_model_enabled: bool = False
    regulatory_examination_renewed_recovery_execution_model: str = "gpt-5.6-terra"
    regulatory_examination_renewed_recovery_outcome_validation_model_enabled: bool = False
    regulatory_examination_renewed_recovery_outcome_validation_model: str = "gpt-5.6-terra"
    regulatory_examination_reclosed_recovery_sustainability_model_enabled: bool = False
    regulatory_examination_reclosed_recovery_sustainability_model: str = "gpt-5.6-terra"
    regulatory_examination_repeated_recovery_failure_investigation_model_enabled: bool = False
    regulatory_examination_repeated_recovery_failure_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_reauthorized_recovery_execution_model_enabled: bool = False
    regulatory_examination_reauthorized_recovery_execution_model: str = "gpt-5.6-terra"
    regulatory_examination_reauthorized_recovery_outcome_validation_model_enabled: bool = False
    regulatory_examination_reauthorized_recovery_outcome_validation_model: str = "gpt-5.6-terra"
    regulatory_examination_reclosed_reauthorized_recovery_surveillance_model_enabled: bool = False
    regulatory_examination_reclosed_reauthorized_recovery_surveillance_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_reauthorized_recovery_investigation_model_enabled: bool = False
    regulatory_examination_reopened_reauthorized_recovery_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_supervisory_reauthorized_recovery_execution_model_enabled: bool = False
    regulatory_examination_supervisory_reauthorized_recovery_execution_model: str = "gpt-5.6-terra"
    regulatory_examination_supervisory_reauthorized_recovery_outcome_validation_model_enabled: bool = False
    regulatory_examination_reclosed_supervisory_recovery_surveillance_model_enabled: bool = False
    regulatory_examination_supervisory_reauthorized_recovery_outcome_validation_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_supervisory_recovery_investigation_model_enabled: bool = False
    regulatory_examination_reopened_supervisory_recovery_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_enterprise_reauthorized_recovery_execution_model_enabled: bool = False
    regulatory_examination_enterprise_reauthorized_recovery_execution_model: str = "gpt-5.6-terra"
    regulatory_examination_enterprise_recovery_outcome_validation_model_enabled: bool = False
    regulatory_examination_enterprise_recovery_outcome_validation_model: str = "gpt-5.6-terra"
    regulatory_examination_reclosed_enterprise_recovery_surveillance_model_enabled: bool = False
    regulatory_examination_reclosed_enterprise_recovery_surveillance_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_enterprise_recovery_investigation_model_enabled: bool = False
    regulatory_examination_reopened_enterprise_recovery_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_reauthorized_enterprise_remediation_execution_model_enabled: bool = False
    regulatory_examination_reauthorized_enterprise_remediation_outcome_validation_model_enabled: bool = False
    regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_model_enabled: bool = False
    regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance_model: str = "gpt-5.6-terra"
    regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_model_enabled: bool = False
    regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation_model: str = "gpt-5.6-terra"
    regulatory_examination_reauthorized_enterprise_remediation_reexecution_model_enabled: bool = False
    regulatory_examination_reauthorized_enterprise_remediation_reexecution_model: str = "gpt-5.6-terra"
    regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_model_enabled: bool = False
    regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation_model: str = "gpt-5.6-terra"
    regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_model_enabled: bool = False
    regulatory_examination_reclosed_reauthorized_enterprise_remediation_reexecution_surveillance_model: str = "gpt-5.6-terra"
    release_candidate_hardening_enabled: bool = True
    release_candidate_minimum_quality_score: float = 0.90
    release_candidate_required_golden_journeys: int = 3
    release_security_certification_enabled: bool = True
    release_security_require_release107_candidate: bool = True
    release_security_critical_findings_allowed: int = 0
    release_security_high_findings_allowed: int = 0
    release_security_secret_findings_allowed: int = 0
    release_security_max_waiver_days: int = 30
    release_security_require_sbom: bool = True
    release_security_require_signed_images: bool = True
    release_security_require_iac_scan: bool = True
    operational_go_live_readiness_enabled: bool = True
    operational_go_live_require_release107_candidate: bool = True
    operational_go_live_require_release108_security_certification: bool = True
    operational_go_live_minimum_soak_minutes: int = 60
    operational_go_live_minimum_capacity_headroom: float = 0.30
    operational_go_live_minimum_capacity_forecast_days: int = 30
    operational_go_live_require_backup_restore: bool = True
    operational_go_live_require_failover_failback: bool = True
    operational_go_live_require_rpo_rto: bool = True
    final_production_go_live_enabled: bool = True
    final_production_go_live_require_release107_candidate: bool = True
    final_production_go_live_require_release108_security_certification: bool = True
    final_production_go_live_require_release109_operational_certification: bool = True
    final_production_go_live_migration_head: str = "0105_final_production_go_live"
    final_production_go_live_require_canary: bool = True
    final_production_go_live_require_rollback: bool = True
    final_production_go_live_hypercare_hours: int = 72
    regulatory_examination_reauthorized_enterprise_remediation_execution_model: str = "gpt-5.6-terra"
    regulatory_remediation_recommendation_model_enabled: bool = False
    regulatory_remediation_recommendation_model: str = "gpt-5.6-terra"
    # Multimodal RAG
    rag_multimodal_max_candidates: int = 60
    rag_multimodal_minimum_confidence: float = 0.50
    rag_multimodal_minimum_citation_coverage: float = 0.80
    multimodal_agent_orchestration_enabled: bool = True
    multimodal_agent_max_pack_items: int = 18

    # Durable agent orchestration
    agent_workflow_max_parallel_agents: int = 8
    agent_workflow_default_max_attempts: int = 3
    agent_workflow_retry_base_seconds: int = 5
    agent_workflow_retry_max_seconds: int = 60
    agent_workflow_default_timeout_seconds: int = 90
    langgraph_strict_msgpack: bool = True
    agent_model_name: str = "gpt-5.6-terra"
    agent_fallback_model: str = "gpt-5.6-luna"
    agent_prompt_version: str = "1.0.0"
    agent_model_timeout_seconds: int = 90
    ai_config_registry_enabled: bool = True
    ai_config_registry_required: bool = False
    ai_config_bundle_key: str = "agents.default"

    # MCP / controlled tool execution
    mcp_protocol_version: str = "2026-07-28"
    mcp_tool_timeout_seconds: float = 10.0
    mcp_read_max_attempts: int = 2
    mcp_circuit_failure_threshold: int = 3
    mcp_circuit_recovery_seconds: int = 30
    mcp_approval_ttl_minutes: int = 30
    rag_index_max_attempts: int = 3
    knowledge_reindex_poll_seconds: float = 2.0
    knowledge_stale_scan_seconds: int = 900
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection_prefix: str = "medclaimiq"
    qdrant_timeout_seconds: float = 10.0
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str | None = None
    s3_bucket: str = "medclaimiq"
    s3_access_key: str = "medclaimiq"
    s3_secret_key: str = "change-me-local-only"
    s3_use_default_credential_chain: bool = False
    s3_region: str = "us-east-1"
    s3_server_side_encryption: str = ""
    s3_sse_kms_key_id: str = ""
    upload_presign_ttl_seconds: int = 900
    upload_max_file_bytes: int = 500 * 1024 * 1024
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    clamav_timeout_seconds: float = 30.0
    malware_scan_required: bool = True

    document_pipeline_version: str = "document-intelligence-v1"
    document_parser_timeout_seconds: int = 120
    document_extraction_max_attempts: int = 3
    document_extraction_retry_base_seconds: int = 15
    document_extraction_retry_max_seconds: int = 300

    fhir_default_base_url: str = "http://localhost:8000/mock-fhir"
    fhir_expected_version: str = "4.0.1"
    fhir_http_timeout_seconds: float = 10.0
    fhir_max_attempts: int = 3
    fhir_rate_limit_per_second: float = 10.0
    fhir_subscription_webhook_secret: SecretStr = SecretStr("local-only-change-this-fhir-webhook-secret")
    smart_token_url: str = "https://identity.example.invalid/oauth2/token"
    smart_client_id: str = "medclaimiq-fhir-gateway"
    smart_key_id: str = "configure-in-secret-manager"
    smart_scopes: str = "system/*.read"

    oidc_issuer_url: str = "https://identity.example.invalid/medclaimiq"
    oidc_audience: str = "medclaimiq-api"
    oidc_allowed_algorithms: str = "RS256"
    oidc_clock_skew_seconds: int = 60
    oidc_jwks_cache_ttl_seconds: int = 300
    oidc_http_timeout_seconds: float = 5.0
    oidc_allow_insecure_http: bool = False
    oidc_required_scopes: str = "medclaimiq.api"
    auth_tenant_header: str = "X-Tenant-Id"
    auth_session_required: bool = True
    auth_session_max_age_seconds: int = 43200
    auth_enforce_client_binding: bool = False
    auth_session_hmac_secret: SecretStr = SecretStr(
        "local-only-change-this-session-hmac-secret-before-deployment"
    )

    @field_validator("auth_session_hmac_secret")
    @classmethod
    def validate_session_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("AUTH_SESSION_HMAC_SECRET must be at least 32 characters")
        return value

    @property
    def oidc_algorithms(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.oidc_allowed_algorithms.split(",") if part.strip())

    @property
    def required_oidc_scopes(self) -> frozenset[str]:
        return frozenset(part.strip() for part in self.oidc_required_scopes.split() if part.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


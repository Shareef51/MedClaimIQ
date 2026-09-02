from __future__ import annotations
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.ingestion_factory import build_object_storage
from app.document_intelligence.isolation import SubprocessParserExecutor
from app.domain.document_intelligence import RetryPolicy
from app.workers.document_intelligence import DocumentIntelligenceWorker


def build_document_intelligence_worker(session: Session, tenant_id: str, settings: Settings) -> DocumentIntelligenceWorker:
    return DocumentIntelligenceWorker(
        session,
        tenant_id,
        storage=build_object_storage(settings),
        bucket_name=settings.s3_bucket,
        parser=SubprocessParserExecutor(timeout_seconds=settings.document_parser_timeout_seconds),
        pipeline_version=settings.document_pipeline_version,
        retry_policy=RetryPolicy(
            max_attempts=settings.document_extraction_max_attempts,
            base_delay_seconds=settings.document_extraction_retry_base_seconds,
            max_delay_seconds=settings.document_extraction_retry_max_seconds,
        ),
        max_input_bytes=settings.upload_max_file_bytes,
    )

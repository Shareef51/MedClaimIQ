from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.claims import EvidenceSourceType
from app.domain.ingestion import (
    ALLOWED_UPLOAD_TYPES,
    DEFAULT_MAX_BYTES_BY_KIND,
    IngestionEventType,
    MediaKind,
    OutboxStatus,
    UploadSessionStatus,
)
from app.ingestion.content_validation import (
    ContentValidationError,
    safe_extension,
    validate_declared_upload,
)
from app.models.ingestion import (
    EvidenceEventOutboxModel,
    EvidenceProcessingEventModel,
    EvidenceUploadSessionModel,
)
from app.repositories.claims import ClaimRepository
from app.repositories.ingestion import (
    EvidenceOutboxRepository,
    ProcessingEventRepository,
    UploadSessionRepository,
)
from app.schemas.ingestion import UploadInitiateRequest
from app.storage.object_store import ObjectStorage, PresignedUpload


class IngestionInvariantError(ValueError):
    def __init__(self, code: str, message: str, *, persist_state: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.persist_state = persist_state


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_detail(message: str) -> str:
    # Error details must remain operational and must not echo file names or object bodies.
    return message[:500]


class EvidenceIngestionService:
    def __init__(
        self,
        session: Session,
        tenant_id: str,
        *,
        storage: ObjectStorage,
        bucket_name: str,
        presign_ttl_seconds: int = 900,
        global_max_file_bytes: int = 500 * 1024 * 1024,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.storage = storage
        self.bucket_name = bucket_name
        self.presign_ttl_seconds = presign_ttl_seconds
        self.global_max_file_bytes = global_max_file_bytes
        self.uploads = UploadSessionRepository(session, tenant_id)
        self.events = ProcessingEventRepository(session, tenant_id)
        self.outbox = EvidenceOutboxRepository(session, tenant_id)
        self.claims = ClaimRepository(session, tenant_id)

    def initiate_upload(
        self,
        *,
        claim_id: str,
        user_id: str,
        source_type: EvidenceSourceType,
        idempotency_key: str,
        payload: UploadInitiateRequest,
        trace_id: str | None = None,
    ) -> tuple[EvidenceUploadSessionModel, PresignedUpload]:
        existing = self.uploads.get_by_idempotency(idempotency_key)
        if existing is not None:
            if existing.claim_id != claim_id or existing.initiated_by_user_id != user_id:
                raise IngestionInvariantError(
                    "idempotency_conflict", "idempotency key was already used for another upload"
                )
            if existing.status != UploadSessionStatus.INITIATED.value:
                raise IngestionInvariantError(
                    "upload_already_completed", "upload session is no longer accepting object uploads"
                )
            if existing.upload_expires_at <= _now():
                existing.status = UploadSessionStatus.EXPIRED.value
                existing.status_version += 1
                raise IngestionInvariantError(
                    "upload_expired", "upload session has expired", persist_state=True
                )
            return existing, self._presign(existing)

        claim = self.claims.get(claim_id)
        if claim is None:
            raise IngestionInvariantError("claim_not_found", "claim does not exist in the selected tenant")

        try:
            extension = safe_extension(payload.client_filename)
            _, kind = ALLOWED_UPLOAD_TYPES[extension]
            max_for_kind = min(self.global_max_file_bytes, DEFAULT_MAX_BYTES_BY_KIND[kind])
            validate_declared_upload(
                extension=extension,
                media_type=payload.declared_media_type,
                byte_size=payload.expected_byte_size,
                max_bytes=max_for_kind,
            )
        except ContentValidationError as exc:
            raise IngestionInvariantError(exc.code, str(exc)) from exc

        session_id = f"upl_{uuid4().hex}"
        object_key = f"quarantine/{self.tenant_id}/{claim_id}/{session_id}/object{extension}"
        expires_at = _now() + timedelta(seconds=self.presign_ttl_seconds)
        model = self.uploads.add(
            EvidenceUploadSessionModel(
                upload_session_id=session_id,
                tenant_id=self.tenant_id,
                claim_id=claim_id,
                initiated_by_user_id=user_id,
                bucket_name=self.bucket_name,
                quarantine_object_key=object_key,
                client_filename_sha256=hashlib.sha256(payload.client_filename.encode("utf-8")).hexdigest(),
                client_extension=extension,
                source_type=source_type.value,
                document_type=payload.document_type,
                declared_media_type=payload.declared_media_type.split(";", 1)[0].strip().lower(),
                media_kind=kind.value,
                expected_byte_size=payload.expected_byte_size,
                expected_sha256=payload.expected_sha256.lower() if payload.expected_sha256 else None,
                captured_at=payload.captured_at,
                status=UploadSessionStatus.INITIATED.value,
                status_version=1,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
                upload_expires_at=expires_at,
            )
        )
        self.append_event(
            upload=model,
            event_type=IngestionEventType.UPLOAD_INITIATED,
            idempotency_key=f"event:init:{session_id}",
            payload={
                "upload_session_id": session_id,
                "claim_id": claim_id,
                "media_kind": model.media_kind,
                "expected_byte_size": model.expected_byte_size,
            },
        )
        return model, self._presign(model)

    def complete_upload(self, upload_session_id: str) -> tuple[EvidenceUploadSessionModel, EvidenceProcessingEventModel]:
        upload = self.uploads.get_for_update(upload_session_id)
        if upload is None:
            raise IngestionInvariantError("upload_not_found", "upload session was not found")

        completion_key = f"event:complete:{upload_session_id}"
        existing_event = self.events.get_by_idempotency(completion_key)
        if existing_event is not None and upload.status != UploadSessionStatus.INITIATED.value:
            return upload, existing_event

        if upload.status != UploadSessionStatus.INITIATED.value:
            raise IngestionInvariantError("invalid_upload_state", "upload session cannot be completed from its current state")
        if upload.upload_expires_at <= _now():
            upload.status = UploadSessionStatus.EXPIRED.value
            upload.status_version += 1
            raise IngestionInvariantError(
                "upload_expired", "upload session has expired", persist_state=True
            )

        try:
            info = self.storage.head_object(bucket=upload.bucket_name, key=upload.quarantine_object_key)
        except Exception as exc:  # storage adapters normalize errors at infrastructure boundaries later
            raise IngestionInvariantError("object_not_available", "uploaded object is not available") from exc

        expected_metadata = {
            "upload-session-id": upload.upload_session_id,
            "tenant-id": upload.tenant_id,
            "claim-id": upload.claim_id,
        }
        for key, expected in expected_metadata.items():
            if info.metadata.get(key) != expected:
                self._reject(upload, "object_metadata_mismatch", "signed object metadata did not match the upload session")
                self._append_rejection_event(upload)
                raise IngestionInvariantError(
                    "object_metadata_mismatch",
                    "uploaded object failed ownership metadata validation",
                    persist_state=True,
                )
        if info.byte_size != upload.expected_byte_size:
            self._reject(upload, "object_size_mismatch", "stored object size did not match the declared size")
            self._append_rejection_event(upload)
            raise IngestionInvariantError(
                "object_size_mismatch",
                "uploaded object size does not match the declared size",
                persist_state=True,
            )
        if info.content_type and info.content_type.split(";", 1)[0].strip().lower() != upload.declared_media_type:
            self._reject(upload, "storage_content_type_mismatch", "stored content type did not match the signed upload")
            self._append_rejection_event(upload)
            raise IngestionInvariantError(
                "storage_content_type_mismatch",
                "uploaded object content type is inconsistent",
                persist_state=True,
            )

        upload.actual_byte_size = info.byte_size
        upload.storage_etag = info.etag
        upload.storage_version_id = info.version_id
        upload.status = UploadSessionStatus.UPLOADED.value
        upload.status_version += 1
        upload.uploaded_at = _now()

        event = self.append_event(
            upload=upload,
            event_type=IngestionEventType.UPLOAD_COMPLETED,
            idempotency_key=completion_key,
            payload={
                "upload_session_id": upload.upload_session_id,
                "claim_id": upload.claim_id,
                "byte_size": info.byte_size,
            },
        )
        return upload, event

    def append_event(
        self,
        *,
        upload: EvidenceUploadSessionModel,
        event_type: IngestionEventType,
        idempotency_key: str,
        payload: dict[str, object],
    ) -> EvidenceProcessingEventModel:
        existing = self.events.get_by_idempotency(idempotency_key)
        if existing is not None:
            return existing
        now = _now()
        event = self.events.add(
            EvidenceProcessingEventModel(
                event_id=f"evt_{uuid4().hex}",
                tenant_id=self.tenant_id,
                claim_id=upload.claim_id,
                aggregate_type="evidence_upload_session",
                aggregate_id=upload.upload_session_id,
                event_type=event_type.value,
                payload=payload,
                trace_id=upload.trace_id,
                idempotency_key=idempotency_key,
                occurred_at=now,
            )
        )
        self.outbox.add(
            EvidenceEventOutboxModel(
                outbox_id=f"out_{uuid4().hex}",
                tenant_id=self.tenant_id,
                event_id=event.event_id,
                topic="medclaimiq.evidence.events.v1",
                partition_key=upload.claim_id,
                status=OutboxStatus.PENDING.value,
                attempt_count=0,
                available_at=now,
            )
        )
        return event

    def _presign(self, upload: EvidenceUploadSessionModel) -> PresignedUpload:
        remaining = max(1, int((upload.upload_expires_at - _now()).total_seconds()))
        return self.storage.create_presigned_upload(
            bucket=upload.bucket_name,
            key=upload.quarantine_object_key,
            content_type=upload.declared_media_type,
            metadata={
                "upload-session-id": upload.upload_session_id,
                "tenant-id": upload.tenant_id,
                "claim-id": upload.claim_id,
            },
            expires_seconds=min(self.presign_ttl_seconds, remaining),
            expected_byte_size=upload.expected_byte_size,
        )

    def _append_rejection_event(self, upload: EvidenceUploadSessionModel) -> None:
        self.append_event(
            upload=upload,
            event_type=IngestionEventType.INGESTION_REJECTED,
            idempotency_key=f"event:rejected:{upload.upload_session_id}:{upload.rejection_code}",
            payload={
                "upload_session_id": upload.upload_session_id,
                "claim_id": upload.claim_id,
                "rejection_code": upload.rejection_code,
            },
        )

    @staticmethod
    def _reject(upload: EvidenceUploadSessionModel, code: str, detail: str) -> None:
        upload.status = UploadSessionStatus.REJECTED.value
        upload.status_version += 1
        upload.rejection_code = code
        upload.rejection_detail = _safe_detail(detail)
        upload.finalized_at = _now()

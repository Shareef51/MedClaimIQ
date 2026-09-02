from __future__ import annotations

import hashlib
from sqlalchemy import select
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.claims import ActorType, EvidenceSourceType, EvidenceStatus
from app.domain.ingestion import IngestionEventType, MalwareVerdict, MediaKind, UploadSessionStatus
from app.ingestion.content_validation import (
    ContentValidationError,
    detect_content,
    enforce_detected_matches_declared,
)
from app.ingestion.malware import MalwareScanner
from app.models.ingestion import EvidenceUploadSessionModel, MalwareScanModel
from app.models.portal import PortalActionEventModel, PortalDocumentRequestModel, PortalSubmissionModel
from app.repositories.claims import EvidenceRepository
from app.repositories.ingestion import MalwareScanRepository, UploadSessionRepository
from app.schemas.claims import EvidenceCreate
from app.services.claims import ClaimDomainService
from app.services.ingestion import EvidenceIngestionService, IngestionInvariantError
from app.storage.object_store import ObjectStorage
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceIngestionWorker:
    """Quarantine worker that turns an uploaded object into trusted evidence.

    No parser, OCR model, RAG indexer, or LLM may consume the object until this worker
    has validated bytes, computed the server hash, received a clean malware verdict,
    and promoted the object out of the quarantine prefix.
    """

    def __init__(
        self,
        session: Session,
        tenant_id: str,
        *,
        storage: ObjectStorage,
        scanner: MalwareScanner,
        bucket_name: str,
        malware_scan_required: bool = True,
        chunk_size: int = 1024 * 1024,
        sample_limit: int = 256 * 1024,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.storage = storage
        self.scanner = scanner
        self.bucket_name = bucket_name
        self.malware_scan_required = malware_scan_required
        self.chunk_size = chunk_size
        self.sample_limit = sample_limit
        self.uploads = UploadSessionRepository(session, tenant_id)
        self.scans = MalwareScanRepository(session, tenant_id)
        self.evidence = EvidenceRepository(session, tenant_id)
        self.events = EvidenceIngestionService(
            session, tenant_id, storage=storage, bucket_name=bucket_name
        )
        self.claim_domain = ClaimDomainService(session, tenant_id)

    def process(self, upload_session_id: str) -> EvidenceUploadSessionModel:
        upload = self.uploads.get_for_update(upload_session_id)
        if upload is None:
            raise IngestionInvariantError("upload_not_found", "upload session was not found")
        if upload.status in {
            UploadSessionStatus.ACCEPTED.value,
            UploadSessionStatus.DUPLICATE.value,
            UploadSessionStatus.REJECTED.value,
        }:
            return upload
        if upload.status not in {UploadSessionStatus.UPLOADED.value, UploadSessionStatus.VERIFYING.value}:
            raise IngestionInvariantError(
                "invalid_upload_state", "only completed uploads can enter quarantine verification"
            )

        upload.status = UploadSessionStatus.VERIFYING.value
        upload.status_version += 1
        self.events.append_event(
            upload=upload,
            event_type=IngestionEventType.VERIFICATION_STARTED,
            idempotency_key=f"event:verify:{upload.upload_session_id}",
            payload={"upload_session_id": upload.upload_session_id, "claim_id": upload.claim_id},
        )

        try:
            object_info = self._revalidate_storage_identity(upload)
            digest, actual_size, sample = self._hash_and_sample(upload)
            if actual_size != upload.expected_byte_size:
                return self._reject(upload, "stream_size_mismatch", "object size changed during verification")
            if upload.expected_sha256 and digest != upload.expected_sha256:
                return self._reject(upload, "sha256_mismatch", "server hash did not match the expected SHA-256")

            detected = detect_content(sample, extension=upload.client_extension)
            enforce_detected_matches_declared(
                detected=detected,
                declared_media_type=upload.declared_media_type,
                expected_kind=MediaKind(upload.media_kind),
            )
            upload.actual_sha256 = digest
            upload.actual_byte_size = actual_size
            upload.detected_media_type = detected.media_type
            upload.media_metadata = detected.metadata
            upload.verified_at = _now()
            self.events.append_event(
                upload=upload,
                event_type=IngestionEventType.CONTENT_VERIFIED,
                idempotency_key=f"event:content-verified:{upload.upload_session_id}",
                payload={
                    "upload_session_id": upload.upload_session_id,
                    "sha256": digest,
                    "byte_size": actual_size,
                    "detected_media_type": detected.media_type,
                },
            )

            verdict = self._scan(upload)
            if verdict is MalwareVerdict.ERROR:
                upload.status = UploadSessionStatus.QUARANTINED.value
                upload.status_version += 1
                upload.rejection_code = "malware_scanner_unavailable"
                self.events.append_event(
                    upload=upload,
                    event_type=IngestionEventType.MALWARE_SCAN_FAILED,
                    idempotency_key=f"event:scan-failed:{upload.upload_session_id}:{upload.status_version}",
                    payload={"upload_session_id": upload.upload_session_id, "retryable": True},
                )
                if self.malware_scan_required:
                    raise IngestionInvariantError(
                        "malware_scanner_unavailable", "malware scanning did not produce a clean verdict"
                    )
            elif verdict is not MalwareVerdict.CLEAN:
                return self._reject(upload, "malware_detected", "object did not pass malware scanning")

            # Re-check identity after streaming/scan to reduce the window for an object
            # replacement using a still-valid presigned URL.
            after_scan = self._revalidate_storage_identity(upload)
            if object_info.etag and after_scan.etag != object_info.etag:
                return self._reject(upload, "object_changed_during_scan", "object identity changed during verification")
            if object_info.version_id and after_scan.version_id != object_info.version_id:
                return self._reject(upload, "object_changed_during_scan", "object version changed during verification")

            duplicate = self.evidence.get_by_content_hash(upload.claim_id, digest)
            if duplicate is not None:
                self.storage.delete_object(bucket=upload.bucket_name, key=upload.quarantine_object_key)
                upload.evidence_id = duplicate.evidence_id
                upload.status = UploadSessionStatus.DUPLICATE.value
                upload.status_version += 1
                upload.finalized_at = _now()
                self.events.append_event(
                    upload=upload,
                    event_type=IngestionEventType.INGESTION_DUPLICATE,
                    idempotency_key=f"event:duplicate:{upload.upload_session_id}",
                    payload={
                        "upload_session_id": upload.upload_session_id,
                        "claim_id": upload.claim_id,
                        "evidence_id": duplicate.evidence_id,
                    },
                )
                self._sync_portal_submission(upload, accepted=True)
                return upload

            accepted_key = (
                f"accepted/{upload.tenant_id}/{upload.claim_id}/{upload.upload_session_id}/"
                f"{digest[:24]}{upload.client_extension}"
            )
            promoted = self.storage.promote_object(
                bucket=upload.bucket_name,
                source_key=upload.quarantine_object_key,
                destination_key=accepted_key,
                source_version_id=object_info.version_id,
            )
            evidence = self.claim_domain.add_evidence(
                EvidenceCreate(
                    evidence_id=f"ev_{uuid4().hex}",
                    claim_id=upload.claim_id,
                    source_type=EvidenceSourceType(upload.source_type),
                    source_system="medclaimiq-secure-upload",
                    source_locator={
                        "upload_session_id": upload.upload_session_id,
                        "bucket": upload.bucket_name,
                    },
                    document_type=upload.document_type,
                    media_type=detected.media_type,
                    object_key=accepted_key,
                    storage_etag=promoted.etag,
                    storage_version_id=promoted.version_id,
                    content_sha256=digest,
                    byte_size=actual_size,
                    status=EvidenceStatus.ACCEPTED,
                    uploaded_by_user_id=upload.initiated_by_user_id,
                    captured_at=upload.captured_at,
                    media_metadata=detected.metadata,
                    verified_at=upload.verified_at,
                    actor_type=ActorType.WORKER,
                    actor_id="secure-evidence-ingestion-worker",
                    idempotency_key=f"ingestion:{upload.upload_session_id}:evidence",
                    trace_id=upload.trace_id,
                )
            )
            upload.accepted_object_key = accepted_key
            upload.storage_etag = promoted.etag
            upload.storage_version_id = promoted.version_id
            upload.evidence_id = evidence.evidence_id
            upload.status = UploadSessionStatus.ACCEPTED.value
            upload.status_version += 1
            upload.finalized_at = _now()
            self.events.append_event(
                upload=upload,
                event_type=IngestionEventType.INGESTION_ACCEPTED,
                idempotency_key=f"event:accepted:{upload.upload_session_id}",
                payload={
                    "upload_session_id": upload.upload_session_id,
                    "claim_id": upload.claim_id,
                    "evidence_id": evidence.evidence_id,
                    "media_type": evidence.media_type,
                },
            )
            self.events.append_event(
                upload=upload,
                event_type=IngestionEventType.PROCESSING_REQUESTED,
                idempotency_key=f"event:processing-requested:{upload.upload_session_id}",
                payload={
                    "claim_id": upload.claim_id,
                    "evidence_id": evidence.evidence_id,
                    "document_type": evidence.document_type,
                    "media_type": evidence.media_type,
                },
            )
            self._sync_portal_submission(upload, accepted=True)
            return upload
        except ContentValidationError as exc:
            return self._reject(upload, exc.code, str(exc))

    def _revalidate_storage_identity(self, upload: EvidenceUploadSessionModel):
        info = self.storage.head_object(bucket=upload.bucket_name, key=upload.quarantine_object_key)
        if info.byte_size != upload.expected_byte_size:
            raise IngestionInvariantError("object_size_mismatch", "object size changed after upload completion")
        if upload.storage_etag and info.etag and upload.storage_etag != info.etag:
            raise IngestionInvariantError("object_identity_mismatch", "object ETag changed after upload completion")
        if upload.storage_version_id and info.version_id != upload.storage_version_id:
            raise IngestionInvariantError("object_identity_mismatch", "object version changed after upload completion")
        return info

    def _hash_and_sample(self, upload: EvidenceUploadSessionModel) -> tuple[str, int, bytes]:
        digest = hashlib.sha256()
        total = 0
        sample = bytearray()
        for chunk in self.storage.iter_object_chunks(
            bucket=upload.bucket_name, key=upload.quarantine_object_key, chunk_size=self.chunk_size
        ):
            total += len(chunk)
            if total > upload.expected_byte_size:
                raise IngestionInvariantError("stream_size_overflow", "object exceeded the declared size")
            digest.update(chunk)
            if len(sample) < self.sample_limit:
                sample.extend(chunk[: self.sample_limit - len(sample)])
        return digest.hexdigest(), total, bytes(sample)

    def _scan(self, upload: EvidenceUploadSessionModel) -> MalwareVerdict:
        started_at = _now()
        result = self.scanner.scan(
            self.storage.iter_object_chunks(
                bucket=upload.bucket_name, key=upload.quarantine_object_key, chunk_size=self.chunk_size
            )
        )
        completed_at = _now()
        attempt = self.scans.count_attempts(upload.upload_session_id) + 1
        self.scans.add(
            MalwareScanModel(
                scan_id=f"scan_{uuid4().hex}",
                tenant_id=self.tenant_id,
                upload_session_id=upload.upload_session_id,
                attempt_number=attempt,
                scanner_name=result.scanner_name,
                scanner_version=result.scanner_version,
                verdict=result.verdict.value,
                signature_name=result.signature_name,
                details=result.details or {},
                started_at=started_at,
                completed_at=completed_at,
            )
        )
        if result.verdict is not MalwareVerdict.ERROR:
            self.events.append_event(
                upload=upload,
                event_type=IngestionEventType.MALWARE_SCAN_COMPLETED,
                idempotency_key=f"event:scan:{upload.upload_session_id}:{attempt}",
                payload={
                    "upload_session_id": upload.upload_session_id,
                    "verdict": result.verdict.value,
                    # Malware signature names are operational metadata, not document content.
                    "signature_name": result.signature_name,
                },
            )
        return result.verdict

    def _reject(self, upload: EvidenceUploadSessionModel, code: str, detail: str) -> EvidenceUploadSessionModel:
        upload.status = UploadSessionStatus.REJECTED.value
        upload.status_version += 1
        upload.rejection_code = code
        upload.rejection_detail = detail[:500]
        upload.finalized_at = _now()
        self.events.append_event(
            upload=upload,
            event_type=IngestionEventType.INGESTION_REJECTED,
            idempotency_key=f"event:rejected:{upload.upload_session_id}:{code}",
            payload={
                "upload_session_id": upload.upload_session_id,
                "claim_id": upload.claim_id,
                "rejection_code": code,
            },
        )
        self._sync_portal_submission(upload, accepted=False)
        return upload

    def _sync_portal_submission(self, upload: EvidenceUploadSessionModel, *, accepted: bool) -> None:
        submission = self.session.scalar(
            select(PortalSubmissionModel).where(
                PortalSubmissionModel.tenant_id == self.tenant_id,
                PortalSubmissionModel.upload_session_id == upload.upload_session_id,
            )
        )
        if submission is None:
            return
        now = _now()
        submission.evidence_id = upload.evidence_id
        submission.status = "accepted" if accepted else "rejected"
        submission.updated_at = now
        request = self.session.scalar(
            select(PortalDocumentRequestModel).where(
                PortalDocumentRequestModel.tenant_id == self.tenant_id,
                PortalDocumentRequestModel.request_id == submission.request_id,
            )
        )
        event_type = "claim.missing_evidence.received" if accepted else "portal.document_upload.rejected"
        idempotency_key = f"portal-worker:{event_type}:{upload.upload_session_id}"
        prior = self.session.scalar(
            select(PortalActionEventModel).where(
                PortalActionEventModel.tenant_id == self.tenant_id,
                PortalActionEventModel.idempotency_key == idempotency_key,
            )
        )
        if prior is None:
            row = PortalActionEventModel(
                event_id=f"pevt_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=upload.claim_id,
                actor_user_id=submission.submitted_by_user_id, event_type=event_type,
                idempotency_key=idempotency_key,
                payload={"request_id": submission.request_id, "submission_id": submission.submission_id,
                         "acknowledgement_code": submission.acknowledgement_code, "status": submission.status},
                trace_id=upload.trace_id, occurred_at=now,
            )
            self.session.add(row); self.session.flush()
            enqueue_realtime_event(
                self.session,
                envelope=EventEnvelope(
                    event_id=row.event_id,event_type=event_type,tenant_id=self.tenant_id,claim_id=upload.claim_id,
                    aggregate_type="external_portal",aggregate_id=upload.claim_id,occurred_at=now,
                    trace_id=upload.trace_id,producer="medclaimiq-secure-evidence-ingestion-worker",payload=row.payload,
                ),
                topic=EventTopic.CLAIMS.value,
            )
        if accepted and request is not None:
            request.status = "satisfied"
            request.satisfied_at = now
            request.updated_at = now

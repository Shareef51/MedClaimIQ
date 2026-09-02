from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType, UserRole
from app.domain.claims import EvidenceSourceType
from app.domain.ingestion import MediaKind, UploadSessionStatus
from app.repositories.claims import ClaimRepository
from app.repositories.ingestion import UploadSessionRepository
from app.schemas.ingestion import (
    IngestionModelResponse,
    UploadCompleteResponse,
    UploadInitiateRequest,
    UploadInitiateResponse,
    UploadSessionView,
)
from app.security.authentication import RequestIdentity
from app.services.authorization import authorization_service
from app.services.ingestion import EvidenceIngestionService, IngestionInvariantError

router = APIRouter(tags=["evidence-ingestion"])
settings = get_settings()


def _identity(request: Request) -> RequestIdentity:
    identity: RequestIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    return identity


def _claim_access_context(db: Session, tenant_id: str, claim_id: str) -> ResourceAccessContext:
    claim = ClaimRepository(db, tenant_id).get(claim_id)
    if claim is None:
        # Deliberately avoid disclosing whether the identifier exists in another tenant.
        raise HTTPException(status_code=404, detail="claim was not found")
    return ResourceAccessContext(
        resource_type=ResourceType.CLAIM,
        resource_id=claim.claim_id,
        owner_tenant_id=claim.tenant_id,
        owner_patient_subject_id=claim.patient_subject_id,
        related_provider_organization_id=claim.provider_organization_id,
        assigned_reviewer_user_id=claim.assigned_reviewer_user_id,
    )


def _authorize_claim(db: Session, identity: RequestIdentity, claim_id: str, permission: Permission) -> None:
    resource = _claim_access_context(db, identity.principal.tenant_id, claim_id)
    decision = authorization_service.evaluate(
        AccessRequest(principal=identity.principal, permission=permission, resource=resource)
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="access to the claim resource is denied")


def _source_type(role: UserRole) -> EvidenceSourceType:
    if role in {UserRole.PROVIDER, UserRole.HOSPITAL_ADMIN}:
        return EvidenceSourceType.PROVIDER_UPLOAD
    return EvidenceSourceType.USER_UPLOAD


@router.get("/ingestion-model", response_model=IngestionModelResponse)
def get_ingestion_model() -> IngestionModelResponse:
    return IngestionModelResponse(
        storage_boundary=(
            "uploads land only in a quarantine object prefix",
            "signed upload metadata binds object to tenant, claim, and upload session",
            "object version/ETag is persisted and revalidated",
            "clean unique objects are promoted to an accepted prefix before downstream use",
        ),
        validation_controls=(
            "extension and declared MIME allowlist at initiation",
            "server-side byte count and SHA-256",
            "magic-byte/server content detection",
            "declared-versus-detected type anti-spoofing check",
            "no raw client filename persisted",
        ),
        malware_controls=(
            "streaming malware scan while object remains quarantined",
            "clean verdict required by default",
            "scan attempts are persisted",
            "infected/suspicious objects never become evidence artifacts",
        ),
        event_controls=(
            "append-only evidence processing events",
            "transactional outbox rows",
            "claim partition key",
            "idempotent event keys for replay-safe workers",
        ),
        supported_media_kinds=tuple(MediaKind),
        acceptance_rule=(
            "No OCR, parser, RAG indexer, model, or agent may consume an upload until server validation "
            "and the required malware scan complete successfully."
        ),
    )


@router.post(
    "/claims/{claim_id}/evidence/uploads",
    response_model=UploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_evidence_upload(
    claim_id: str,
    payload: UploadInitiateRequest,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    trace_id: str | None = Header(default=None, alias="X-Trace-Id", max_length=128),
) -> UploadInitiateResponse:
    identity = _identity(request)
    _authorize_claim(db, identity, claim_id, Permission.EVIDENCE_UPLOAD)
    storage = request.app.state.object_storage_provider()
    service = EvidenceIngestionService(
        db,
        identity.principal.tenant_id,
        storage=storage,
        bucket_name=settings.s3_bucket,
        presign_ttl_seconds=settings.upload_presign_ttl_seconds,
        global_max_file_bytes=settings.upload_max_file_bytes,
    )
    try:
        upload, signed = service.initiate_upload(
            claim_id=claim_id,
            user_id=identity.principal.user_id,
            source_type=_source_type(identity.principal.role),
            idempotency_key=idempotency_key,
            payload=payload,
            trace_id=trace_id,
        )
        db.commit()
    except IngestionInvariantError as exc:
        if exc.persist_state:
            db.commit()
        else:
            db.rollback()
        code = 404 if exc.code == "claim_not_found" else 409 if "idempotency" in exc.code else 422
        raise HTTPException(status_code=code, detail={"code": exc.code, "message": str(exc)}) from exc
    return UploadInitiateResponse(
        upload_session_id=upload.upload_session_id,
        claim_id=upload.claim_id,
        status=UploadSessionStatus(upload.status),
        method=signed.method,
        upload_url=signed.url,
        required_headers=signed.required_headers,
        form_fields=signed.form_fields,
        upload_expires_at=upload.upload_expires_at,
        expected_byte_size=upload.expected_byte_size,
        media_kind=MediaKind(upload.media_kind),
    )


@router.post(
    "/claims/{claim_id}/evidence/uploads/{upload_session_id}/complete",
    response_model=UploadCompleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def complete_evidence_upload(
    claim_id: str,
    upload_session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> UploadCompleteResponse:
    identity = _identity(request)
    _authorize_claim(db, identity, claim_id, Permission.EVIDENCE_UPLOAD)
    storage = request.app.state.object_storage_provider()
    service = EvidenceIngestionService(
        db,
        identity.principal.tenant_id,
        storage=storage,
        bucket_name=settings.s3_bucket,
        presign_ttl_seconds=settings.upload_presign_ttl_seconds,
        global_max_file_bytes=settings.upload_max_file_bytes,
    )
    upload = UploadSessionRepository(db, identity.principal.tenant_id).get(upload_session_id)
    if upload is None or upload.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="upload session was not found")
    if upload.initiated_by_user_id != identity.principal.user_id:
        raise HTTPException(status_code=403, detail="only the initiating identity may complete this upload")
    try:
        upload, event = service.complete_upload(upload_session_id)
        db.commit()
    except IngestionInvariantError as exc:
        if exc.persist_state:
            db.commit()
        else:
            db.rollback()
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc
    return UploadCompleteResponse(
        upload_session_id=upload.upload_session_id,
        claim_id=upload.claim_id,
        status=UploadSessionStatus(upload.status),
        accepted_for_processing=upload.status == UploadSessionStatus.UPLOADED.value,
        event_id=event.event_id,
    )


@router.get(
    "/claims/{claim_id}/evidence/uploads/{upload_session_id}",
    response_model=UploadSessionView,
)
def get_evidence_upload(
    claim_id: str,
    upload_session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> UploadSessionView:
    identity = _identity(request)
    _authorize_claim(db, identity, claim_id, Permission.EVIDENCE_READ)
    upload = UploadSessionRepository(db, identity.principal.tenant_id).get(upload_session_id)
    if upload is None or upload.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="upload session was not found")
    return UploadSessionView.model_validate(upload)

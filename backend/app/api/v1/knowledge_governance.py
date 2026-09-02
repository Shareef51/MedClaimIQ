from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository
from app.schemas.knowledge_governance import (
    ApprovalRequest, DocumentCreateRequest, DriftEvaluationRequest, IndexMigrationCreate,
    ProjectionRequest, QualityRunRequest, ReleaseCreateRequest, ReleasePromoteRequest,
    SourceOnboardRequest, StaleScanRequest, VersionCreateRequest,
)
from app.services.knowledge_governance import KnowledgeGovernanceService, knowledge_governance_model_contract

router = APIRouter(tags=["knowledge-governance"])
ADMINS = {UserRole.TENANT_ADMIN, UserRole.SYSTEM_ADMIN}
READERS = {UserRole.TENANT_ADMIN, UserRole.AUDITOR, UserRole.SYSTEM_ADMIN}


def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity required")
    return identity


def _service(request: Request, db: Session, roles: set[UserRole]):
    identity = _identity(request)
    if identity.principal.role not in roles:
        raise HTTPException(403, "knowledge governance access denied")
    return identity, KnowledgeGovernanceService(KnowledgeGovernanceRepository(db, identity.principal.tenant_id))


def _call(db: Session, fn):
    try:
        result = fn()
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "knowledge governance uniqueness conflict") from exc
    except (ValueError, PermissionError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get("/knowledge-governance-model")
def model_contract() -> dict:
    return knowledge_governance_model_contract()


@router.get("/knowledge-governance/history")
def history(request: Request, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, READERS)
    return svc.history(min(max(limit, 1), 100))


@router.post("/knowledge-governance/sources")
def onboard_source(payload: SourceOnboardRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.onboard_source(actor=identity.principal.user_id, **payload.model_dump()))
    return {"source_id": item.source_id, "source_key": item.source_key, "status": item.status, "authority_rank": item.authority_rank}


@router.post("/knowledge-governance/documents")
def create_document(payload: DocumentCreateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.create_document(actor=identity.principal.user_id, **payload.model_dump()))
    return {"document_id": item.document_id, "source_id": item.source_id, "domain": item.domain}


@router.post("/knowledge-governance/documents/{document_id}/versions")
def create_version(document_id: str, payload: VersionCreateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.create_version(actor=identity.principal.user_id, document_id=document_id, **payload.model_dump()))
    return {"version_id": item.version_id, "version": item.version, "status": item.status, "content_sha256": item.content_sha256}


@router.post("/knowledge-governance/versions/{version_id}/submit")
def submit_version(version_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.submit_version(actor=identity.principal.user_id, version_id=version_id))
    return {"version_id": item.version_id, "status": item.status}


@router.post("/knowledge-governance/versions/{version_id}/quality")
def quality(version_id: str, payload: QualityRunRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.run_quality(actor=identity.principal.user_id, version_id=version_id, **payload.model_dump()))
    return {"quality_run_id": item.quality_run_id, "score": item.score, "passed": item.passed, "reasons": item.reasons}


@router.post("/knowledge-governance/versions/{version_id}/approve")
def approve(version_id: str, payload: ApprovalRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.approve_version(actor=identity.principal.user_id, version_id=version_id, reason=payload.reason))
    return {"version_id": item.version_id, "status": item.status, "approved_by": item.approved_by}


@router.post("/knowledge-governance/versions/{version_id}/reindex")
def reindex(version_id: str, payload: ProjectionRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.request_reindex(actor=identity.principal.user_id, version_id=version_id, **payload.model_dump()))
    return {"job_id": item.job_id, "status": item.status, "action": item.action, "stale_chunk_count": item.stale_chunk_count}


@router.post("/knowledge-governance/projections/stale-scan")
def stale_scan(payload: StaleScanRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    return _call(db, lambda: svc.scan_stale_vectors(actor=identity.principal.user_id, **payload.model_dump()))


@router.post("/knowledge-governance/index-migrations")
def create_migration(payload: IndexMigrationCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.create_index_migration(actor=identity.principal.user_id, **payload.model_dump()))
    return {"migration_id": item.migration_id, "status": item.status, "to_index_version": item.to_index_version}


@router.post("/knowledge-governance/index-migrations/{migration_id}/approve")
def approve_migration(migration_id: str, payload: ApprovalRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item, queued = _call(db, lambda: svc.approve_index_migration(actor=identity.principal.user_id, migration_id=migration_id))
    return {"migration_id": item.migration_id, "status": item.status, "queued_versions": queued}


@router.post("/knowledge-governance/index-migrations/{migration_id}/refresh")
def refresh_migration(migration_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.refresh_index_migration(actor=identity.principal.user_id, migration_id=migration_id))
    return {"migration_id": item.migration_id, "status": item.status, "completed_at": item.completed_at}


@router.post("/knowledge-governance/retrieval-drift")
def retrieval_drift(payload: DriftEvaluationRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.evaluate_retrieval_drift(actor=identity.principal.user_id, **payload.model_dump()))
    return {"drift_event_id": item.drift_event_id, "severity": item.severity, "blocking": item.blocking, "reasons": item.reasons}


@router.post("/knowledge-governance/releases")
def create_release(payload: ReleaseCreateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.create_release(actor=identity.principal.user_id, **payload.model_dump()))
    return {"release_id": item.release_id, "status": item.status, "manifest_sha256": item.manifest_sha256}


@router.post("/knowledge-governance/releases/{release_id}/promote")
def promote_release(release_id: str, payload: ReleasePromoteRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMINS)
    item = _call(db, lambda: svc.promote_release(actor=identity.principal.user_id, release_id=release_id, **payload.model_dump()))
    return {"release_id": item.release_id, "status": item.status, "promoted_at": item.promoted_at}

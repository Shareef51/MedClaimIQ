from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.authentication import (
    AuthenticationContextResponse,
    SessionRevokeRequest,
    SessionRevokeResponse,
)
from app.security.authentication import RequestIdentity
from app.security.session import AuthenticationSessionService, SessionSecurityError

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=AuthenticationContextResponse)
def get_authentication_context(request: Request) -> AuthenticationContextResponse:
    identity: RequestIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    return AuthenticationContextResponse(
        user_id=identity.principal.user_id,
        tenant_id=identity.principal.tenant_id,
        role=identity.principal.role.value,
        application_session_id=identity.application_session_id,
        token_issuer=identity.token.issuer,
        token_subject=identity.token.subject,
        token_expires_at=identity.token.expires_at,
        scopes=sorted(identity.token.scopes),
    )


@router.post("/sessions/{session_id}/revoke", response_model=SessionRevokeResponse)
def revoke_authentication_session(
    session_id: str,
    payload: SessionRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SessionRevokeResponse:
    identity: RequestIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    # A user may revoke only their current application session through this endpoint.
    # Tenant-wide administrative revocation will be introduced behind explicit
    # authorization permissions in the identity-administration API.
    if identity.application_session_id != session_id:
        raise HTTPException(status_code=403, detail="session does not belong to the current request")
    auth_service = request.app.state.authentication_service
    try:
        auth_session = AuthenticationSessionService(
            db, hmac_secret=auth_service.session_hmac_secret
        ).revoke(
            tenant_id=identity.principal.tenant_id,
            session_id=session_id,
            revoked_by_user_id=identity.principal.user_id,
            reason=payload.reason,
        )
        db.commit()
    except SessionSecurityError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SessionRevokeResponse(
        session_id=auth_session.session_id,
        revoked=auth_session.revoked_at is not None,
        revoked_at=auth_session.revoked_at,
    )

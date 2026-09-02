from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.authentication import AuthenticationSessionModel


class AuthenticationSessionRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def get(self, session_id: str) -> AuthenticationSessionModel | None:
        return self.session.scalar(
            select(AuthenticationSessionModel).where(
                AuthenticationSessionModel.session_id == session_id,
                AuthenticationSessionModel.tenant_id == self.tenant_id,
            )
        )

    def get_by_external_session(
        self,
        *,
        issuer: str,
        subject: str,
        external_session_hash: str,
    ) -> AuthenticationSessionModel | None:
        return self.session.scalar(
            select(AuthenticationSessionModel).where(
                AuthenticationSessionModel.tenant_id == self.tenant_id,
                AuthenticationSessionModel.issuer == issuer,
                AuthenticationSessionModel.subject == subject,
                AuthenticationSessionModel.external_session_hash == external_session_hash,
            )
        )

    def list_for_user(self, user_id: str) -> list[AuthenticationSessionModel]:
        return list(
            self.session.scalars(
                select(AuthenticationSessionModel)
                .where(
                    AuthenticationSessionModel.tenant_id == self.tenant_id,
                    AuthenticationSessionModel.user_id == user_id,
                )
                .order_by(AuthenticationSessionModel.created_at.desc())
            )
        )

    def add(self, auth_session: AuthenticationSessionModel) -> AuthenticationSessionModel:
        if auth_session.tenant_id != self.tenant_id:
            raise ValueError("authentication session tenant does not match repository tenant context")
        self.session.add(auth_session)
        self.session.flush()
        return auth_session

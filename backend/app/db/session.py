from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    session = get_session_factory()()
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        set_tenant_context(session, tenant_id)
    try:
        yield session
    finally:
        session.close()


def set_tenant_context(session: Session, tenant_id: str) -> None:
    """Set transaction-local tenant context used by PostgreSQL RLS policies.

    Repository methods still apply explicit tenant filters. PostgreSQL RLS is a
    second line of defense against accidental cross-tenant queries.
    """

    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )

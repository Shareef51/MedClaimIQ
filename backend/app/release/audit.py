from __future__ import annotations
import json, os
from datetime import datetime, timezone
from uuid import uuid4
from app.db.session import get_session_factory, set_tenant_context
from app.models.release_engineering import ReleaseManifestModel, DeploymentRecordModel, ReleaseGateResultModel
from sqlalchemy import select


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"missing required release audit environment: {name}")
    return value


def main() -> None:
    tenant_id = _env("RELEASE_AUDIT_TENANT_ID")
    release_id = _env("RELEASE_ID")
    env = _env("APP_ENV", "unknown")
    now = datetime.now(timezone.utc)
    session = get_session_factory()()
    try:
        set_tenant_context(session, tenant_id)
        manifest = session.scalar(select(ReleaseManifestModel).where(ReleaseManifestModel.tenant_id == tenant_id, ReleaseManifestModel.release_id == release_id))
        if manifest is None:
            manifest = ReleaseManifestModel(
                manifest_id=f"rel_{uuid4().hex}", tenant_id=tenant_id, release_id=release_id,
                git_sha=_env("RELEASE_GIT_SHA"), api_image_digest=_env("RELEASE_API_DIGEST"), frontend_image_digest=_env("RELEASE_FRONTEND_DIGEST"),
                alembic_head=_env("RELEASE_ALEMBIC_HEAD"), manifest_sha256=_env("RELEASE_MANIFEST_SHA256"), sbom_sha256=_env("RELEASE_SBOM_SHA256"), provenance_sha256=_env("RELEASE_PROVENANCE_SHA256"),
                gate_summary=json.loads(os.getenv("RELEASE_GATE_SUMMARY", "{}")), created_by=os.getenv("RELEASE_ACTOR", "gitops-release-controller"), released_at=now,
            )
            session.add(manifest)
        gate_summary=json.loads(os.getenv("RELEASE_GATE_SUMMARY", "{}"))
        for gate_name, status in sorted(gate_summary.items()):
            exists=session.scalar(select(ReleaseGateResultModel).where(ReleaseGateResultModel.tenant_id==tenant_id, ReleaseGateResultModel.release_id==release_id, ReleaseGateResultModel.gate_name==gate_name))
            if exists is None:
                session.add(ReleaseGateResultModel(gate_result_id=f"gate_{uuid4().hex}",tenant_id=tenant_id,release_id=release_id,gate_name=gate_name,status=str(status),evidence_sha256=_env("RELEASE_MANIFEST_SHA256"),source="immutable-release-manifest",evaluated_at=now))
        deployment = DeploymentRecordModel(
            deployment_id=f"dep_{uuid4().hex}", tenant_id=tenant_id, release_id=release_id, environment=env,
            strategy=os.getenv("RELEASE_STRATEGY", "canary"), status=os.getenv("RELEASE_DEPLOYMENT_STATUS", "deployed"),
            desired_state_sha=_env("RELEASE_DESIRED_STATE_SHA", _env("RELEASE_GIT_SHA")), argocd_application=os.getenv("ARGOCD_APPLICATION", f"medclaimiq-{env}"),
            initiated_by=os.getenv("RELEASE_ACTOR", "gitops-release-controller"), approved_by=os.getenv("RELEASE_APPROVED_BY") or None,
            rollback_release_id=os.getenv("RELEASE_ROLLBACK_RELEASE_ID") or None, rollback_triggered=os.getenv("RELEASE_ROLLBACK_TRIGGERED", "false").lower() == "true",
            started_at=now, completed_at=now, trace_id=os.getenv("TRACE_ID") or None,
            deployment_metadata={"controller":"argocd","immutable_images":True,"source":"helm-post-sync-audit"},
        )
        session.add(deployment); session.commit(); print(deployment.deployment_id)
    finally:
        session.close()

if __name__ == "__main__":
    main()

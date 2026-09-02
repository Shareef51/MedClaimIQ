from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.domain.knowledge_governance import (
    KnowledgeReleaseStatus, KnowledgeSourceStatus, KnowledgeVersionStatus, ProjectionTarget,
    ReindexAction, ReindexStatus, assess_knowledge_quality, assess_retrieval_drift, is_temporally_valid, sha256_json,
)
from app.models.knowledge_governance import (
    KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeGovernanceEventModel,
    KnowledgeIndexMigrationModel, KnowledgeQualityRunModel, KnowledgeReindexJobModel,
    KnowledgeReleaseItemModel, KnowledgeReleaseModel, KnowledgeRetrievalDriftModel, KnowledgeSourceModel,
)
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository


def knowledge_governance_model_contract() -> dict:
    return {
        "authority": "PostgreSQL knowledge lifecycle and release records are authoritative; Qdrant is a rebuildable projection",
        "source_lifecycle": [x.value for x in KnowledgeSourceStatus],
        "version_lifecycle": [x.value for x in KnowledgeVersionStatus],
        "release_lifecycle": [x.value for x in KnowledgeReleaseStatus],
        "reindex_actions": [x.value for x in ReindexAction],
        "controls": [
            "owner-and-authority-required", "immutable-version-content-hash", "independent-approval",
            "temporal-validity", "quality-before-release", "stale-vector-detection", "deletion-propagation",
            "embedding-index-migration", "retrieval-drift-blocking", "release-manifest-sha256",
        ],
        "retrieval_rule": "only promoted active temporally-valid knowledge versions may remain projected as active retrieval content",
    }


class KnowledgeGovernanceService:
    def __init__(self, repo: KnowledgeGovernanceRepository):
        self.repo = repo

    def _event(self, event_type: str, actor: str, subject_type: str, subject_id: str, details: dict):
        return self.repo.add(KnowledgeGovernanceEventModel(
            event_id=f"kgevt_{uuid4().hex}", tenant_id=self.repo.tenant_id, event_type=event_type,
            actor_user_id=actor, subject_type=subject_type, subject_id=subject_id,
            details=details, details_sha256=sha256_json(details),
        ))

    def onboard_source(self, *, actor: str, source_key: str, source_type: str, display_name: str,
                       owner_principal_id: str, owner_team: str | None, authority_rank: int, metadata: dict):
        if not owner_principal_id.strip():
            raise ValueError("knowledge source owner is required")
        if not 0 <= authority_rank <= 100:
            raise ValueError("authority_rank must be between 0 and 100")
        source = self.repo.add(KnowledgeSourceModel(
            source_id=f"ksrc_{uuid4().hex}", tenant_id=self.repo.tenant_id, source_key=source_key,
            source_type=source_type, display_name=display_name, owner_principal_id=owner_principal_id,
            owner_team=owner_team, authority_rank=authority_rank, status=KnowledgeSourceStatus.ACTIVE.value,
            onboarding_metadata=metadata, created_by=actor,
        ))
        self._event("knowledge.source.onboarded", actor, "source", source.source_id,
                    {"source_key": source_key, "source_type": source_type, "authority_rank": authority_rank})
        return source

    def create_document(self, *, actor: str, source_id: str, document_key: str, title: str, domain: str,
                        source_locator: str | None, metadata: dict):
        source = self.repo.source(source_id)
        if source is None or source.status != KnowledgeSourceStatus.ACTIVE.value:
            raise ValueError("active knowledge source required")
        doc = self.repo.add(KnowledgeDocumentModel(
            document_id=f"kdoc_{uuid4().hex}", tenant_id=self.repo.tenant_id, source_id=source_id,
            document_key=document_key, title=title, domain=domain, source_locator=source_locator,
            lifecycle_metadata=metadata, created_by=actor,
        ))
        self._event("knowledge.document.created", actor, "document", doc.document_id, {"source_id": source_id, "domain": domain})
        return doc

    def create_version(self, *, actor: str, document_id: str, version: str, content_sha256: str,
                       content_locator: str | None, rag_source_id: str, rag_source_version: str,
                       valid_from, valid_to, metadata: dict):
        if self.repo.document(document_id) is None:
            raise ValueError("knowledge document not found")
        if len(content_sha256) != 64:
            raise ValueError("content_sha256 must be a SHA-256 hex digest")
        if valid_from and valid_to and valid_to <= valid_from:
            raise ValueError("valid_to must be later than valid_from")
        item = self.repo.add(KnowledgeDocumentVersionModel(
            version_id=f"kver_{uuid4().hex}", tenant_id=self.repo.tenant_id, document_id=document_id,
            version=version, content_sha256=content_sha256.lower(), content_locator=content_locator,
            rag_source_id=rag_source_id, rag_source_version=rag_source_version,
            status=KnowledgeVersionStatus.DRAFT.value, valid_from=valid_from, valid_to=valid_to,
            version_metadata=metadata, created_by=actor,
        ))
        self._event("knowledge.version.created", actor, "version", item.version_id,
                    {"document_id": document_id, "version": version, "content_sha256": item.content_sha256})
        return item

    def submit_version(self, *, actor: str, version_id: str):
        item = self.repo.version(version_id)
        if item is None or item.status != KnowledgeVersionStatus.DRAFT.value:
            raise ValueError("only draft knowledge versions can be submitted")
        item.status = KnowledgeVersionStatus.IN_REVIEW.value
        item.submitted_by = actor
        self.repo.session.flush()
        self._event("knowledge.version.submitted", actor, "version", version_id, {})
        return item

    def run_quality(self, *, actor: str, version_id: str, citation_coverage: float):
        version = self.repo.version(version_id)
        if version is None:
            raise ValueError("knowledge version not found")
        document = self.repo.document(version.document_id)
        source = self.repo.source(document.source_id) if document else None
        metadata = {**(document.lifecycle_metadata if document else {}), **version.version_metadata,
                    "title": document.title if document else None, "source_type": source.source_type if source else None}
        result = assess_knowledge_quality(
            owner_present=bool(source and source.owner_principal_id), authority_rank=source.authority_rank if source else 0,
            content_sha256=version.content_sha256, metadata=metadata, citation_coverage=citation_coverage,
            valid_from=version.valid_from, valid_to=version.valid_to,
        )
        evidence = {"version_id": version_id, "checks": result.checks, "citation_coverage": citation_coverage}
        run = self.repo.add(KnowledgeQualityRunModel(
            quality_run_id=f"kqr_{uuid4().hex}", tenant_id=self.repo.tenant_id, version_id=version_id,
            score=result.score, passed=result.passed, checks=result.checks, reasons=list(result.reasons),
            citation_coverage=citation_coverage, evaluated_by=actor, evidence_sha256=sha256_json(evidence),
        ))
        self._event("knowledge.quality.evaluated", actor, "version", version_id,
                    {"quality_run_id": run.quality_run_id, "score": run.score, "passed": run.passed})
        return run

    def approve_version(self, *, actor: str, version_id: str, reason: str):
        item = self.repo.version(version_id)
        if item is None or item.status != KnowledgeVersionStatus.IN_REVIEW.value:
            raise ValueError("knowledge version is not awaiting review")
        if actor in {item.created_by, item.submitted_by}:
            raise ValueError("knowledge author/submitter cannot self-approve")
        quality = self.repo.latest_quality(version_id)
        if quality is None or not quality.passed:
            raise ValueError("passing knowledge quality evaluation required")
        item.status = KnowledgeVersionStatus.APPROVED.value
        item.approved_by = actor
        item.approved_at = datetime.now(UTC)
        self.repo.session.flush()
        self._event("knowledge.version.approved", actor, "version", version_id, {"reason_sha256": sha256(reason.encode()).hexdigest()})
        return item

    def request_reindex(self, *, actor: str, version_id: str, action: str, embedding_model: str,
                        embedding_dimensions: int, index_version: str, migration_id: str | None = None):
        version = self.repo.version(version_id)
        if version is None:
            raise ValueError("knowledge version not found")
        target = ProjectionTarget(embedding_model, embedding_dimensions, index_version)
        stale = self.repo.stale_chunk_ids(version, embedding_model=embedding_model,
                                           embedding_dimensions=embedding_dimensions, index_version=index_version)
        key = sha256_json({"version_id": version_id, "action": action, "target": target.fingerprint(),
                           "content": version.content_sha256, "migration_id": migration_id})
        existing = self.repo.reindex_job_by_key(key)
        if existing:
            return existing
        job = self.repo.add(KnowledgeReindexJobModel(
            job_id=f"krj_{uuid4().hex}", tenant_id=self.repo.tenant_id, version_id=version_id, migration_id=migration_id,
            action=ReindexAction(action).value, status=ReindexStatus.PENDING.value,
            embedding_model=embedding_model, embedding_dimensions=embedding_dimensions, index_version=index_version,
            projection_fingerprint=target.fingerprint(), idempotency_key=key, stale_chunk_count=len(stale),
            requested_by=actor,
        ))
        self._event("knowledge.reindex.requested", actor, "reindex_job", job.job_id,
                    {"version_id": version_id, "action": action, "stale_chunk_count": len(stale), "target": target.fingerprint()})
        return job

    def scan_stale_vectors(self, *, actor: str, embedding_model: str, embedding_dimensions: int, index_version: str) -> dict:
        stale: list[dict] = []
        expired: list[str] = []
        now = datetime.now(UTC)
        for version in self.repo.active_versions():
            if not is_temporally_valid(valid_from=version.valid_from, valid_to=version.valid_to, at=now):
                version.status = KnowledgeVersionStatus.RETIRED.value
                version.retired_at = now
                expired.append(version.version_id)
                self.request_reindex(actor=actor, version_id=version.version_id, action="delete",
                                     embedding_model=embedding_model, embedding_dimensions=embedding_dimensions,
                                     index_version=index_version)
                continue
            ids = self.repo.stale_chunk_ids(version, embedding_model=embedding_model,
                                            embedding_dimensions=embedding_dimensions, index_version=index_version)
            if ids:
                stale.append({"version_id": version.version_id, "stale_chunk_count": len(ids)})
                self.request_reindex(actor=actor, version_id=version.version_id, action="incremental",
                                     embedding_model=embedding_model, embedding_dimensions=embedding_dimensions,
                                     index_version=index_version)
        self.repo.session.flush()
        self._event("knowledge.projection.stale_scan", actor, "projection", index_version,
                    {"stale_versions": len(stale), "stale_chunks": sum(x["stale_chunk_count"] for x in stale),
                     "temporally_expired_versions": len(expired)})
        return {"stale_versions": stale, "expired_versions": expired, "count": len(stale), "expired_count": len(expired)}

    def create_index_migration(self, *, actor: str, from_embedding_model: str, from_dimensions: int,
                               from_index_version: str, to_embedding_model: str, to_dimensions: int,
                               to_index_version: str):
        if (from_embedding_model, from_dimensions, from_index_version) == (to_embedding_model, to_dimensions, to_index_version):
            raise ValueError("index migration target must differ from source")
        if (from_embedding_model, from_dimensions) != (to_embedding_model, to_dimensions) and from_index_version == to_index_version:
            raise ValueError("embedding model/dimension changes require a new index_version and isolated vector collection")
        item = self.repo.add(KnowledgeIndexMigrationModel(
            migration_id=f"kim_{uuid4().hex}", tenant_id=self.repo.tenant_id,
            from_embedding_model=from_embedding_model, from_dimensions=from_dimensions, from_index_version=from_index_version,
            to_embedding_model=to_embedding_model, to_dimensions=to_dimensions, to_index_version=to_index_version,
            status="pending_approval", requested_by=actor,
        ))
        self._event("knowledge.index_migration.requested", actor, "index_migration", item.migration_id,
                    {"from": [from_embedding_model, from_dimensions, from_index_version], "to": [to_embedding_model, to_dimensions, to_index_version]})
        return item

    def approve_index_migration(self, *, actor: str, migration_id: str):
        migration = self.repo.index_migration(migration_id)
        if migration is None or migration.status != "pending_approval":
            raise ValueError("index migration is not awaiting approval")
        if actor == migration.requested_by:
            raise ValueError("index migration requester cannot self-approve")
        migration.status = "running"
        migration.approved_by = actor
        migration.started_at = datetime.now(UTC)
        queued = 0
        for version in self.repo.active_versions():
            self.request_reindex(
                actor=actor, version_id=version.version_id, action="migrate",
                embedding_model=migration.to_embedding_model, embedding_dimensions=migration.to_dimensions,
                index_version=migration.to_index_version, migration_id=migration_id,
            )
            queued += 1
        self.repo.session.flush()
        self._event("knowledge.index_migration.started", actor, "index_migration", migration_id, {"queued_versions": queued})
        return migration, queued

    def refresh_index_migration(self, *, actor: str, migration_id: str):
        migration = self.repo.index_migration(migration_id)
        if migration is None or migration.status not in {"running", "failed"}:
            raise ValueError("index migration is not running")
        jobs = self.repo.migration_jobs(migration_id)
        if jobs and any(job.status == ReindexStatus.DEAD_LETTER.value for job in jobs):
            migration.status = "failed"
        elif jobs and all(job.status == ReindexStatus.COMPLETED.value for job in jobs):
            migration.status = "completed"
            migration.completed_at = datetime.now(UTC)
        self.repo.session.flush()
        self._event("knowledge.index_migration.refreshed", actor, "index_migration", migration_id,
                    {"status": migration.status, "job_count": len(jobs)})
        return migration

    def evaluate_retrieval_drift(self, *, actor: str, release_id: str | None, baseline_metrics: dict, observed_metrics: dict):
        result = assess_retrieval_drift(
            baseline_recall=float(baseline_metrics["recall"]), observed_recall=float(observed_metrics["recall"]),
            baseline_precision=float(baseline_metrics["precision"]), observed_precision=float(observed_metrics["precision"]),
            baseline_ndcg=float(baseline_metrics["ndcg"]), observed_ndcg=float(observed_metrics["ndcg"]),
            baseline_no_evidence_rate=float(baseline_metrics["no_evidence_rate"]),
            observed_no_evidence_rate=float(observed_metrics["no_evidence_rate"]),
        )
        deltas = {"recall": result.recall_delta, "precision": result.precision_delta, "ndcg": result.ndcg_delta,
                  "no_evidence_rate": result.no_evidence_delta}
        evidence = {"baseline": baseline_metrics, "observed": observed_metrics, "deltas": deltas, "reasons": result.reasons}
        event = self.repo.add(KnowledgeRetrievalDriftModel(
            drift_event_id=f"kdrift_{uuid4().hex}", tenant_id=self.repo.tenant_id, release_id=release_id,
            severity=result.severity.value, blocking=result.blocking, baseline_metrics=baseline_metrics,
            observed_metrics=observed_metrics, deltas=deltas, reasons=list(result.reasons),
            evidence_sha256=sha256_json(evidence), evaluated_by=actor,
        ))
        if result.blocking:
            self._event("knowledge.retrieval_drift.blocked", actor, "retrieval_drift", event.drift_event_id,
                        {"severity": event.severity, "reasons": event.reasons})
        return event

    def create_release(self, *, actor: str, release_key: str, release_version: str, version_ids: list[str]):
        unique_ids = list(dict.fromkeys(version_ids))
        if not unique_ids:
            raise ValueError("knowledge release must contain at least one version")
        versions = []
        for version_id in unique_ids:
            version = self.repo.version(version_id)
            if version is None or version.status != KnowledgeVersionStatus.APPROVED.value:
                raise ValueError("all release versions must be approved")
            quality = self.repo.latest_quality(version_id)
            if quality is None or not quality.passed:
                raise ValueError("all release versions require a passing quality run")
            versions.append(version)
        manifest = {"release_key": release_key, "release_version": release_version,
                    "versions": sorted([{"version_id": x.version_id, "document_id": x.document_id,
                                         "content_sha256": x.content_sha256, "valid_from": x.valid_from,
                                         "valid_to": x.valid_to} for x in versions], key=lambda x: x["version_id"])}
        release = self.repo.add(KnowledgeReleaseModel(
            release_id=f"krel_{uuid4().hex}", tenant_id=self.repo.tenant_id, release_key=release_key,
            release_version=release_version, status=KnowledgeReleaseStatus.PENDING_APPROVAL.value,
            manifest=manifest, manifest_sha256=sha256_json(manifest), requested_by=actor,
        ))
        for version in versions:
            self.repo.add(KnowledgeReleaseItemModel(
                release_item_id=f"krli_{uuid4().hex}", tenant_id=self.repo.tenant_id, release_id=release.release_id,
                version_id=version.version_id, document_id=version.document_id, content_sha256=version.content_sha256,
            ))
        self._event("knowledge.release.requested", actor, "release", release.release_id,
                    {"release_version": release_version, "manifest_sha256": release.manifest_sha256, "version_count": len(versions)})
        return release

    def promote_release(self, *, actor: str, release_id: str, reason: str,
                        embedding_model: str, embedding_dimensions: int, index_version: str):
        release = self.repo.release(release_id)
        if release is None or release.status != KnowledgeReleaseStatus.PENDING_APPROVAL.value:
            raise ValueError("knowledge release is not awaiting approval")
        if actor == release.requested_by:
            raise ValueError("knowledge release requester cannot self-approve")
        blocking_drift = self.repo.latest_blocking_drift()
        if blocking_drift and blocking_drift.created_at >= release.created_at:
            raise ValueError("blocking retrieval drift must be resolved before promotion")
        now = datetime.now(UTC)
        for item in self.repo.release_items(release_id):
            version = self.repo.version(item.version_id)
            if version is None or version.status != KnowledgeVersionStatus.APPROVED.value:
                raise ValueError("release contains a version that is no longer approved")
            if not is_temporally_valid(valid_from=version.valid_from, valid_to=version.valid_to, at=now):
                raise ValueError("release contains a version outside its temporal validity window")
        release.status = KnowledgeReleaseStatus.PROMOTED.value
        release.approved_by = actor
        release.approval_reason = reason
        release.promoted_at = now
        for item in self.repo.release_items(release_id):
            version = self.repo.version(item.version_id)
            retired = self.repo.retire_other_versions(version.document_id, version.version_id, now)
            for retired_id in retired:
                self.request_reindex(actor=actor, version_id=retired_id, action="delete",
                                     embedding_model=embedding_model, embedding_dimensions=embedding_dimensions,
                                     index_version=index_version)
            version.status = KnowledgeVersionStatus.ACTIVE.value
            version.activated_at = now
            self.request_reindex(actor=actor, version_id=version.version_id, action="full",
                                 embedding_model=embedding_model, embedding_dimensions=embedding_dimensions,
                                 index_version=index_version)
        self.repo.session.flush()
        self._event("knowledge.release.promoted", actor, "release", release_id,
                    {"manifest_sha256": release.manifest_sha256, "reason_sha256": sha256(reason.encode()).hexdigest()})
        return release

    def retire_version(self, *, actor: str, version_id: str, reason: str,
                       embedding_model: str, embedding_dimensions: int, index_version: str):
        version = self.repo.version(version_id)
        if version is None or version.status not in {KnowledgeVersionStatus.ACTIVE.value, KnowledgeVersionStatus.APPROVED.value}:
            raise ValueError("knowledge version cannot be retired from current state")
        version.status = KnowledgeVersionStatus.RETIRED.value
        version.retired_at = datetime.now(UTC)
        self.repo.session.flush()
        job = self.request_reindex(actor=actor, version_id=version_id, action="delete",
                                   embedding_model=embedding_model, embedding_dimensions=embedding_dimensions,
                                   index_version=index_version)
        self._event("knowledge.version.retired", actor, "version", version_id,
                    {"reason_sha256": sha256(reason.encode()).hexdigest(), "delete_job_id": job.job_id})
        return version, job

    def history(self, limit: int = 50) -> dict:
        return {
            "sources": [{"source_id": x.source_id, "source_key": x.source_key, "status": x.status,
                         "authority_rank": x.authority_rank, "owner_principal_id": x.owner_principal_id} for x in self.repo.sources(limit)],
            "releases": [{"release_id": x.release_id, "release_key": x.release_key, "release_version": x.release_version,
                          "status": x.status, "manifest_sha256": x.manifest_sha256} for x in self.repo.releases(limit)],
            "quality": [{"quality_run_id": x.quality_run_id, "version_id": x.version_id,
                         "score": x.score, "passed": x.passed} for x in self.repo.quality_runs(limit)],
            "drift": [{"drift_event_id": x.drift_event_id, "severity": x.severity,
                        "blocking": x.blocking, "reasons": x.reasons} for x in self.repo.drift_events(limit)],
            "events": [{"event_id": x.event_id, "event_type": x.event_type, "subject_id": x.subject_id,
                         "details_sha256": x.details_sha256} for x in self.repo.events(limit * 2)],
        }

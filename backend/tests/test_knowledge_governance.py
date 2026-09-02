from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.domain.knowledge_governance import (
    ProjectionTarget, assess_knowledge_quality, assess_retrieval_drift, is_temporally_valid,
)
from app.services.knowledge_governance import KnowledgeGovernanceService, knowledge_governance_model_contract


class FakeSession:
    def flush(self):
        return None


class FakeRepo:
    def __init__(self):
        self.tenant_id = "tenant_demo"
        self.session = FakeSession()
        self._sources = {}
        self._documents = {}
        self._versions = {}
        self._quality = {}
        self._jobs = {}
        self._releases = {}
        self._release_items = {}
        self._migrations = {}
        self._drifts = []
        self._events = []

    def add(self, model):
        name = type(model).__name__
        if name == "KnowledgeSourceModel": self._sources[model.source_id] = model
        elif name == "KnowledgeDocumentModel": self._documents[model.document_id] = model
        elif name == "KnowledgeDocumentVersionModel": self._versions[model.version_id] = model
        elif name == "KnowledgeQualityRunModel": self._quality.setdefault(model.version_id, []).append(model)
        elif name == "KnowledgeReindexJobModel": self._jobs[model.idempotency_key] = model
        elif name == "KnowledgeReleaseModel": self._releases[model.release_id] = model
        elif name == "KnowledgeIndexMigrationModel": self._migrations[model.migration_id] = model
        elif name == "KnowledgeReleaseItemModel": self._release_items.setdefault(model.release_id, []).append(model)
        elif name == "KnowledgeRetrievalDriftModel": self._drifts.append(model)
        elif name == "KnowledgeGovernanceEventModel": self._events.append(model)
        return model

    def source(self, source_id): return self._sources.get(source_id)
    def document(self, document_id): return self._documents.get(document_id)
    def version(self, version_id): return self._versions.get(version_id)
    def latest_quality(self, version_id):
        values = self._quality.get(version_id, [])
        return values[-1] if values else None
    def stale_chunk_ids(self, version, **kwargs): return ["chunk-1", "chunk-2"]
    def reindex_job_by_key(self, key): return self._jobs.get(key)
    def index_migration(self, migration_id): return self._migrations.get(migration_id)
    def migration_jobs(self, migration_id): return [x for x in self._jobs.values() if getattr(x, "migration_id", None) == migration_id]
    def active_versions(self): return [v for v in self._versions.values() if v.status == "active"]
    def release(self, release_id): return self._releases.get(release_id)
    def release_items(self, release_id): return self._release_items.get(release_id, [])
    def latest_blocking_drift(self):
        return next((x for x in reversed(self._drifts) if x.blocking), None)
    def retire_other_versions(self, document_id, keep_version_id, retired_at):
        retired = []
        for item in self._versions.values():
            if item.document_id == document_id and item.version_id != keep_version_id and item.status == "active":
                item.status = "retired"; item.retired_at = retired_at; retired.append(item.version_id)
        return retired
    def sources(self, limit=100): return list(self._sources.values())[-limit:]
    def releases(self, limit=100): return list(self._releases.values())[-limit:]
    def quality_runs(self, limit=100): return [x for xs in self._quality.values() for x in xs][-limit:]
    def drift_events(self, limit=100): return self._drifts[-limit:]
    def events(self, limit=100): return self._events[-limit:]


def _make_approved_version(service: KnowledgeGovernanceService, repo: FakeRepo, *, creator="author"):
    source = service.onboard_source(actor=creator, source_key="policy-lib", source_type="policy", display_name="Policy Library",
                                    owner_principal_id="owner-1", owner_team="policy", authority_rank=90, metadata={})
    doc = service.create_document(actor=creator, source_id=source.source_id, document_key="coverage", title="Coverage Policy",
                                  domain="policy", source_locator="s3://synthetic/policy", metadata={})
    version = service.create_version(actor=creator, document_id=doc.document_id, version="2", content_sha256="a"*64,
                                     content_locator="s3://synthetic/policy-v2", rag_source_id="evidence-policy",
                                     rag_source_version="2", valid_from=datetime.now(UTC)-timedelta(days=1),
                                     valid_to=datetime.now(UTC)+timedelta(days=30), metadata={})
    service.submit_version(actor=creator, version_id=version.version_id)
    quality = service.run_quality(actor="quality-bot", version_id=version.version_id, citation_coverage=1.0)
    assert quality.passed
    service.approve_version(actor="approver", version_id=version.version_id, reason="verified synthetic policy")
    return version


def test_quality_gate_requires_owner_authority_metadata_hash_and_citations():
    result = assess_knowledge_quality(owner_present=True, authority_rank=90, content_sha256="a"*64,
                                      metadata={"title":"Policy", "source_type":"policy"}, citation_coverage=.98,
                                      valid_from=None, valid_to=None)
    assert result.passed and result.score == 1.0
    bad = assess_knowledge_quality(owner_present=False, authority_rank=10, content_sha256="bad",
                                   metadata={}, citation_coverage=.4, valid_from=None, valid_to=None)
    assert not bad.passed and "citation_coverage" in bad.reasons


def test_temporal_validity_is_half_open_window():
    now = datetime.now(UTC)
    assert is_temporally_valid(valid_from=now-timedelta(seconds=1), valid_to=now+timedelta(seconds=1), at=now)
    assert not is_temporally_valid(valid_from=now+timedelta(seconds=1), valid_to=None, at=now)
    assert not is_temporally_valid(valid_from=None, valid_to=now, at=now)


def test_retrieval_drift_blocks_material_quality_regression():
    result = assess_retrieval_drift(baseline_recall=.94, observed_recall=.86, baseline_precision=.82, observed_precision=.80,
                                    baseline_ndcg=.90, observed_ndcg=.82, baseline_no_evidence_rate=.04, observed_no_evidence_rate=.09)
    assert result.blocking
    assert result.severity.value == "critical"
    assert "recall_regression" in result.reasons


def test_projection_target_fingerprint_changes_for_embedding_migration():
    assert ProjectionTarget("embed", 1536, "v1").fingerprint() != ProjectionTarget("embed", 3072, "v2").fingerprint()


def test_author_cannot_self_approve_version():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    source = service.onboard_source(actor="author", source_key="x-source", source_type="policy", display_name="X",
                                    owner_principal_id="owner", owner_team=None, authority_rank=90, metadata={})
    doc = service.create_document(actor="author", source_id=source.source_id, document_key="x-doc", title="X policy",
                                  domain="policy", source_locator=None, metadata={})
    version = service.create_version(actor="author", document_id=doc.document_id, version="1", content_sha256="a"*64,
                                     content_locator=None, rag_source_id="src", rag_source_version="1",
                                     valid_from=None, valid_to=None, metadata={})
    service.submit_version(actor="author", version_id=version.version_id)
    service.run_quality(actor="quality", version_id=version.version_id, citation_coverage=1.0)
    with pytest.raises(ValueError, match="self-approve"):
        service.approve_version(actor="author", version_id=version.version_id, reason="no")


def test_reindex_request_is_idempotent_and_records_stale_count():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    version = _make_approved_version(service, repo)
    first = service.request_reindex(actor="admin", version_id=version.version_id, action="incremental",
                                    embedding_model="embed", embedding_dimensions=1536, index_version="v2")
    second = service.request_reindex(actor="admin", version_id=version.version_id, action="incremental",
                                     embedding_model="embed", embedding_dimensions=1536, index_version="v2")
    assert first is second
    assert first.stale_chunk_count == 2


def test_release_requester_cannot_self_promote_and_temporal_window_is_enforced():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    version = _make_approved_version(service, repo, creator="author")
    release = service.create_release(actor="release-owner", release_key="policies", release_version="2026.08", version_ids=[version.version_id])
    with pytest.raises(ValueError, match="self-approve"):
        service.promote_release(actor="release-owner", release_id=release.release_id, reason="same person",
                                embedding_model="embed", embedding_dimensions=1536, index_version="v2")
    version.valid_from = datetime.now(UTC) + timedelta(days=1)
    with pytest.raises(ValueError, match="temporal"):
        service.promote_release(actor="independent", release_id=release.release_id, reason="approve",
                                embedding_model="embed", embedding_dimensions=1536, index_version="v2")


def test_release_promotion_activates_exact_version_and_queues_full_reindex():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    version = _make_approved_version(service, repo)
    release = service.create_release(actor="release-owner", release_key="policies", release_version="2026.08.1", version_ids=[version.version_id])
    promoted = service.promote_release(actor="independent", release_id=release.release_id, reason="quality passed",
                                       embedding_model="embed", embedding_dimensions=1536, index_version="v2")
    assert promoted.status == "promoted"
    assert version.status == "active"
    assert any(job.action == "full" for job in repo._jobs.values())


def test_model_contract_states_vector_store_is_not_authority():
    contract = knowledge_governance_model_contract()
    assert "Qdrant is a rebuildable projection" in contract["authority"]
    assert "deletion-propagation" in contract["controls"]


def test_release_policy_requires_knowledge_governance_gate():
    import json
    from pathlib import Path
    policy = json.loads(Path("../config/release_engineering_policy.json").read_text())
    assert "knowledge-governance" in policy["gates"]["required"]
    workflow = Path("../.github/workflows/release-promotion.yml").read_text()
    assert "verify_knowledge_governance.py" in workflow
    assert "knowledge-governance=pass" in workflow


def test_rag_repository_filters_retired_governed_version_but_keeps_legacy_content():
    from types import SimpleNamespace
    from app.repositories.rag import RAGRepository
    class S:
        def scalars(self, statement):
            return [SimpleNamespace(rag_source_id="policy-source", rag_source_version="1", status="retired", valid_from=None, valid_to=None)]
    repo = RAGRepository(S(), tenant_id="tenant_demo")
    retired = SimpleNamespace(metadata={"source_id":"policy-source", "source_version":"1"})
    legacy = SimpleNamespace(metadata={"source_id":"claim-evidence", "source_version":"7"})
    assert repo.filter_governed_retrieval_hits([retired, legacy]) == [legacy]


def test_embedding_index_migration_requires_independent_approval_and_queues_active_versions():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    version = _make_approved_version(service, repo)
    version.status = "active"
    migration = service.create_index_migration(
        actor="migration-owner", from_embedding_model="embed-a", from_dimensions=1536, from_index_version="v2",
        to_embedding_model="embed-b", to_dimensions=3072, to_index_version="v3",
    )
    with pytest.raises(ValueError, match="self-approve"):
        service.approve_index_migration(actor="migration-owner", migration_id=migration.migration_id)
    migration, queued = service.approve_index_migration(actor="platform-approver", migration_id=migration.migration_id)
    assert migration.status == "running" and queued == 1
    assert any(job.action == "migrate" and job.migration_id == migration.migration_id for job in repo._jobs.values())


def test_embedding_dimension_change_requires_new_index_version_collection():
    repo = FakeRepo(); service = KnowledgeGovernanceService(repo)
    with pytest.raises(ValueError, match="new index_version"):
        service.create_index_migration(
            actor="platform", from_embedding_model="embed", from_dimensions=1536, from_index_version="rag-v2",
            to_embedding_model="embed", to_dimensions=3072, to_index_version="rag-v2",
        )

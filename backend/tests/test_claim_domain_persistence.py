from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.access import TenantType, UserRole
from app.domain.claims import ActorType, ClaimStatus, EvidenceSourceType, HumanDecision
from app.repositories.claims import (
    AuditEventRepository,
    ClaimRepository,
    ClaimStatusEventRepository,
    EvidenceLineageRepository,
    EvidenceRepository,
    HumanDecisionRepository,
)
from app.schemas.claims import (
    ClaimCreate,
    ClaimLineCreate,
    ClaimTransitionRequest,
    EncounterCreate,
    EvidenceCreate,
    EvidenceLineageCreate,
    HumanDecisionCreate,
    PatientCreate,
    PolicyCreate,
    ProviderCreate,
)
from app.schemas.tenancy import MembershipCreate, OrganizationCreate, TenantCreate, UserAccountCreate
from app.services.claims import ClaimDomainInvariantError, ClaimDomainService
from app.services.tenancy import TenancyService


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    Base.metadata.drop_all(engine)


def bootstrap_tenant(session: Session, tenant_id: str, *, reviewer_id: str | None = None) -> None:
    tenancy = TenancyService(session)
    tenancy.create_tenant(
        TenantCreate(
            tenant_id=tenant_id,
            slug=tenant_id,
            display_name=tenant_id,
            tenant_type=TenantType.DEMO,
        )
    )
    tenancy.create_organization(
        tenant_id,
        OrganizationCreate(
            organization_id=f"{tenant_id}-payer",
            slug="payer-ops",
            display_name="Synthetic Payer",
            organization_type="payer",
        ),
    )
    tenancy.create_organization(
        tenant_id,
        OrganizationCreate(
            organization_id=f"{tenant_id}-provider",
            slug="provider-network",
            display_name="Synthetic Hospital",
            organization_type="hospital",
        ),
    )
    if reviewer_id:
        tenancy.create_user(
            UserAccountCreate(
                user_id=reviewer_id,
                external_subject=f"oidc|{reviewer_id}",
                display_name="Synthetic Reviewer",
                status="active",
            )
        )
        tenancy.add_membership(
            tenant_id,
            MembershipCreate(
                membership_id=f"membership-{reviewer_id}",
                user_id=reviewer_id,
                role=UserRole.CLAIMS_REVIEWER,
            ),
        )


def bootstrap_claim_domain(
    session: Session, tenant_id: str = "tenant-claim-a", *, reviewer_id: str = "reviewer-001"
) -> ClaimDomainService:
    bootstrap_tenant(session, tenant_id, reviewer_id=reviewer_id)
    service = ClaimDomainService(session, tenant_id)
    service.create_patient(
        PatientCreate(
            patient_id=f"{tenant_id}-patient",
            patient_subject_id=f"{tenant_id}-subject",
            external_identifiers={"member_ref": "SYNTHETIC-MEMBER-001"},
        )
    )
    service.create_provider(
        ProviderCreate(
            provider_id=f"{tenant_id}-provider-record",
            organization_id=f"{tenant_id}-provider",
            provider_ref="SYNTHETIC-PROVIDER-001",
        )
    )
    service.create_policy(
        PolicyCreate(
            policy_id=f"{tenant_id}-policy",
            patient_subject_id=f"{tenant_id}-subject",
            payer_organization_id=f"{tenant_id}-payer",
            policy_ref="SYNTHETIC-POLICY-001",
            plan_name="Synthetic Gold Plan",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
    )
    service.create_encounter(
        EncounterCreate(
            encounter_id=f"{tenant_id}-encounter",
            patient_subject_id=f"{tenant_id}-subject",
            provider_organization_id=f"{tenant_id}-provider",
            encounter_ref="SYNTHETIC-ENCOUNTER-001",
            encounter_type="outpatient",
            started_at=datetime(2026, 8, 15, 8, tzinfo=timezone.utc),
            ended_at=datetime(2026, 8, 15, 10, tzinfo=timezone.utc),
        )
    )
    service.create_claim(
        ClaimCreate(
            claim_id=f"{tenant_id}-claim",
            external_claim_ref="SYNTHETIC-CLAIM-001",
            patient_subject_id=f"{tenant_id}-subject",
            provider_organization_id=f"{tenant_id}-provider",
            payer_organization_id=f"{tenant_id}-payer",
            policy_id=f"{tenant_id}-policy",
            encounter_id=f"{tenant_id}-encounter",
            assigned_reviewer_user_id=reviewer_id,
            total_amount=Decimal("250.00"),
            service_from=date(2026, 8, 15),
            service_to=date(2026, 8, 15),
            created_by_actor_type=ActorType.SYSTEM,
            created_by_actor_id="claim-intake",
            idempotency_key=f"create-{tenant_id}-claim",
            trace_id=f"trace-{tenant_id}",
        )
    )
    return service


def evidence_payload(tenant_id: str, evidence_id: str, char: str, *, document_type: str = "medical_bill") -> EvidenceCreate:
    return EvidenceCreate(
        evidence_id=evidence_id,
        claim_id=f"{tenant_id}-claim",
        source_type=EvidenceSourceType.SYNTHETIC_FIXTURE,
        source_system="synthetic-fixture-generator",
        source_locator={"fixture": f"{evidence_id}.pdf", "page": 1},
        document_type=document_type,
        media_type="application/pdf",
        object_key=f"synthetic/{tenant_id}/{evidence_id}.pdf",
        content_sha256=char * 64,
        byte_size=1024,
        actor_type=ActorType.SYSTEM,
        actor_id="evidence-intake",
        idempotency_key=f"ingest-{evidence_id}",
    )


def transition(service: ClaimDomainService, claim_id: str, status: ClaimStatus, version: int) -> None:
    service.transition_claim(
        claim_id,
        ClaimTransitionRequest(
            status_event_id=f"evt-{version}-{status.value}",
            to_status=status,
            actor_type=ActorType.WORKER,
            actor_id="workflow-worker",
            reason=f"advance to {status.value}",
            idempotency_key=f"transition-{version}-{status.value}",
            expected_status_version=version,
        ),
    )


def advance_to_human_review(service: ClaimDomainService, claim_id: str) -> None:
    sequence = (
        ClaimStatus.QUARANTINED,
        ClaimStatus.EXTRACTING,
        ClaimStatus.NORMALIZING,
        ClaimStatus.VERIFYING,
        ClaimStatus.AI_REVIEWED,
        ClaimStatus.HUMAN_REVIEW,
    )
    version = 1
    for status in sequence:
        transition(service, claim_id, status, version)
        version += 1


def test_persists_claim_relations_lines_and_audit(session: Session) -> None:
    tenant_id = "tenant-claim-a"
    service = bootstrap_claim_domain(session, tenant_id)
    line = service.add_claim_line(
        f"{tenant_id}-claim",
        ClaimLineCreate(
            claim_line_id="line-001",
            line_number=1,
            code_system="CPT",
            service_code="99213",
            service_date=date(2026, 8, 15),
            units=Decimal("1"),
            amount=Decimal("250.00"),
            provider_id=f"{tenant_id}-provider-record",
        ),
    )

    claim = ClaimRepository(session, tenant_id).get(f"{tenant_id}-claim")
    audits = AuditEventRepository(session, tenant_id).list_for_resource(
        "claim", f"{tenant_id}-claim"
    )

    assert claim is not None
    assert claim.policy_id == f"{tenant_id}-policy"
    assert claim.encounter_id == f"{tenant_id}-encounter"
    assert line.claim_id == claim.claim_id
    assert [event.action for event in audits] == ["claim.created"]


def test_claim_repository_cannot_read_other_tenant_claim(session: Session) -> None:
    service = bootstrap_claim_domain(session, "tenant-claim-a")
    bootstrap_tenant(session, "tenant-claim-b")

    assert service.claims.get("tenant-claim-a-claim") is not None
    assert ClaimRepository(session, "tenant-claim-b").get("tenant-claim-a-claim") is None


def test_claim_rejects_policy_outside_service_date(session: Session) -> None:
    tenant_id = "tenant-date"
    bootstrap_tenant(session, tenant_id, reviewer_id="reviewer-date")
    service = ClaimDomainService(session, tenant_id)
    service.create_patient(
        PatientCreate(patient_id="patient-date", patient_subject_id="subject-date")
    )
    service.create_policy(
        PolicyCreate(
            policy_id="policy-date",
            patient_subject_id="subject-date",
            payer_organization_id=f"{tenant_id}-payer",
            policy_ref="POL-DATE",
            plan_name="Expired Plan",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 1, 31),
        )
    )

    with pytest.raises(ClaimDomainInvariantError, match="outside policy effective window"):
        service.create_claim(
            ClaimCreate(
                claim_id="claim-date",
                external_claim_ref="CLAIM-DATE",
                patient_subject_id="subject-date",
                provider_organization_id=f"{tenant_id}-provider",
                payer_organization_id=f"{tenant_id}-payer",
                policy_id="policy-date",
                total_amount=Decimal("10.00"),
                service_from=date(2026, 8, 1),
                created_by_actor_id="intake",
                idempotency_key="create-claim-date",
            )
        )


def test_evidence_deduplicates_by_claim_hash_and_preserves_lineage(session: Session) -> None:
    tenant_id = "tenant-evidence"
    service = bootstrap_claim_domain(session, tenant_id)
    parent = service.add_evidence(evidence_payload(tenant_id, "evidence-original", "a"))
    duplicate = service.add_evidence(evidence_payload(tenant_id, "evidence-duplicate", "a"))
    child = service.add_evidence(
        evidence_payload(tenant_id, "evidence-extracted", "b", document_type="extracted_text")
    )
    edge = service.add_evidence_lineage(
        EvidenceLineageCreate(
            lineage_id="lineage-001",
            child_evidence_id=child.evidence_id,
            parent_evidence_id=parent.evidence_id,
            transformation_name="docling-extract",
            transformation_version="1.0",
            transformation_metadata={"page_count": 2},
        )
    )

    assert duplicate.evidence_id == parent.evidence_id
    assert len(EvidenceRepository(session, tenant_id).list_for_claim(f"{tenant_id}-claim")) == 2
    assert edge.claim_id == f"{tenant_id}-claim"
    assert len(EvidenceLineageRepository(session, tenant_id).list_for_evidence(child.evidence_id)) == 1


def test_transition_is_validated_versioned_and_idempotent(session: Session) -> None:
    tenant_id = "tenant-transition"
    service = bootstrap_claim_domain(session, tenant_id)
    claim_id = f"{tenant_id}-claim"
    payload = ClaimTransitionRequest(
        status_event_id="status-quarantine",
        to_status=ClaimStatus.QUARANTINED,
        actor_type=ActorType.WORKER,
        actor_id="ingestion-worker",
        reason="security intake accepted",
        idempotency_key="transition-quarantine-001",
        expected_status_version=1,
    )

    first = service.transition_claim(claim_id, payload)
    second = service.transition_claim(claim_id, payload)
    claim = service.claims.get(claim_id)

    assert first.status_event_id == second.status_event_id
    assert claim is not None and claim.status == ClaimStatus.QUARANTINED.value
    assert claim.status_version == 2
    assert len(ClaimStatusEventRepository(session, tenant_id).list_for_claim(claim_id)) == 1

    with pytest.raises(ClaimDomainInvariantError, match="invalid claim transition"):
        service.transition_claim(
            claim_id,
            ClaimTransitionRequest(
                status_event_id="status-invalid",
                to_status=ClaimStatus.AI_REVIEWED,
                actor_type=ActorType.AGENT,
                actor_id="ai-orchestrator",
                reason="attempted shortcut",
                idempotency_key="transition-invalid-001",
                expected_status_version=2,
            ),
        )


def test_status_version_conflict_is_rejected(session: Session) -> None:
    tenant_id = "tenant-version"
    service = bootstrap_claim_domain(session, tenant_id)
    with pytest.raises(ClaimDomainInvariantError, match="status version conflict"):
        service.transition_claim(
            f"{tenant_id}-claim",
            ClaimTransitionRequest(
                status_event_id="status-version-conflict",
                to_status=ClaimStatus.QUARANTINED,
                actor_type=ActorType.WORKER,
                actor_id="worker",
                reason="stale write",
                idempotency_key="transition-version-conflict",
                expected_status_version=99,
            ),
        )


def test_generic_workflow_cannot_finalize_human_review(session: Session) -> None:
    tenant_id = "tenant-final-boundary"
    service = bootstrap_claim_domain(session, tenant_id)
    claim_id = f"{tenant_id}-claim"
    advance_to_human_review(service, claim_id)

    with pytest.raises(ClaimDomainInvariantError, match="persisted human decision"):
        service.transition_claim(
            claim_id,
            ClaimTransitionRequest(
                status_event_id="status-illegal-final",
                to_status=ClaimStatus.COMPLETED,
                actor_type=ActorType.AGENT,
                actor_id="decision-agent",
                reason="AI tried to finalize",
                idempotency_key="transition-illegal-final",
                expected_status_version=7,
            ),
        )


def test_persisted_human_decision_finalizes_claim_with_evidence_snapshot(session: Session) -> None:
    tenant_id = "tenant-human-decision"
    service = bootstrap_claim_domain(session, tenant_id, reviewer_id="human-reviewer")
    claim_id = f"{tenant_id}-claim"
    evidence = service.add_evidence(evidence_payload(tenant_id, "evidence-review", "c"))
    advance_to_human_review(service, claim_id)

    decision_payload = HumanDecisionCreate(
        decision_id="decision-001",
        reviewer_user_id="human-reviewer",
        decision=HumanDecision.APPROVE,
        rationale="Evidence and policy records support payment in this synthetic case.",
        evidence_snapshot=[{"evidence_id": evidence.evidence_id, "version": 1}],
        idempotency_key="human-decision-approve-001",
        trace_id="trace-human-review",
    )
    decision = service.record_human_decision(claim_id, decision_payload)
    replay = service.record_human_decision(claim_id, decision_payload)
    claim = service.claims.get(claim_id)

    assert replay.decision_id == decision.decision_id
    assert claim is not None and claim.status == ClaimStatus.COMPLETED.value
    assert claim.status_version == 8
    assert claim.human_review_completed_at is not None
    assert HumanDecisionRepository(session, tenant_id).get_by_idempotency(
        "human-decision-approve-001"
    ) is not None
    actions = [
        event.action
        for event in AuditEventRepository(session, tenant_id).list_for_resource("claim", claim_id)
    ]
    assert "claim.human_decision_recorded" in actions
    assert "claim.status_changed" in actions


def test_unassigned_reviewer_cannot_record_decision(session: Session) -> None:
    tenant_id = "tenant-assignment"
    service = bootstrap_claim_domain(session, tenant_id, reviewer_id="assigned-reviewer")
    tenancy = TenancyService(session)
    tenancy.create_user(
        UserAccountCreate(
            user_id="other-reviewer",
            external_subject="oidc|other-reviewer",
            display_name="Other Reviewer",
            status="active",
        )
    )
    tenancy.add_membership(
        tenant_id,
        MembershipCreate(
            membership_id="membership-other-reviewer",
            user_id="other-reviewer",
            role=UserRole.CLAIMS_REVIEWER,
        ),
    )
    evidence = service.add_evidence(evidence_payload(tenant_id, "evidence-assignment", "d"))
    claim_id = f"{tenant_id}-claim"
    advance_to_human_review(service, claim_id)

    with pytest.raises(ClaimDomainInvariantError, match="assigned to another reviewer"):
        service.record_human_decision(
            claim_id,
            HumanDecisionCreate(
                decision_id="decision-wrong-reviewer",
                reviewer_user_id="other-reviewer",
                decision=HumanDecision.APPROVE,
                rationale="Should be rejected by assignment enforcement.",
                evidence_snapshot=[{"evidence_id": evidence.evidence_id, "version": 1}],
                idempotency_key="decision-wrong-reviewer-001",
            ),
        )

from app.domain.claims import ALLOWED_CLAIM_TRANSITIONS, ClaimStatus
from app.models.claims import (
    AuditEventModel,
    ClaimLineModel,
    ClaimModel,
    ClaimStatusEventModel,
    EncounterModel,
    EvidenceArtifactModel,
    EvidenceLineageModel,
    HumanReviewDecisionModel,
    PatientModel,
    PolicyModel,
    ProviderModel,
)


def main() -> None:
    tables = {
        model.__tablename__
        for model in (
            PatientModel,
            ProviderModel,
            PolicyModel,
            EncounterModel,
            ClaimModel,
            ClaimLineModel,
            EvidenceArtifactModel,
            EvidenceLineageModel,
            ClaimStatusEventModel,
            HumanReviewDecisionModel,
            AuditEventModel,
        )
    }
    required = {
        "patients",
        "providers",
        "policies",
        "encounters",
        "claims",
        "claim_lines",
        "evidence_artifacts",
        "evidence_lineage",
        "claim_status_events",
        "human_review_decisions",
        "audit_events",
    }
    assert tables == required
    assert ClaimStatus.QUARANTINED in ALLOWED_CLAIM_TRANSITIONS[ClaimStatus.SUBMITTED]
    assert ClaimStatus.COMPLETED in ALLOWED_CLAIM_TRANSITIONS[ClaimStatus.HUMAN_REVIEW]
    assert not ALLOWED_CLAIM_TRANSITIONS[ClaimStatus.CANCELLED]
    print("Claim/evidence domain architecture verified.")


if __name__ == "__main__":
    main()

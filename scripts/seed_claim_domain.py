from __future__ import annotations

import json
from pathlib import Path

from app.db.session import get_session_factory
from app.schemas.claims import (
    ClaimCreate,
    ClaimLineCreate,
    EncounterCreate,
    EvidenceCreate,
    EvidenceLineageCreate,
    PatientCreate,
    PolicyCreate,
    ProviderCreate,
)
from app.services.claims import ClaimDomainService

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "sample-data" / "claim_evidence_seed.json"


def main() -> None:
    payload = json.loads(SEED.read_text())
    if payload.get("data_classification") != "synthetic_only":
        raise RuntimeError("claim seed must be explicitly classified synthetic_only")

    session = get_session_factory()()
    try:
        service = ClaimDomainService(session, payload["tenant_id"])
        service.create_patient(PatientCreate(**payload["patient"]))
        service.create_provider(ProviderCreate(**payload["provider"]))
        service.create_policy(PolicyCreate(**payload["policy"]))
        service.create_encounter(EncounterCreate(**payload["encounter"]))
        claim = service.create_claim(ClaimCreate(**payload["claim"]))
        for item in payload["claim_lines"]:
            service.add_claim_line(claim.claim_id, ClaimLineCreate(**item))
        for item in payload["evidence"]:
            service.add_evidence(EvidenceCreate(**item))
        for item in payload["lineage"]:
            service.add_evidence_lineage(EvidenceLineageCreate(**item))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print("Synthetic claim/evidence domain seed loaded.")


if __name__ == "__main__":
    main()

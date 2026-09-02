from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.fhir import FHIRVerificationStatus
from app.fhir_canonical import normalize_claim, normalize_eob


@dataclass(frozen=True)
class VerificationFinding:
    field: str
    uploaded_value: Any
    hospital_value: Any
    status: str
    severity: str


@dataclass(frozen=True)
class CrossVerificationResult:
    status: FHIRVerificationStatus
    confidence: float
    findings: tuple[VerificationFinding, ...]


def verify_financial_claim(uploaded: dict[str, Any], hospital_resource: dict[str, Any]) -> CrossVerificationResult:
    kind = hospital_resource.get("resourceType")
    hospital = normalize_eob(hospital_resource) if kind == "ExplanationOfBenefit" else normalize_claim(hospital_resource)
    findings: list[VerificationFinding] = []

    def compare(field: str, left: Any, right: Any, severity: str = "medium") -> None:
        status = "match" if left == right and left is not None else "mismatch"
        findings.append(VerificationFinding(field, left, right, status, severity))

    compare("patient_external_id", uploaded.get("patient_external_id"), hospital.patient_external_id, "high")
    compare("provider_external_id", uploaded.get("provider_external_id"), hospital.provider_external_id)
    if uploaded.get("total_amount") is not None and hospital.total_amount is not None:
        left = Decimal(str(uploaded["total_amount"])).quantize(Decimal("0.01"))
        right = hospital.total_amount.quantize(Decimal("0.01"))
        compare("total_amount", str(left), str(right), "high")
    if uploaded.get("currency") or hospital.currency:
        compare("currency", uploaded.get("currency"), hospital.currency)
    mismatches = sum(1 for item in findings if item.status == "mismatch")
    matches = len(findings) - mismatches
    if not findings:
        return CrossVerificationResult(FHIRVerificationStatus.INCONCLUSIVE, 0.0, ())
    if mismatches == 0:
        status = FHIRVerificationStatus.MATCH
    elif matches == 0:
        status = FHIRVerificationStatus.MISMATCH
    else:
        status = FHIRVerificationStatus.PARTIAL_MATCH
    confidence = round(matches / len(findings), 4)
    return CrossVerificationResult(status, confidence, tuple(findings))

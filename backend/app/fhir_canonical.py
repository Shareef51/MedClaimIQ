from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.fhir import reference_id


def _identifier(resource: dict[str, Any], preferred_system: str | None = None) -> str | None:
    values = resource.get("identifier") or []
    if preferred_system:
        for item in values:
            if item.get("system") == preferred_system and item.get("value"):
                return str(item["value"])
    for item in values:
        if item.get("value"):
            return str(item["value"])
    return None


def _period(resource: dict[str, Any]) -> tuple[str | None, str | None]:
    period = resource.get("period") or {}
    return period.get("start"), period.get("end")


@dataclass(frozen=True)
class CanonicalPatient:
    external_id: str
    identifiers: tuple[str, ...]
    birth_date: str | None
    family_name: str | None
    given_names: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalEncounter:
    external_id: str
    patient_external_id: str | None
    organization_external_id: str | None
    started_at: str | None
    ended_at: str | None
    status: str | None


@dataclass(frozen=True)
class CanonicalCoverage:
    external_id: str
    patient_external_id: str | None
    subscriber_id: str | None
    payor_external_id: str | None
    effective_from: str | None
    effective_to: str | None
    status: str | None


@dataclass(frozen=True)
class CanonicalFinancialClaim:
    external_id: str
    patient_external_id: str | None
    provider_external_id: str | None
    insurer_external_id: str | None
    coverage_external_id: str | None
    encounter_external_ids: tuple[str, ...]
    total_amount: Decimal | None
    currency: str | None
    service_date: str | None
    status: str | None
    item_count: int


@dataclass(frozen=True)
class CanonicalDocumentReference:
    external_id: str
    patient_external_id: str | None
    encounter_external_ids: tuple[str, ...]
    author_external_ids: tuple[str, ...]
    content_types: tuple[str, ...]
    attachment_urls: tuple[str, ...]
    status: str | None


@dataclass(frozen=True)
class CanonicalOrganization:
    external_id: str
    identifier: str | None
    name: str | None
    active: bool | None


@dataclass(frozen=True)
class CanonicalPractitioner:
    external_id: str
    identifier: str | None
    family_name: str | None
    given_names: tuple[str, ...]
    active: bool | None


def normalize_patient(resource: dict[str, Any]) -> CanonicalPatient:
    names = resource.get("name") or []
    name = names[0] if names else {}
    return CanonicalPatient(
        external_id=str(resource["id"]),
        identifiers=tuple(str(i["value"]) for i in resource.get("identifier") or [] if i.get("value")),
        birth_date=resource.get("birthDate"),
        family_name=name.get("family"),
        given_names=tuple(str(v) for v in name.get("given") or []),
    )


def normalize_encounter(resource: dict[str, Any]) -> CanonicalEncounter:
    start, end = _period(resource)
    service_provider = resource.get("serviceProvider") or {}
    return CanonicalEncounter(
        external_id=str(resource["id"]),
        patient_external_id=reference_id((resource.get("subject") or {}).get("reference"), "Patient"),
        organization_external_id=reference_id(service_provider.get("reference"), "Organization"),
        started_at=start,
        ended_at=end,
        status=resource.get("status"),
    )


def normalize_coverage(resource: dict[str, Any]) -> CanonicalCoverage:
    start, end = _period(resource)
    payors = resource.get("payor") or []
    return CanonicalCoverage(
        external_id=str(resource["id"]),
        patient_external_id=reference_id((resource.get("beneficiary") or {}).get("reference"), "Patient"),
        subscriber_id=resource.get("subscriberId") or _identifier(resource),
        payor_external_id=reference_id((payors[0] if payors else {}).get("reference"), "Organization"),
        effective_from=start,
        effective_to=end,
        status=resource.get("status"),
    )


def normalize_claim(resource: dict[str, Any]) -> CanonicalFinancialClaim:
    total = resource.get("total") or {}
    created = resource.get("created")
    return CanonicalFinancialClaim(
        external_id=str(resource["id"]),
        patient_external_id=reference_id((resource.get("patient") or {}).get("reference"), "Patient"),
        provider_external_id=reference_id((resource.get("provider") or {}).get("reference")),
        insurer_external_id=reference_id((resource.get("insurer") or {}).get("reference"), "Organization"),
        coverage_external_id=reference_id((((resource.get("insurance") or [{}])[0].get("coverage") or {}).get("reference")), "Coverage") if resource.get("insurance") else None,
        encounter_external_ids=tuple(filter(None, [reference_id(enc.get("reference"), "Encounter") for item in resource.get("item") or [] for enc in item.get("encounter") or []])),
        total_amount=Decimal(str(total["value"])) if total.get("value") is not None else None,
        currency=total.get("currency"),
        service_date=created[:10] if isinstance(created, str) and len(created) >= 10 else None,
        status=resource.get("status"),
        item_count=len(resource.get("item") or []),
    )


def normalize_eob(resource: dict[str, Any]) -> CanonicalFinancialClaim:
    total_entries = resource.get("total") or []
    amount = None
    currency = None
    for entry in total_entries:
        money = entry.get("amount") or {}
        if money.get("value") is not None:
            amount = Decimal(str(money["value"]))
            currency = money.get("currency")
            break
    return CanonicalFinancialClaim(
        external_id=str(resource["id"]),
        patient_external_id=reference_id((resource.get("patient") or {}).get("reference"), "Patient"),
        provider_external_id=reference_id((resource.get("provider") or {}).get("reference")),
        insurer_external_id=reference_id((resource.get("insurer") or {}).get("reference"), "Organization"),
        coverage_external_id=reference_id((((resource.get("insurance") or [{}])[0].get("coverage") or {}).get("reference")), "Coverage") if resource.get("insurance") else None,
        encounter_external_ids=tuple(filter(None, [reference_id(enc.get("reference"), "Encounter") for item in resource.get("item") or [] for enc in item.get("encounter") or []])),
        total_amount=amount,
        currency=currency,
        service_date=(resource.get("created") or "")[:10] or None,
        status=resource.get("status"),
        item_count=len(resource.get("item") or []),
    )



def normalize_document_reference(resource: dict[str, Any]) -> CanonicalDocumentReference:
    content = resource.get("content") or []
    context = resource.get("context") or {}
    return CanonicalDocumentReference(
        external_id=str(resource["id"]),
        patient_external_id=reference_id((resource.get("subject") or {}).get("reference"), "Patient"),
        encounter_external_ids=tuple(filter(None, [reference_id(e.get("reference"), "Encounter") for e in context.get("encounter") or []])),
        author_external_ids=tuple(filter(None, [reference_id(a.get("reference")) for a in resource.get("author") or []])),
        content_types=tuple(str((c.get("attachment") or {}).get("contentType")) for c in content if (c.get("attachment") or {}).get("contentType")),
        attachment_urls=tuple(str((c.get("attachment") or {}).get("url")) for c in content if (c.get("attachment") or {}).get("url")),
        status=resource.get("status"),
    )


def normalize_organization(resource: dict[str, Any]) -> CanonicalOrganization:
    return CanonicalOrganization(external_id=str(resource["id"]), identifier=_identifier(resource), name=resource.get("name"), active=resource.get("active"))


def normalize_practitioner(resource: dict[str, Any]) -> CanonicalPractitioner:
    names=resource.get("name") or []
    name=names[0] if names else {}
    return CanonicalPractitioner(external_id=str(resource["id"]), identifier=_identifier(resource), family_name=name.get("family"), given_names=tuple(str(v) for v in name.get("given") or []), active=resource.get("active"))

def normalize_resource(resource: dict[str, Any]) -> object:
    kind = resource.get("resourceType")
    if kind == "Patient":
        return normalize_patient(resource)
    if kind == "Encounter":
        return normalize_encounter(resource)
    if kind == "Coverage":
        return normalize_coverage(resource)
    if kind == "Claim":
        return normalize_claim(resource)
    if kind == "ExplanationOfBenefit":
        return normalize_eob(resource)
    if kind == "DocumentReference":
        return normalize_document_reference(resource)
    if kind == "Organization":
        return normalize_organization(resource)
    if kind == "Practitioner":
        return normalize_practitioner(resource)
    return {"resource_type": kind, "id": resource.get("id")}

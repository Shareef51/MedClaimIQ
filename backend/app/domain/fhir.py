from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

FHIR_R4_VERSION = "4.0.1"


class FHIRResourceType(StrEnum):
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    COVERAGE = "Coverage"
    CLAIM = "Claim"
    EXPLANATION_OF_BENEFIT = "ExplanationOfBenefit"
    DOCUMENT_REFERENCE = "DocumentReference"
    ORGANIZATION = "Organization"
    PRACTITIONER = "Practitioner"


SUPPORTED_RESOURCE_TYPES = frozenset(item.value for item in FHIRResourceType)


class FHIRVerificationStatus(StrEnum):
    MATCH = "match"
    PARTIAL_MATCH = "partial_match"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    INCONCLUSIVE = "inconclusive"


class IdentityMatchStatus(StrEnum):
    MATCHED = "matched"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ResourceVersion:
    resource_type: str
    logical_id: str
    version_id: str
    last_updated: str | None
    source_url: str
    payload: dict[str, Any]


def reference_id(reference: str | None, resource_type: str | None = None) -> str | None:
    if not reference:
        return None
    value = reference.split("?")[0].strip("/")
    parts = value.split("/")
    if len(parts) >= 2:
        if resource_type and parts[-2] != resource_type:
            return None
        return parts[-1]
    return value


def resource_version(resource: dict[str, Any], source_url: str) -> ResourceVersion:
    resource_type = str(resource.get("resourceType") or "")
    logical_id = str(resource.get("id") or "")
    meta = resource.get("meta") or {}
    version_id = str(meta.get("versionId") or "1")
    if not resource_type or not logical_id:
        raise ValueError("FHIR resource requires resourceType and id")
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise ValueError(f"unsupported FHIR resource type: {resource_type}")
    return ResourceVersion(
        resource_type=resource_type,
        logical_id=logical_id,
        version_id=version_id,
        last_updated=meta.get("lastUpdated"),
        source_url=source_url,
        payload=resource,
    )

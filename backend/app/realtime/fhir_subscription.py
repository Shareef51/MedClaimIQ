from __future__ import annotations
from dataclasses import dataclass
from app.domain.fhir import SUPPORTED_RESOURCE_TYPES

@dataclass(frozen=True, slots=True)
class FHIRSubscriptionNotification:
    resource_type: str
    resource_id: str
    version_id: str | None
    subscription_id: str | None

class FHIRSubscriptionValidator:
    def validate(self,payload:dict)->FHIRSubscriptionNotification:
        resource_type=str(payload.get("resourceType") or "")
        resource_id=str(payload.get("id") or "")
        if resource_type not in SUPPORTED_RESOURCE_TYPES: raise ValueError("unsupported FHIR subscription resource type")
        if not resource_id: raise ValueError("FHIR subscription event requires resource id")
        meta=payload.get("meta") if isinstance(payload.get("meta"),dict) else {}
        return FHIRSubscriptionNotification(resource_type,resource_id,str(meta.get("versionId")) if meta.get("versionId") else None,str(payload.get("subscriptionId")) if payload.get("subscriptionId") else None)

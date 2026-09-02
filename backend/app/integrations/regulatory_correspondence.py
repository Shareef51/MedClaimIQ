from __future__ import annotations
from dataclasses import dataclass
import hashlib,json
from typing import Protocol

@dataclass(frozen=True,slots=True)
class RegulatoryCorrespondenceDeliveryResult:
    status:str
    external_reference:str
    provider_metadata:dict[str,str]

class RegulatoryCorrespondenceAdapter(Protocol):
    def deliver(self,*,channel:str,subject:str,body:str,idempotency_key:str)->RegulatoryCorrespondenceDeliveryResult: ...

class SandboxSecureRegulatoryCorrespondenceAdapter:
    """Deterministic non-network adapter for the portfolio.

    Production deployments replace this with a regulator-approved portal/SFTP/encrypted-mail/API adapter.
    It transports only an already human-approved response and has no response-approval or financial authority.
    """
    def deliver(self,*,channel:str,subject:str,body:str,idempotency_key:str)->RegulatoryCorrespondenceDeliveryResult:
        raw=json.dumps({"channel":channel,"subject":subject,"body_sha256":hashlib.sha256(body.encode()).hexdigest(),"idempotency_key":idempotency_key},sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(raw.encode()).hexdigest()
        return RegulatoryCorrespondenceDeliveryResult(status="delivered",external_reference=f"sandbox-regcorr-{digest[:20]}",provider_metadata={"adapter":"sandbox-secure-regulatory-correspondence","network":"disabled","authority":"transport_only"})

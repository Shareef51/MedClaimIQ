from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class RegulatoryTransportRequest:
    dispatch_key:str
    destination_key:str
    endpoint_reference:str
    encrypted_envelope:str
    envelope_signature:str
    schema_name:str
    schema_version:str

@dataclass(frozen=True)
class RegulatoryTransportResult:
    provider_message_id:str
    external_submission_reference:str
    accepted_for_delivery:bool=True

class RegulatoryTransportAdapter(Protocol):
    def send(self,request:RegulatoryTransportRequest)->RegulatoryTransportResult: ...

class SandboxRegulatoryTransportAdapter:
    """Deterministic non-network adapter used by tests/demo.

    It transmits an already encrypted envelope conceptually and never creates a regulatory release.
    `fail://` endpoint references deliberately raise to exercise retry/circuit-breaker controls.
    """
    def send(self,request:RegulatoryTransportRequest)->RegulatoryTransportResult:
        if request.endpoint_reference.startswith("fail://"):
            raise RuntimeError("synthetic regulator transport failure")
        return RegulatoryTransportResult(
            provider_message_id=f"regmsg_{request.dispatch_key[:24]}",
            external_submission_reference=f"EXT-{request.dispatch_key[:20]}",
        )


def adapter_for(transport_type:str)->RegulatoryTransportAdapter:
    # Production https/sftp implementations plug into this registry. This portfolio build intentionally
    # ships a non-network adapter so no external submission occurs without deployment-specific integration.
    return SandboxRegulatoryTransportAdapter()

from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class FinancialAdapterResult:
    external_instruction_id:str; status:str; acknowledgement_sha256:str
class FinancialAdapter(Protocol):
    name:str
    def stage_instruction(self,instruction:dict)->FinancialAdapterResult: ...
class SandboxFinancialAdapter:
    """Deterministic non-settling adapter. It acknowledges an authorized instruction; it never moves funds."""
    name="sandbox-financial-ledger"
    def stage_instruction(self,instruction:dict)->FinancialAdapterResult:
        raw=json.dumps(instruction,sort_keys=True,separators=(",",":"),default=str)
        digest=hashlib.sha256(raw.encode()).hexdigest()
        return FinancialAdapterResult(external_instruction_id=f"fin_{digest[:24]}",status="accepted_for_processing",acknowledgement_sha256=digest)
class FinancialAdapterRegistry:
    def __init__(self,adapters=None): self._adapters={a.name:a for a in (adapters or [SandboxFinancialAdapter()])}
    def get(self,name:str):
        if name not in self._adapters: raise LookupError("financial adapter not registered")
        return self._adapters[name]

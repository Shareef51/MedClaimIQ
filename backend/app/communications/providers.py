from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class ProviderSendResult:
    accepted: bool
    provider_message_id: str | None
    error_code: str | None = None
    retryable: bool = False


class CommunicationProvider(Protocol):
    name: str
    channel: str
    def send(self, *, destination:str, subject:str|None, body:str, idempotency_key:str, metadata:dict) -> ProviderSendResult: ...


class _SandboxProvider:
    def __init__(self,name:str,channel:str): self.name=name; self.channel=channel
    def send(self, *, destination:str, subject:str|None, body:str, idempotency_key:str, metadata:dict) -> ProviderSendResult:
        if destination.startswith("fail:"):
            return ProviderSendResult(False,None,"sandbox_provider_failure",True)
        if destination.startswith("bounce:"):
            return ProviderSendResult(True,f"{self.name}_{uuid4().hex}")
        return ProviderSendResult(True,f"{self.name}_{uuid4().hex}")


class EmailDeliveryAdapter(_SandboxProvider):
    def __init__(self): super().__init__("email-sandbox","email")


class SmsDeliveryAdapter(_SandboxProvider):
    def __init__(self): super().__init__("sms-sandbox","sms")


class PortalDeliveryAdapter(_SandboxProvider):
    def __init__(self): super().__init__("portal-inbox","portal")


class ProviderRegistry:
    def __init__(self, providers:list[CommunicationProvider]|None=None):
        providers=providers or [EmailDeliveryAdapter(),SmsDeliveryAdapter(),PortalDeliveryAdapter()]
        self._by_channel={p.channel:p for p in providers}
        self._by_name={p.name:p for p in providers}
    def for_channel(self,channel:str)->CommunicationProvider:
        try:return self._by_channel[channel]
        except KeyError as exc: raise LookupError(f"no communication provider configured for {channel}") from exc
    def by_name(self,name:str)->CommunicationProvider:
        try:return self._by_name[name]
        except KeyError as exc: raise LookupError(f"unknown communication provider {name}") from exc

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import httpx

from app.domain.fhir import SUPPORTED_RESOURCE_TYPES, resource_version
from app.fhir.smart import AccessTokenProvider
from app.observability.tracing import inject_trace_headers, traced_operation


class FHIRGatewayError(RuntimeError):
    pass


@dataclass
class TokenBucketRateLimiter:
    rate_per_second: float = 10.0
    burst: int = 20
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.burst)
        self.last_refill = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate_per_second)
        self.last_refill = now
        if self.tokens < 1.0:
            wait = (1.0 - self.tokens) / max(self.rate_per_second, 0.001)
            time.sleep(wait)
            self.tokens = 0.0
        else:
            self.tokens -= 1.0


class FHIRGateway:
    def __init__(
        self,
        *,
        base_url: str,
        token_provider: AccessTokenProvider | None = None,
        timeout_seconds: float = 10.0,
        max_attempts: int = 3,
        rate_per_second: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.rate_limiter = TokenBucketRateLimiter(rate_per_second=rate_per_second)
        self.client = client or httpx.Client(timeout=timeout_seconds)
        parsed = urlparse(self.base_url)
        self._base_origin = (parsed.scheme, parsed.netloc)

    def close(self) -> None:
        self.client.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/fhir+json", "User-Agent": "MedClaimIQ-FHIR-Gateway/1"}
        if self.token_provider:
            headers["Authorization"] = f"Bearer {self.token_provider.get_access_token()}"
        return inject_trace_headers(headers)

    def _safe_next_url(self, url: str) -> str:
        absolute = urljoin(self.base_url, url)
        parsed = urlparse(absolute)
        if (parsed.scheme, parsed.netloc) != self._base_origin:
            raise FHIRGatewayError("FHIR Bundle next link changed origin")
        return absolute

    def _get(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self.rate_limiter.acquire()
            try:
                with traced_operation("fhir.http.get", kind="client", attributes={"origin": self._base_origin[1], "attempt": attempt}):
                    response = self.client.get(url, params=params, headers=self._headers())
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    break
                time.sleep(min(2 ** (attempt - 1), 4) + random.random() * 0.05)
                continue
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            if attempt == self.max_attempts:
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** (attempt - 1), 4)
            time.sleep(delay)
        raise FHIRGatewayError(f"FHIR request failed after retries: {last_error}")

    def capability_statement(self) -> dict[str, Any]:
        response = self._get(urljoin(self.base_url, "metadata"))
        response.raise_for_status()
        body = response.json()
        if body.get("resourceType") != "CapabilityStatement":
            raise FHIRGatewayError("FHIR metadata endpoint did not return CapabilityStatement")
        return body

    def read(self, resource_type: str, logical_id: str) -> dict[str, Any]:
        if resource_type not in SUPPORTED_RESOURCE_TYPES:
            raise FHIRGatewayError(f"unsupported resource type {resource_type}")
        response = self._get(urljoin(self.base_url, f"{resource_type}/{logical_id}"))
        if response.status_code == 404:
            raise KeyError(f"{resource_type}/{logical_id}")
        response.raise_for_status()
        resource = response.json()
        resource_version(resource, str(response.url))
        return resource

    def search(self, resource_type: str, *, params: dict[str, Any] | None = None, max_pages: int = 20) -> list[dict[str, Any]]:
        if resource_type not in SUPPORTED_RESOURCE_TYPES:
            raise FHIRGatewayError(f"unsupported resource type {resource_type}")
        url = urljoin(self.base_url, resource_type)
        query = dict(params or {})
        resources: list[dict[str, Any]] = []
        seen_next: set[str] = set()
        for _ in range(max_pages):
            response = self._get(url, params=query)
            response.raise_for_status()
            bundle = response.json()
            if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "searchset":
                raise FHIRGatewayError("FHIR search did not return searchset Bundle")
            for entry in bundle.get("entry") or []:
                resource = entry.get("resource")
                if resource:
                    resource_version(resource, entry.get("fullUrl") or str(response.url))
                    resources.append(resource)
            next_url = None
            for link in bundle.get("link") or []:
                if link.get("relation") == "next":
                    next_url = self._safe_next_url(str(link.get("url")))
                    break
            if not next_url:
                break
            if next_url in seen_next:
                raise FHIRGatewayError("FHIR pagination loop detected")
            seen_next.add(next_url)
            url, query = next_url, None
        return resources

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx
import jwt


class AccessTokenProvider(Protocol):
    def get_access_token(self) -> str: ...


@dataclass
class SmartBackendServicesTokenProvider:
    """SMART Backend Services-style private-key JWT token boundary.

    Production secrets/private keys should come from a secret manager, never source control.
    """

    token_url: str
    client_id: str
    private_key_pem: str
    key_id: str
    scopes: tuple[str, ...] = ("system/*.read",)
    algorithm: str = "RS384"
    timeout_seconds: float = 5.0
    _cached_token: str | None = None
    _cached_expires_at: float = 0

    def get_access_token(self) -> str:
        now = int(time.time())
        if self._cached_token and now < self._cached_expires_at - 30:
            return self._cached_token
        assertion = jwt.encode(
            {
                "iss": self.client_id,
                "sub": self.client_id,
                "aud": self.token_url,
                "exp": now + 300,
                "jti": str(uuid.uuid4()),
            },
            self.private_key_pem,
            algorithm=self.algorithm,
            headers={"kid": self.key_id, "typ": "JWT"},
        )
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": " ".join(self.scopes),
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": assertion,
                },
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        body = response.json()
        token = body.get("access_token")
        if not token:
            raise RuntimeError("SMART token response missing access_token")
        self._cached_token = str(token)
        self._cached_expires_at = now + int(body.get("expires_in", 300))
        return self._cached_token

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EncryptedDataKey:
    ciphertext_b64: str
    key_id: str
    provider: str


class DataKeyProvider(Protocol):
    def generate_data_key(self, *, encryption_context: dict[str, str]) -> tuple[bytes, EncryptedDataKey]: ...
    def decrypt_data_key(self, encrypted: EncryptedDataKey, *, encryption_context: dict[str, str]) -> bytes: ...


class AWSKMSDataKeyProvider:
    """Envelope-encryption adapter. boto3 is already a core MedClaimIQ dependency.

    Plaintext data keys are returned only to the caller and must never be persisted.
    The database/object metadata stores the encrypted data key and key identifier.
    """

    def __init__(self, kms_key_id: str, *, region_name: str | None = None, client=None) -> None:
        if not kms_key_id:
            raise ValueError("KMS key id is required")
        self.kms_key_id = kms_key_id
        if client is None:
            import boto3
            client = boto3.client("kms", region_name=region_name)
        self.client = client

    def generate_data_key(self, *, encryption_context: dict[str, str]) -> tuple[bytes, EncryptedDataKey]:
        result = self.client.generate_data_key(KeyId=self.kms_key_id, KeySpec="AES_256", EncryptionContext=encryption_context)
        plaintext = bytes(result["Plaintext"])
        ciphertext = base64.b64encode(bytes(result["CiphertextBlob"])).decode("ascii")
        return plaintext, EncryptedDataKey(ciphertext_b64=ciphertext, key_id=str(result.get("KeyId") or self.kms_key_id), provider="aws-kms")

    def decrypt_data_key(self, encrypted: EncryptedDataKey, *, encryption_context: dict[str, str]) -> bytes:
        result = self.client.decrypt(
            CiphertextBlob=base64.b64decode(encrypted.ciphertext_b64),
            KeyId=encrypted.key_id,
            EncryptionContext=encryption_context,
        )
        return bytes(result["Plaintext"])


class EnvironmentSecretResolver:
    """Local/dev resolver. Production deployments should inject references via Vault/Secrets Manager."""

    def get(self, name: str) -> str:
        value = os.getenv(name)
        if value is None:
            raise KeyError(f"Secret {name} is not configured")
        return value


class AWSSecretsManagerResolver:
    """Production secret resolver; secret values are returned only to the requesting component."""
    def __init__(self, *, region_name: str | None = None, client=None) -> None:
        if client is None:
            import boto3
            client = boto3.client("secretsmanager", region_name=region_name)
        self.client = client

    def get(self, secret_id: str, *, json_key: str | None = None) -> str:
        result = self.client.get_secret_value(SecretId=secret_id)
        value = result.get("SecretString")
        if value is None:
            value = base64.b64decode(result["SecretBinary"]).decode("utf-8")
        if json_key is None:
            return str(value)
        parsed = json.loads(value)
        if json_key not in parsed:
            raise KeyError(f"Secret JSON key {json_key} is not present")
        return str(parsed[json_key])


@dataclass(frozen=True)
class KeyLifecyclePolicy:
    rotation_days: int = 365

    def rotation_due(self, activated_at, *, now=None) -> bool:
        from datetime import datetime, timezone, timedelta
        now = now or datetime.now(timezone.utc)
        return now >= activated_at + timedelta(days=self.rotation_days)

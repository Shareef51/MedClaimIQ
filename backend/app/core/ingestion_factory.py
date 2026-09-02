from __future__ import annotations

from app.core.config import Settings
from app.ingestion.malware import ClamAVScanner
from app.storage.object_store import S3ObjectStorage


def build_object_storage(settings: Settings) -> S3ObjectStorage:
    return S3ObjectStorage(
        endpoint_url=settings.s3_endpoint_url,
        public_endpoint_url=settings.s3_public_endpoint_url,
        access_key=None if settings.s3_use_default_credential_chain else settings.s3_access_key,
        secret_key=None if settings.s3_use_default_credential_chain else settings.s3_secret_key,
        region=settings.s3_region,
        server_side_encryption=settings.s3_server_side_encryption or None,
        sse_kms_key_id=settings.s3_sse_kms_key_id or None,
    )


def build_malware_scanner(settings: Settings) -> ClamAVScanner:
    return ClamAVScanner(
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout_seconds=settings.clamav_timeout_seconds,
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Protocol


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    method: str
    required_headers: dict[str, str]
    form_fields: dict[str, str]


@dataclass(frozen=True)
class StoredObjectInfo:
    bucket: str
    key: str
    byte_size: int
    etag: str | None
    version_id: str | None
    content_type: str | None
    metadata: dict[str, str]


class ObjectStorage(Protocol):
    def create_presigned_upload(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        metadata: dict[str, str],
        expires_seconds: int,
        expected_byte_size: int,
    ) -> PresignedUpload: ...

    def create_presigned_download(self, *, bucket: str, key: str, expires_seconds: int, response_content_type: str | None = None) -> str: ...

    def head_object(self, *, bucket: str, key: str) -> StoredObjectInfo: ...

    def iter_object_chunks(
        self, *, bucket: str, key: str, chunk_size: int = 1024 * 1024
    ) -> Iterable[bytes]: ...

    def promote_object(
        self, *, bucket: str, source_key: str, destination_key: str, source_version_id: str | None = None
    ) -> StoredObjectInfo: ...

    def put_object(self, *, bucket: str, key: str, body: bytes, content_type: str, metadata: dict[str, str] | None = None) -> StoredObjectInfo: ...

    def delete_object(self, *, bucket: str, key: str) -> None: ...


class S3ObjectStorage:
    """S3-compatible storage adapter for AWS S3 or MinIO.

    boto3 is imported lazily so API/unit-test imports do not require an object-store
    client to be constructed. Production packaging includes boto3 as a dependency.
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None,
        public_endpoint_url: str | None = None,
        access_key: str | None,
        secret_key: str | None,
        region: str = "us-east-1",
        server_side_encryption: str | None = None,
        sse_kms_key_id: str | None = None,
    ) -> None:
        try:
            import boto3  # type: ignore
            from botocore.config import Config  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment packaging guard
            raise RuntimeError("boto3 is required for the S3/MinIO object storage adapter") from exc

        self.server_side_encryption = server_side_encryption or None
        self.sse_kms_key_id = sse_kms_key_id or None
        client_args: dict[str, object] = {
            "service_name": "s3",
            "region_name": region,
            "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        }
        if access_key and secret_key:
            client_args["aws_access_key_id"] = access_key
            client_args["aws_secret_access_key"] = secret_key
        self.client = boto3.client(endpoint_url=endpoint_url or None, **client_args)
        self.presign_client = (
            boto3.client(endpoint_url=public_endpoint_url, **client_args)
            if public_endpoint_url and public_endpoint_url != endpoint_url
            else self.client
        )

    def create_presigned_upload(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        metadata: dict[str, str],
        expires_seconds: int,
        expected_byte_size: int,
    ) -> PresignedUpload:
        fields: dict[str, str] = {"Content-Type": content_type}
        conditions: list[object] = [
            {"Content-Type": content_type},
            ["content-length-range", expected_byte_size, expected_byte_size],
        ]
        for name, value in metadata.items():
            field_name = f"x-amz-meta-{name}"
            fields[field_name] = value
            conditions.append({field_name: value})
        if self.server_side_encryption:
            fields["x-amz-server-side-encryption"] = self.server_side_encryption
            conditions.append({"x-amz-server-side-encryption": self.server_side_encryption})
            if self.server_side_encryption == "aws:kms" and self.sse_kms_key_id:
                fields["x-amz-server-side-encryption-aws-kms-key-id"] = self.sse_kms_key_id
                conditions.append({"x-amz-server-side-encryption-aws-kms-key-id": self.sse_kms_key_id})
        response = self.presign_client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_seconds,
        )
        return PresignedUpload(
            url=response["url"],
            method="POST",
            required_headers={},
            form_fields={str(k): str(v) for k, v in response["fields"].items()},
        )

    def create_presigned_download(self, *, bucket: str, key: str, expires_seconds: int, response_content_type: str | None = None) -> str:
        params: dict[str, str] = {"Bucket": bucket, "Key": key}
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        return str(self.presign_client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_seconds))

    def head_object(self, *, bucket: str, key: str) -> StoredObjectInfo:
        response = self.client.head_object(Bucket=bucket, Key=key)
        return StoredObjectInfo(
            bucket=bucket,
            key=key,
            byte_size=int(response["ContentLength"]),
            etag=str(response.get("ETag", "")).strip('"') or None,
            version_id=response.get("VersionId"),
            content_type=response.get("ContentType"),
            metadata={str(k).lower(): str(v) for k, v in response.get("Metadata", {}).items()},
        )

    def iter_object_chunks(
        self, *, bucket: str, key: str, chunk_size: int = 1024 * 1024
    ) -> Iterator[bytes]:
        response = self.client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        try:
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                yield bytes(chunk)
        finally:
            body.close()

    def promote_object(
        self, *, bucket: str, source_key: str, destination_key: str, source_version_id: str | None = None
    ) -> StoredObjectInfo:
        copy_source: dict[str, str] = {"Bucket": bucket, "Key": source_key}
        if source_version_id:
            copy_source["VersionId"] = source_version_id
        args: dict[str, object] = {
            "Bucket": bucket,
            "Key": destination_key,
            "CopySource": copy_source,
            "MetadataDirective": "COPY",
        }
        if self.server_side_encryption:
            args["ServerSideEncryption"] = self.server_side_encryption
            if self.server_side_encryption == "aws:kms" and self.sse_kms_key_id:
                args["SSEKMSKeyId"] = self.sse_kms_key_id
                args["BucketKeyEnabled"] = True
        self.client.copy_object(**args)
        promoted = self.head_object(bucket=bucket, key=destination_key)
        self.client.delete_object(Bucket=bucket, Key=source_key)
        return promoted

    def put_object(self, *, bucket: str, key: str, body: bytes, content_type: str, metadata: dict[str, str] | None = None) -> StoredObjectInfo:
        args: dict[str, object] = {"Bucket": bucket, "Key": key, "Body": body, "ContentType": content_type, "Metadata": metadata or {}}
        if self.server_side_encryption:
            args["ServerSideEncryption"] = self.server_side_encryption
            if self.server_side_encryption == "aws:kms" and self.sse_kms_key_id:
                args["SSEKMSKeyId"] = self.sse_kms_key_id
                args["BucketKeyEnabled"] = True
        self.client.put_object(**args)
        return self.head_object(bucket=bucket, key=key)

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.client.delete_object(Bucket=bucket, Key=key)

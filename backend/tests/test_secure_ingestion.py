from __future__ import annotations

from datetime import date
from decimal import Decimal
from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.access import TenantType, UserRole
from app.domain.claims import ActorType, EvidenceSourceType
from app.domain.ingestion import IngestionEventType, MalwareVerdict, UploadSessionStatus
from app.ingestion.malware import MalwareScanResult
from app.repositories.claims import EvidenceRepository
from app.repositories.ingestion import ProcessingEventRepository, UploadSessionRepository
from app.schemas.claims import ClaimCreate, PatientCreate
from app.schemas.ingestion import UploadInitiateRequest
from app.schemas.tenancy import MembershipCreate, OrganizationCreate, TenantCreate, UserAccountCreate
from app.services.claims import ClaimDomainService
from app.services.ingestion import EvidenceIngestionService, IngestionInvariantError
from app.services.tenancy import TenancyService
from app.storage.object_store import PresignedUpload, StoredObjectInfo
from app.workers.evidence_ingestion import EvidenceIngestionWorker


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, object]] = {}
        self.last_presign: dict[str, object] | None = None
        self.promotions: list[tuple[str, str]] = []

    def create_presigned_upload(self, *, bucket, key, content_type, metadata, expires_seconds, expected_byte_size):
        self.last_presign = {
            "bucket": bucket,
            "key": key,
            "content_type": content_type,
            "metadata": metadata,
            "expires_seconds": expires_seconds,
            "expected_byte_size": expected_byte_size,
        }
        fields = {"Content-Type": content_type}
        fields.update({f"x-amz-meta-{k}": v for k, v in metadata.items()})
        return PresignedUpload(
            url=f"https://object-store.invalid/{bucket}/{key}?signature=synthetic",
            method="POST",
            required_headers={},
            form_fields=fields,
        )

    def put(self, *, bucket: str, key: str, body: bytes, content_type: str, metadata: dict[str, str]):
        self.objects[(bucket, key)] = {
            "body": body,
            "content_type": content_type,
            "metadata": dict(metadata),
            "etag": sha256(body).hexdigest()[:32],
            "version_id": f"v-{sha256(body).hexdigest()[:12]}",
        }

    def head_object(self, *, bucket: str, key: str) -> StoredObjectInfo:
        obj = self.objects[(bucket, key)]
        return StoredObjectInfo(
            bucket=bucket,
            key=key,
            byte_size=len(obj["body"]),
            etag=obj["etag"],
            version_id=obj["version_id"],
            content_type=obj["content_type"],
            metadata=obj["metadata"],
        )

    def iter_object_chunks(self, *, bucket: str, key: str, chunk_size: int = 1024 * 1024):
        body = self.objects[(bucket, key)]["body"]
        for offset in range(0, len(body), chunk_size):
            yield body[offset : offset + chunk_size]

    def promote_object(self, *, bucket: str, source_key: str, destination_key: str, source_version_id=None):
        obj = dict(self.objects[(bucket, source_key)])
        if source_version_id is not None:
            assert obj["version_id"] == source_version_id
        self.objects[(bucket, destination_key)] = obj
        del self.objects[(bucket, source_key)]
        self.promotions.append((source_key, destination_key))
        return self.head_object(bucket=bucket, key=destination_key)

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)


class FakeScanner:
    def __init__(self, verdict: MalwareVerdict) -> None:
        self.verdict = verdict
        self.bytes_seen = 0

    def scan(self, chunks):
        for chunk in chunks:
            self.bytes_seen += len(chunk)
        return MalwareScanResult(
            verdict=self.verdict,
            scanner_name="fake-clamav",
            scanner_version="test",
            signature_name="EICAR-Test-Signature" if self.verdict is MalwareVerdict.INFECTED else None,
        )


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    Base.metadata.drop_all(engine)


def bootstrap_claim(session: Session, tenant_id: str = "tenant-upload", user_id: str = "user-upload") -> str:
    tenancy = TenancyService(session)
    tenancy.create_tenant(
        TenantCreate(
            tenant_id=tenant_id,
            slug=tenant_id,
            display_name=tenant_id,
            tenant_type=TenantType.DEMO,
        )
    )
    tenancy.create_organization(
        tenant_id,
        OrganizationCreate(
            organization_id=f"{tenant_id}-payer",
            slug="payer",
            display_name="Synthetic Payer",
            organization_type="payer",
        ),
    )
    tenancy.create_organization(
        tenant_id,
        OrganizationCreate(
            organization_id=f"{tenant_id}-provider",
            slug="provider",
            display_name="Synthetic Provider",
            organization_type="hospital",
        ),
    )
    tenancy.create_user(
        UserAccountCreate(
            user_id=user_id,
            external_subject=f"oidc|{user_id}",
            display_name="Synthetic User",
            status="active",
        )
    )
    tenancy.add_membership(
        tenant_id,
        MembershipCreate(
            membership_id=f"membership-{tenant_id}-{user_id}",
            user_id=user_id,
            role=UserRole.PATIENT,
            patient_subject_id=f"{tenant_id}-subject",
        ),
    )
    claims = ClaimDomainService(session, tenant_id)
    claims.create_patient(
        PatientCreate(patient_id=f"{tenant_id}-patient", patient_subject_id=f"{tenant_id}-subject")
    )
    claim_id = f"{tenant_id}-claim"
    claims.create_claim(
        ClaimCreate(
            claim_id=claim_id,
            external_claim_ref=f"CLAIM-{tenant_id}",
            patient_subject_id=f"{tenant_id}-subject",
            provider_organization_id=f"{tenant_id}-provider",
            payer_organization_id=f"{tenant_id}-payer",
            total_amount=Decimal("25.00"),
            service_from=date(2026, 8, 19),
            created_by_actor_type=ActorType.SYSTEM,
            created_by_actor_id="synthetic-intake",
            idempotency_key=f"create-{tenant_id}-claim",
        )
    )
    return claim_id


def initiate_pdf(session: Session, storage: FakeObjectStorage, *, tenant_id="tenant-upload", user_id="user-upload", idempotency="upload-request-001", body=b"%PDF-1.7\nsynthetic evidence\n"):
    claim_id = f"{tenant_id}-claim"
    service = EvidenceIngestionService(
        session,
        tenant_id,
        storage=storage,
        bucket_name="medclaimiq",
        presign_ttl_seconds=900,
    )
    upload, signed = service.initiate_upload(
        claim_id=claim_id,
        user_id=user_id,
        source_type=EvidenceSourceType.USER_UPLOAD,
        idempotency_key=idempotency,
        payload=UploadInitiateRequest(
            client_filename="Jane_Doe_medical_bill.pdf",
            document_type="medical_bill",
            declared_media_type="application/pdf",
            expected_byte_size=len(body),
            expected_sha256=sha256(body).hexdigest(),
        ),
        trace_id="trace-upload",
    )
    metadata = {
        key.removeprefix("x-amz-meta-"): value
        for key, value in signed.form_fields.items()
        if key.startswith("x-amz-meta-")
    }
    storage.put(
        bucket="medclaimiq",
        key=upload.quarantine_object_key,
        body=body,
        content_type="application/pdf",
        metadata=metadata,
    )
    return service, upload, signed


def test_upload_session_hashes_filename_and_is_idempotent(session: Session) -> None:
    claim_id = bootstrap_claim(session)
    storage = FakeObjectStorage()
    body = b"%PDF-1.7\nsynthetic evidence\n"
    service, upload, signed = initiate_pdf(session, storage, body=body)
    again, again_signed = service.initiate_upload(
        claim_id=claim_id,
        user_id="user-upload",
        source_type=EvidenceSourceType.USER_UPLOAD,
        idempotency_key="upload-request-001",
        payload=UploadInitiateRequest(
            client_filename="Jane_Doe_medical_bill.pdf",
            document_type="medical_bill",
            declared_media_type="application/pdf",
            expected_byte_size=len(body),
            expected_sha256=sha256(body).hexdigest(),
        ),
    )

    assert upload.upload_session_id == again.upload_session_id
    assert upload.client_filename_sha256 == sha256(b"Jane_Doe_medical_bill.pdf").hexdigest()
    assert "Jane_Doe" not in upload.quarantine_object_key
    assert upload.quarantine_object_key.startswith("quarantine/tenant-upload/")
    assert signed.method == again_signed.method == "POST"
    assert signed.form_fields["Content-Type"] == "application/pdf"


def test_initiation_rejects_extension_mime_mismatch(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    service = EvidenceIngestionService(session, "tenant-upload", storage=storage, bucket_name="medclaimiq")
    with pytest.raises(IngestionInvariantError, match="declared media type"):
        service.initiate_upload(
            claim_id="tenant-upload-claim",
            user_id="user-upload",
            source_type=EvidenceSourceType.USER_UPLOAD,
            idempotency_key="upload-request-bad-mime",
            payload=UploadInitiateRequest(
                client_filename="evidence.pdf",
                document_type="medical_bill",
                declared_media_type="image/png",
                expected_byte_size=100,
            ),
        )


def test_completion_rejects_tampered_object_metadata(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    service, upload, _ = initiate_pdf(session, storage)
    storage.objects[("medclaimiq", upload.quarantine_object_key)]["metadata"] = {
        "upload-session-id": upload.upload_session_id,
        "tenant-id": "other-tenant",
        "claim-id": upload.claim_id,
    }
    with pytest.raises(IngestionInvariantError, match="ownership metadata"):
        service.complete_upload(upload.upload_session_id)
    assert upload.status == UploadSessionStatus.REJECTED.value
    assert upload.rejection_code == "object_metadata_mismatch"


def test_clean_pdf_is_promoted_and_registered_as_evidence(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    service, upload, _ = initiate_pdf(session, storage)
    service.complete_upload(upload.upload_session_id)

    worker = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.CLEAN),
        bucket_name="medclaimiq",
    )
    processed = worker.process(upload.upload_session_id)
    evidence = EvidenceRepository(session, "tenant-upload").get(processed.evidence_id)
    events = ProcessingEventRepository(session, "tenant-upload").list_for_aggregate(upload.upload_session_id)

    assert processed.status == UploadSessionStatus.ACCEPTED.value
    assert processed.accepted_object_key is not None
    assert processed.accepted_object_key.startswith("accepted/tenant-upload/")
    assert ("medclaimiq", upload.quarantine_object_key) not in storage.objects
    assert evidence is not None
    assert evidence.status == "accepted"
    assert evidence.content_sha256 == sha256(b"%PDF-1.7\nsynthetic evidence\n").hexdigest()
    assert evidence.media_metadata["format"] == "pdf"
    assert IngestionEventType.PROCESSING_REQUESTED.value in [event.event_type for event in events]


def test_infected_object_never_becomes_evidence(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    service, upload, _ = initiate_pdf(session, storage)
    service.complete_upload(upload.upload_session_id)
    worker = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.INFECTED),
        bucket_name="medclaimiq",
    )

    processed = worker.process(upload.upload_session_id)
    assert processed.status == UploadSessionStatus.REJECTED.value
    assert processed.rejection_code == "malware_detected"
    assert processed.evidence_id is None
    assert EvidenceRepository(session, "tenant-upload").list_for_claim(upload.claim_id) == []
    assert ("medclaimiq", upload.quarantine_object_key) in storage.objects


def test_magic_byte_spoofing_is_rejected_before_malware_acceptance(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    fake_pdf = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    service, upload, _ = initiate_pdf(session, storage, body=fake_pdf, idempotency="upload-request-spoof")
    service.complete_upload(upload.upload_session_id)
    worker = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.CLEAN),
        bucket_name="medclaimiq",
    )

    processed = worker.process(upload.upload_session_id)
    assert processed.status == UploadSessionStatus.REJECTED.value
    assert processed.rejection_code == "content_type_spoofing"
    assert processed.evidence_id is None


def test_duplicate_content_links_existing_evidence_without_duplicate_object(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    body = b"%PDF-1.7\nidentical evidence\n"
    service1, upload1, _ = initiate_pdf(session, storage, body=body, idempotency="upload-request-dup-1")
    service1.complete_upload(upload1.upload_session_id)
    worker1 = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.CLEAN),
        bucket_name="medclaimiq",
    )
    worker1.process(upload1.upload_session_id)

    service2, upload2, _ = initiate_pdf(session, storage, body=body, idempotency="upload-request-dup-2")
    service2.complete_upload(upload2.upload_session_id)
    worker2 = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.CLEAN),
        bucket_name="medclaimiq",
    )
    worker2.process(upload2.upload_session_id)

    assert upload2.status == UploadSessionStatus.DUPLICATE.value
    assert upload2.evidence_id == upload1.evidence_id
    assert len(EvidenceRepository(session, "tenant-upload").list_for_claim(upload1.claim_id)) == 1
    assert ("medclaimiq", upload2.quarantine_object_key) not in storage.objects


def test_upload_repository_is_tenant_scoped(session: Session) -> None:
    bootstrap_claim(session, "tenant-upload-a", "user-upload-a")
    bootstrap_claim(session, "tenant-upload-b", "user-upload-b")
    storage = FakeObjectStorage()
    body = b"%PDF-1.7\ntenant evidence\n"
    service = EvidenceIngestionService(session, "tenant-upload-a", storage=storage, bucket_name="medclaimiq")
    upload, _ = service.initiate_upload(
        claim_id="tenant-upload-a-claim",
        user_id="user-upload-a",
        source_type=EvidenceSourceType.USER_UPLOAD,
        idempotency_key="upload-request-tenant-a",
        payload=UploadInitiateRequest(
            client_filename="evidence.pdf",
            document_type="medical_bill",
            declared_media_type="application/pdf",
            expected_byte_size=len(body),
        ),
    )
    assert UploadSessionRepository(session, "tenant-upload-a").get(upload.upload_session_id) is not None
    assert UploadSessionRepository(session, "tenant-upload-b").get(upload.upload_session_id) is None


def test_png_dimensions_are_captured_as_server_metadata(session: Session) -> None:
    bootstrap_claim(session)
    storage = FakeObjectStorage()
    # PNG signature + IHDR length/type + width=640, height=480 is enough for the basic probe.
    body = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (480).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00" + b"x" * 20
    service = EvidenceIngestionService(session, "tenant-upload", storage=storage, bucket_name="medclaimiq")
    upload, signed = service.initiate_upload(
        claim_id="tenant-upload-claim",
        user_id="user-upload",
        source_type=EvidenceSourceType.USER_UPLOAD,
        idempotency_key="upload-request-png",
        payload=UploadInitiateRequest(
            client_filename="scan.png",
            document_type="medical_bill_image",
            declared_media_type="image/png",
            expected_byte_size=len(body),
            expected_sha256=sha256(body).hexdigest(),
        ),
    )
    metadata = {
        key.removeprefix("x-amz-meta-"): value
        for key, value in signed.form_fields.items()
        if key.startswith("x-amz-meta-")
    }
    storage.put(bucket="medclaimiq", key=upload.quarantine_object_key, body=body, content_type="image/png", metadata=metadata)
    service.complete_upload(upload.upload_session_id)
    worker = EvidenceIngestionWorker(
        session,
        "tenant-upload",
        storage=storage,
        scanner=FakeScanner(MalwareVerdict.CLEAN),
        bucket_name="medclaimiq",
    )
    worker.process(upload.upload_session_id)
    evidence = EvidenceRepository(session, "tenant-upload").get(upload.evidence_id)
    assert evidence.media_metadata["width"] == 640
    assert evidence.media_metadata["height"] == 480

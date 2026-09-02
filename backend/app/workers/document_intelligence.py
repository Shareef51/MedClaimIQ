from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import PurePosixPath
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_intelligence.isolation import ParserIsolationError, SubprocessParserExecutor
from app.document_intelligence.normalization import normalized_manifest, unit_hash
from app.domain.claims import ActorType, EvidenceRelationship, EvidenceSourceType, EvidenceStatus
from app.domain.document_intelligence import ExtractionEventType, ExtractionRunStatus, RetryPolicy
from app.models.document_intelligence import DocumentExtractionRunModel, ExtractionDeadLetterModel, ExtractionUnitModel
from app.repositories.claims import EvidenceRepository
from app.repositories.document_intelligence import DocumentExtractionRunRepository, ExtractionDeadLetterRepository, ExtractionUnitRepository
from app.repositories.ingestion import EvidenceOutboxRepository, ProcessingEventRepository
from app.services.claims import ClaimDomainService
from app.schemas.claims import EvidenceCreate, EvidenceLineageCreate
from app.storage.object_store import ObjectStorage
from app.models.ingestion import EvidenceEventOutboxModel, EvidenceProcessingEventModel


def _now() -> datetime: return datetime.now(timezone.utc)


class DocumentIntelligenceInvariantError(RuntimeError): pass


class DocumentIntelligenceWorker:
    def __init__(self, session: Session, tenant_id: str, *, storage: ObjectStorage, bucket_name: str, parser: SubprocessParserExecutor | None = None, pipeline_version: str = "document-intelligence-v1", retry_policy: RetryPolicy | None = None, max_input_bytes: int = 500 * 1024 * 1024) -> None:
        self.session=session; self.tenant_id=tenant_id; self.storage=storage; self.bucket_name=bucket_name
        self.parser=parser or SubprocessParserExecutor(); self.pipeline_version=pipeline_version; self.retry_policy=retry_policy or RetryPolicy(); self.max_input_bytes=max_input_bytes
        self.runs=DocumentExtractionRunRepository(session,tenant_id); self.units=ExtractionUnitRepository(session,tenant_id); self.dlq=ExtractionDeadLetterRepository(session,tenant_id)
        self.evidence=EvidenceRepository(session,tenant_id); self.events=ProcessingEventRepository(session,tenant_id); self.outbox=EvidenceOutboxRepository(session,tenant_id); self.claim_domain=ClaimDomainService(session,tenant_id)

    def process(self, evidence_id: str, *, requested_by_event_id: str | None = None, trace_id: str | None = None, attempt_number: int = 1) -> DocumentExtractionRunModel:
        key=f"extract:{evidence_id}:{self.pipeline_version}:attempt:{attempt_number}"
        existing=self.runs.get_by_idempotency(key)
        if existing: return existing
        evidence=self.evidence.get(evidence_id)
        if evidence is None: raise DocumentIntelligenceInvariantError("evidence not found in tenant")
        if evidence.status not in {EvidenceStatus.ACCEPTED.value, EvidenceStatus.PROCESSING.value, EvidenceStatus.READY.value}: raise DocumentIntelligenceInvariantError("only accepted evidence may enter document intelligence")
        run=self.runs.add(DocumentExtractionRunModel(run_id=f"xrun_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=evidence.claim_id,evidence_id=evidence.evidence_id,requested_by_event_id=requested_by_event_id,media_type=evidence.media_type,pipeline_version=self.pipeline_version,status=ExtractionRunStatus.RUNNING.value,attempt_number=attempt_number,unit_count=0,warnings=[],parser_metadata={},idempotency_key=key,trace_id=trace_id,started_at=_now()))
        try:
            content=self._read_verified_object(evidence.object_key,evidence.byte_size)
            suffix=PurePosixPath(evidence.object_key).suffix or self._suffix_for_media(evidence.media_type)
            bundle=self.parser.parse_bytes(content,evidence_id=evidence.evidence_id,media_type=evidence.media_type,suffix=suffix)
            if not bundle.units: raise DocumentIntelligenceInvariantError("parser returned no usable extraction units")
            rows=[]
            for unit in bundle.units:
                c=unit.citation
                rows.append(ExtractionUnitModel(unit_id=f"xunit_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=evidence.claim_id,run_id=run.run_id,source_evidence_id=evidence.evidence_id,unit_type=unit.unit_type.value,sequence=unit.sequence,text_content=unit.text,structured_data=unit.structured_data,confidence=Decimal(str(unit.confidence)),page_number=c.page_number,start_ms=c.start_ms,end_ms=c.end_ms,bbox=list(c.bbox) if c.bbox else None,source_locator=c.source_locator,citation_anchor={"evidence_id":c.evidence_id,"page_number":c.page_number,"start_ms":c.start_ms,"end_ms":c.end_ms,"bbox":list(c.bbox) if c.bbox else None,"frame_index":c.frame_index,"frame_sha256":c.frame_sha256,"source_locator":c.source_locator},content_sha256=unit_hash(unit.text,unit.structured_data),created_at=_now()))
            self.units.add_all(rows)
            manifest=normalized_manifest(bundle,source_evidence_id=evidence.evidence_id); digest=hashlib.sha256(manifest).hexdigest()
            derived_key=f"derived/{self.tenant_id}/{evidence.claim_id}/{evidence.evidence_id}/{run.run_id}.extraction.json"
            stored=self.storage.put_object(bucket=self.bucket_name,key=derived_key,body=manifest,content_type="application/vnd.medclaimiq.extraction+json",metadata={"tenant-id":self.tenant_id,"claim-id":evidence.claim_id,"source-evidence-id":evidence.evidence_id,"extraction-run-id":run.run_id})
            derived_id=f"ev_{uuid4().hex}"
            derived=self.claim_domain.add_evidence(EvidenceCreate(evidence_id=derived_id,claim_id=evidence.claim_id,source_type=EvidenceSourceType.GENERATED_DERIVATIVE,source_system="medclaimiq-document-intelligence",source_locator={"extraction_run_id":run.run_id,"source_evidence_id":evidence.evidence_id},document_type=f"{evidence.document_type}_normalized_extraction",media_type="application/vnd.medclaimiq.extraction+json",object_key=derived_key,storage_etag=stored.etag,storage_version_id=stored.version_id,content_sha256=digest,byte_size=len(manifest),status=EvidenceStatus.READY,authoritative=False,media_metadata={"unit_count":len(rows),"aggregate_confidence":bundle.aggregate_confidence,"parser":bundle.parser_name},verified_at=_now(),actor_type=ActorType.WORKER,actor_id="document-intelligence-worker",idempotency_key=f"derived:{run.run_id}",trace_id=trace_id))
            self.claim_domain.add_evidence_lineage(EvidenceLineageCreate(lineage_id=f"lin_{uuid4().hex}",child_evidence_id=derived.evidence_id,parent_evidence_id=evidence.evidence_id,relationship=EvidenceRelationship.DERIVED_FROM,transformation_name=bundle.parser_name,transformation_version=bundle.parser_version,transformation_metadata={"pipeline_version":self.pipeline_version,"run_id":run.run_id,"aggregate_confidence":bundle.aggregate_confidence}))
            run.status=ExtractionRunStatus.SUCCEEDED.value; run.parser_name=bundle.parser_name; run.parser_version=bundle.parser_version; run.aggregate_confidence=Decimal(str(bundle.aggregate_confidence)); run.unit_count=len(rows); run.warnings=list(bundle.warnings); run.parser_metadata=bundle.metadata; run.derived_evidence_id=derived.evidence_id; run.completed_at=_now(); run.retryable=False
            self._event(evidence.claim_id,evidence.evidence_id,ExtractionEventType.SUCCEEDED.value,f"extraction:succeeded:{run.run_id}",{"run_id":run.run_id,"derived_evidence_id":derived.evidence_id,"unit_count":len(rows),"aggregate_confidence":bundle.aggregate_confidence},trace_id)
            return run
        except Exception as exc:
            return self._handle_failure(run, evidence.claim_id, evidence.evidence_id, exc, trace_id)

    def _read_verified_object(self,key: str,expected_size: int) -> bytes:
        if expected_size > self.max_input_bytes: raise DocumentIntelligenceInvariantError("evidence exceeds parser input limit")
        body=bytearray()
        for chunk in self.storage.iter_object_chunks(bucket=self.bucket_name,key=key):
            body.extend(chunk)
            if len(body)>self.max_input_bytes: raise DocumentIntelligenceInvariantError("evidence exceeded parser input limit while streaming")
        if len(body)!=expected_size: raise DocumentIntelligenceInvariantError("accepted evidence object size no longer matches provenance")
        return bytes(body)

    def _handle_failure(self,run,claim_id,evidence_id,exc,trace_id):
        retryable=isinstance(exc, (ParserIsolationError, TimeoutError, OSError))
        run.error_code=type(exc).__name__.lower()[:80]; run.error_detail=str(exc)[:2000]; run.retryable=retryable; run.completed_at=_now()
        if retryable and not self.retry_policy.should_dead_letter(run.attempt_number):
            run.status=ExtractionRunStatus.RETRY_PENDING.value; run.next_attempt_at=_now()+timedelta(seconds=self.retry_policy.delay_seconds(run.attempt_number)); event=ExtractionEventType.RETRY_SCHEDULED
        elif retryable:
            run.status=ExtractionRunStatus.DEAD_LETTERED.value; run.next_attempt_at=None; self.dlq.add(ExtractionDeadLetterModel(dead_letter_id=f"xdlq_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,evidence_id=evidence_id,run_id=run.run_id,error_code=run.error_code,error_detail=run.error_detail,replay_payload={"evidence_id":evidence_id,"pipeline_version":self.pipeline_version,"next_attempt":run.attempt_number+1},trace_id=trace_id)); event=ExtractionEventType.DEAD_LETTERED
        else:
            run.status=ExtractionRunStatus.FAILED.value; event=ExtractionEventType.FAILED
        self._event(claim_id,evidence_id,event.value,f"extraction:{event.value}:{run.run_id}",{"run_id":run.run_id,"error_code":run.error_code,"retryable":retryable,"attempt_number":run.attempt_number},trace_id)
        return run

    def _event(self,claim_id,evidence_id,event_type,key,payload,trace_id):
        existing=self.events.get_by_idempotency(key)
        if existing is not None:
            return existing
        now=_now()
        event=self.events.add(EvidenceProcessingEventModel(event_id=f"evt_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type="evidence",aggregate_id=evidence_id,event_type=event_type,payload=payload,trace_id=trace_id,idempotency_key=key,occurred_at=now))
        self.outbox.add(EvidenceEventOutboxModel(outbox_id=f"out_{uuid4().hex}",tenant_id=self.tenant_id,event_id=event.event_id,topic="medclaimiq.evidence.events.v1",partition_key=claim_id,status="pending",attempt_count=0,available_at=now))
        return event

    @staticmethod
    def _suffix_for_media(media_type: str) -> str:
        return {"application/pdf":".pdf","application/json":".json","text/csv":".csv","image/png":".png","image/jpeg":".jpg","audio/mpeg":".mp3","audio/wav":".wav","video/mp4":".mp4"}.get(media_type,".bin")

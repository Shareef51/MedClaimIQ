from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.appeal_reconsideration import (
    AppealCheckpointStatus, AppealComparisonType, AppealEscalationLevel,
    AppealEvidenceSnapshotStatus, AppealReingestionStatus, ReconsiderationRecommendation,
)
from app.domain.post_decision import AppealStatus
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.appeal_reconsideration import (
    AppealEvidenceComparisonModel, AppealEvidenceReingestionModel, AppealEvidenceSnapshotModel,
    AppealEscalationModel, AppealMissingEvidenceRequestModel, AppealRAGItemModel, AppealRAGRunModel,
    AppealReconsiderationCheckpointModel, AppealReconsiderationRunModel, AppealReviewerAnnotationModel,
)
from app.models.claims import EvidenceArtifactModel
from app.models.document_intelligence import DocumentExtractionRunModel, ExtractionUnitModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.models.governed_closure import ReviewDecisionPacketModel
from app.models.ingestion import EvidenceUploadSessionModel, MalwareScanModel
from app.models.post_decision import AppealCaseModel, AppealSupplementalEvidenceModel
from app.repositories.appeal_reconsideration import AppealReconsiderationRepository
from app.repositories.post_decision import PostDecisionRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError

_TOKEN=re.compile(r"[a-z0-9]{2,}",re.I)
MATERIAL_FIELDS={"amount","total","total_amount","service_date","date","provider","provider_id","patient","patient_id","code","service_code","units","diagnosis","procedure","status"}


def _now()->datetime: return datetime.now(UTC)
def _canonical(value:object)->str: return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)
def _sha(value:object)->str: return hashlib.sha256((value if isinstance(value,str) else _canonical(value)).encode()).hexdigest()


class AppealReconsiderationService:
    """Appeal evidence re-ingestion and recommendation-only decision support.

    This service deliberately has no dependency on GovernedClosureService.resolve or
    PostDecisionService.resolve_appeal. It can validate/index/compare/retrieve evidence,
    prepare recommendations, persist human-review checkpoints and annotations, and
    request/escalate review work. It cannot create or change a controlling claim outcome.
    """

    def __init__(self, session:Session, tenant_id:str, *, embedder=None, embedding_model:str="text-embedding-3-large", embedding_dimensions:int=1536, index_version:str="appeal-rag-v1") -> None:
        self.session=session; self.tenant_id=tenant_id; self.repo=AppealReconsiderationRepository(session,tenant_id)
        self.post=PostDecisionRepository(session,tenant_id); self.embedder=embedder
        self.embedding_model=embedding_model; self.embedding_dimensions=embedding_dimensions; self.index_version=index_version

    def _appeal(self,claim_id:str,appeal_id:str,*,for_update:bool=False)->AppealCaseModel:
        appeal=self.post.appeal(appeal_id,for_update=for_update)
        if appeal is None or appeal.claim_id!=claim_id: raise LookupError("appeal not found")
        return appeal

    def _require_reviewer(self,user_id:str)->None:
        membership=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if membership is None or membership.status!="active" or membership.role!="claims_reviewer":
            raise ReviewConflictError("active human claims reviewer membership required")

    def _require_assigned(self,appeal:AppealCaseModel,user_id:str)->None:
        self._require_reviewer(user_id)
        if appeal.assigned_reviewer_user_id!=user_id:
            raise ReviewConflictError("only the independent assigned appeal reviewer may perform this review action")

    def authorize_independent_reviewer(self,claim_id:str,appeal_id:str,user_id:str)->AppealCaseModel:
        appeal=self._appeal(claim_id,appeal_id)
        self._require_assigned(appeal,user_id)
        return appeal

    def _packet(self,appeal:AppealCaseModel)->ReviewDecisionPacketModel:
        packet=self.session.scalar(select(ReviewDecisionPacketModel).where(
            ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.packet_id==appeal.original_packet_id,
        ))
        if packet is None or packet.status!="closed" or not packet.decision_id or not packet.evidence_snapshot_sha256:
            raise ReviewConflictError("appeal requires an immutable closed original human decision packet")
        return packet

    def _emit(self,claim_id:str,event_type:str,appeal_id:str,metadata:dict,trace_id:str|None=None):
        safe={k:v for k,v in metadata.items() if k in {"appeal_id","status","stage","snapshot_id","run_id","modality","progress","requires_human_review"}}
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(
            event_id=f"are_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,
            aggregate_type="appeal_reconsideration",aggregate_id=appeal_id,occurred_at=_now(),trace_id=trace_id,
            producer="medclaimiq-appeal-reconsideration",payload=metadata,metadata=safe,
        ),topic=EventTopic.CLAIMS.value)

    @staticmethod
    def _modality(media_type:str,document_type:str="")->str:
        m=(media_type or "").lower(); d=(document_type or "").lower()
        if "fhir" in m or "fhir" in d: return "fhir"
        if m.startswith("image/"): return "image"
        if m.startswith("audio/"): return "audio"
        if m.startswith("video/"): return "video"
        if "csv" in m or "spreadsheet" in m or "invoice" in d or "bill" in d: return "table"
        return "document"

    def register_linked_evidence(self,claim_id:str,appeal_id:str,evidence_id:str,*,trace_id:str|None=None)->AppealEvidenceReingestionModel:
        appeal=self._appeal(claim_id,appeal_id)
        link=self.session.scalar(select(AppealSupplementalEvidenceModel).where(
            AppealSupplementalEvidenceModel.tenant_id==self.tenant_id,AppealSupplementalEvidenceModel.appeal_id==appeal_id,
            AppealSupplementalEvidenceModel.evidence_id==evidence_id,
        ))
        if link is None: raise ReviewConflictError("evidence is not linked to this appeal")
        evidence=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,EvidenceArtifactModel.claim_id==claim_id))
        if evidence is None: raise LookupError("supplemental evidence not found")
        existing=self.repo.reingestion(appeal_id,"evidence",evidence_id,str(evidence.evidence_version))
        if existing:return existing
        row=self.repo.add(AppealEvidenceReingestionModel(
            reingestion_id=f"ari_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal.appeal_id,
            source_kind="evidence",source_id=evidence.evidence_id,source_version=str(evidence.evidence_version),
            modality=self._modality(evidence.media_type,evidence.document_type),media_type=evidence.media_type,content_sha256=evidence.content_sha256,
            file_validation_status="pending",malware_verdict="pending",extraction_status="pending",chunk_count=0,chunk_manifest=[],
            embedding_model=self.embedding_model,embedding_dimensions=self.embedding_dimensions,embedding_input_sha256s=[],
            index_version=self.index_version,retrieval_namespace=f"appeal:{appeal_id}",status=AppealReingestionStatus.PENDING.value,
            error_code=None,error_detail=None,trace_id=trace_id,started_at=_now(),completed_at=None,
        ))
        self._emit(claim_id,"appeal.reconsideration.reingestion.queued",appeal_id,{"appeal_id":appeal_id,"status":row.status,"modality":row.modality,"progress":0},trace_id)
        return row

    def _malware_verdict(self,evidence:EvidenceArtifactModel)->str:
        upload=self.session.scalar(select(EvidenceUploadSessionModel).where(
            EvidenceUploadSessionModel.tenant_id==self.tenant_id,EvidenceUploadSessionModel.evidence_id==evidence.evidence_id,
        ).order_by(EvidenceUploadSessionModel.created_at.desc()).limit(1))
        if upload is None:
            # EvidenceArtifact status=ready is only reachable after the accepted evidence boundary;
            # imported/synthetic/system evidence may not retain an upload session.
            return "accepted_boundary_inherited"
        scan=self.session.scalar(select(MalwareScanModel).where(
            MalwareScanModel.tenant_id==self.tenant_id,MalwareScanModel.upload_session_id==upload.upload_session_id,
        ).order_by(MalwareScanModel.attempt_number.desc()).limit(1))
        if scan is None: return "missing_scan"
        return str(scan.verdict)

    def _evidence_units(self,evidence_id:str)->list[tuple[ExtractionUnitModel,DocumentExtractionRunModel]]:
        return list(self.session.execute(select(ExtractionUnitModel,DocumentExtractionRunModel).join(
            DocumentExtractionRunModel,DocumentExtractionRunModel.run_id==ExtractionUnitModel.run_id,
        ).where(
            ExtractionUnitModel.tenant_id==self.tenant_id,ExtractionUnitModel.source_evidence_id==evidence_id,
            DocumentExtractionRunModel.tenant_id==self.tenant_id,DocumentExtractionRunModel.status=="succeeded",
        ).order_by(DocumentExtractionRunModel.completed_at.desc(),ExtractionUnitModel.sequence)).all())

    def process_reingestion(self,claim_id:str,appeal_id:str,evidence_id:str,*,trace_id:str|None=None)->AppealEvidenceReingestionModel:
        evidence=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,EvidenceArtifactModel.claim_id==claim_id))
        if evidence is None: raise LookupError("supplemental evidence not found")
        row=self.register_linked_evidence(claim_id,appeal_id,evidence_id,trace_id=trace_id)
        if row.status==AppealReingestionStatus.READY.value:return row
        row.status=AppealReingestionStatus.VALIDATING.value
        if evidence.status!="ready" or len(evidence.content_sha256)!=64 or evidence.byte_size<=0:
            row.file_validation_status="blocked";row.malware_verdict="not_evaluated";row.status=AppealReingestionStatus.BLOCKED.value;row.error_code="evidence_not_ready";row.error_detail="supplemental evidence must pass quarantine/file validation before appeal use";row.completed_at=_now();self.session.flush();return row
        verdict=self._malware_verdict(evidence); row.malware_verdict=verdict
        if verdict.lower() in {"infected","malicious","suspicious","error","missing_scan"}:
            row.file_validation_status="blocked";row.status=AppealReingestionStatus.BLOCKED.value;row.error_code="malware_validation_failed";row.error_detail="evidence did not satisfy malware validation";row.completed_at=_now();self.session.flush();return row
        row.file_validation_status="passed";row.status=AppealReingestionStatus.EXTRACTING.value
        units=self._evidence_units(evidence_id)
        chunks=[]
        # Keep every chunk version-bound to the accepted evidence version and exact extraction locator.
        seen=set()
        for unit,run in units:
            text=(unit.text_content or "").strip()
            structured=dict(unit.structured_data or {})
            if not text and structured:text=_canonical(structured)
            if not text:continue
            key=(unit.unit_id,run.pipeline_version)
            if key in seen:continue
            seen.add(key)
            citation={"evidence_id":evidence.evidence_id,"evidence_version":evidence.evidence_version,"extraction_unit_id":unit.unit_id,"page_number":unit.page_number,"bbox":unit.bbox,"start_ms":unit.start_ms,"end_ms":unit.end_ms,"source_locator":unit.source_locator}
            chunks.append({"chunk_id":f"appeal:{appeal_id}:{unit.unit_id}","source_version":str(evidence.evidence_version),"pipeline_version":run.pipeline_version,"text":text[:12000],"content_sha256":unit.content_sha256,"structured_data":structured,"citation":citation})
        if not chunks:
            metadata_text=_canonical({"document_type":evidence.document_type,"media_type":evidence.media_type,"source_system":evidence.source_system,"source_locator":evidence.source_locator,"media_metadata":evidence.media_metadata})
            chunks=[{"chunk_id":f"appeal:{appeal_id}:metadata:{evidence.evidence_id}:v{evidence.evidence_version}","source_version":str(evidence.evidence_version),"pipeline_version":"metadata-fallback-v1","text":metadata_text,"content_sha256":_sha(metadata_text),"structured_data":dict(evidence.media_metadata or {}),"citation":{"evidence_id":evidence.evidence_id,"evidence_version":evidence.evidence_version,"source_locator":evidence.source_locator}}]
            row.extraction_status="metadata_only"
        else: row.extraction_status="succeeded"
        row.status=AppealReingestionStatus.INDEXING.value
        texts=[c["text"] for c in chunks]
        input_hashes=[_sha(f"{self.embedding_model}|{self.embedding_dimensions}|{t.replace(chr(10),' ').strip()}") for t in texts]
        if self.embedder is not None:
            vectors=self.embedder.embed(texts)
            if len(vectors)!=len(texts) or any(len(v)!=self.embedding_dimensions for v in vectors):
                row.status=AppealReingestionStatus.FAILED.value;row.error_code="embedding_shape_mismatch";row.error_detail="embedding provider returned invalid appeal index vectors";row.completed_at=_now();self.session.flush();return row
        row.chunk_manifest=[{k:v for k,v in c.items() if k!="text"}|{"text_preview":c["text"][:800]} for c in chunks]
        row.chunk_count=len(chunks);row.embedding_input_sha256s=input_hashes;row.status=AppealReingestionStatus.READY.value;row.completed_at=_now();self.session.flush()
        self._emit(claim_id,"appeal.reconsideration.reingestion.completed",appeal_id,{"appeal_id":appeal_id,"status":row.status,"modality":row.modality,"progress":100},trace_id)
        return row

    def register_fhir_updates(self,claim_id:str,appeal_id:str,*,trace_id:str|None=None)->list[AppealEvidenceReingestionModel]:
        appeal=self._appeal(claim_id,appeal_id)
        snapshots=list(self.session.scalars(select(FHIRResourceSnapshotModel).where(
            FHIRResourceSnapshotModel.tenant_id==self.tenant_id,FHIRResourceSnapshotModel.claim_id==claim_id,
            FHIRResourceSnapshotModel.fetched_at>=appeal.submitted_at,
        ).order_by(FHIRResourceSnapshotModel.fetched_at)))
        rows=[]
        for fhir in snapshots:
            existing=self.repo.reingestion(appeal_id,"fhir",fhir.snapshot_id,fhir.version_id)
            if existing:rows.append(existing);continue
            text=_canonical(fhir.canonical_resource or fhir.raw_resource or {})
            citation={"fhir_snapshot_id":fhir.snapshot_id,"fhir_resource_type":fhir.resource_type,"fhir_logical_id":fhir.logical_id,"fhir_version_id":fhir.version_id}
            row=self.repo.add(AppealEvidenceReingestionModel(
                reingestion_id=f"ari_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,source_kind="fhir",source_id=fhir.snapshot_id,source_version=fhir.version_id,
                modality="fhir",media_type="application/fhir+json",content_sha256=fhir.content_sha256,file_validation_status="trusted_fhir_gateway",malware_verdict="not_applicable",
                extraction_status="canonical_fhir",chunk_count=1,chunk_manifest=[{"chunk_id":f"appeal:{appeal_id}:fhir:{fhir.snapshot_id}","source_version":fhir.version_id,"pipeline_version":"fhir-canonical-v1","content_sha256":_sha(text),"structured_data":fhir.canonical_resource or {},"citation":citation,"text_preview":text[:800]}],
                embedding_model=self.embedding_model,embedding_dimensions=self.embedding_dimensions,embedding_input_sha256s=[_sha(f"{self.embedding_model}|{self.embedding_dimensions}|{text}")],index_version=self.index_version,retrieval_namespace=f"appeal:{appeal_id}",status=AppealReingestionStatus.READY.value,error_code=None,error_detail=None,trace_id=trace_id,started_at=_now(),completed_at=_now(),
            ));rows.append(row)
        if rows:self._emit(claim_id,"appeal.reconsideration.fhir.updated",appeal_id,{"appeal_id":appeal_id,"status":"ready","modality":"fhir","progress":100},trace_id)
        return rows

    def _source_entry_from_evidence(self,evidence_id:str,source_scope:str)->dict:
        ev=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id))
        if ev is None:return {"source_scope":source_scope,"source_kind":"evidence","source_id":evidence_id,"missing":True}
        return {"source_scope":source_scope,"source_kind":"evidence","source_id":ev.evidence_id,"source_version":str(ev.evidence_version),"content_sha256":ev.content_sha256,"media_type":ev.media_type,"document_type":ev.document_type,"modality":self._modality(ev.media_type,ev.document_type)}

    def build_snapshot(self,claim_id:str,appeal_id:str,actor_id:str,actor_type:str="human",*,trace_id:str|None=None)->AppealEvidenceSnapshotModel:
        appeal=self._appeal(claim_id,appeal_id);packet=self._packet(appeal)
        if actor_type=="human": self._require_assigned(appeal,actor_id)
        # Every linked supplemental evidence source must be reprocessed and ready before it enters a locked snapshot.
        links=self.post.supplemental(appeal_id)
        for link in links:self.process_reingestion(claim_id,appeal_id,link.evidence_id,trace_id=trace_id)
        self.register_fhir_updates(claim_id,appeal_id,trace_id=trace_id)
        reingestions=self.repo.reingestions(appeal_id)
        blocked=[x for x in reingestions if x.source_kind=="evidence" and x.status!=AppealReingestionStatus.READY.value]
        if blocked: raise ReviewConflictError("appeal evidence snapshot cannot lock while supplemental evidence re-ingestion is blocked or incomplete")
        original=[]
        for item in packet.evidence_snapshot or []:
            eid=item.get("evidence_id")
            if eid:original.append(self._source_entry_from_evidence(eid,"original"))
        supplemental=[]
        for row in reingestions:
            supplemental.append({"source_scope":"supplemental","source_kind":row.source_kind,"source_id":row.source_id,"source_version":row.source_version,"content_sha256":row.content_sha256,"media_type":row.media_type,"modality":row.modality,"reingestion_id":row.reingestion_id,"chunk_count":row.chunk_count})
        payload={"appeal_id":appeal_id,"original_decision_id":appeal.original_decision_id,"original_evidence_snapshot_sha256":packet.evidence_snapshot_sha256,"original_sources":original,"supplemental_sources":supplemental}
        digest=_sha(payload);existing=self.session.scalar(select(AppealEvidenceSnapshotModel).where(AppealEvidenceSnapshotModel.tenant_id==self.tenant_id,AppealEvidenceSnapshotModel.snapshot_sha256==digest))
        if existing:return existing
        prior=self.repo.latest_snapshot(appeal_id)
        if prior and prior.status==AppealEvidenceSnapshotStatus.LOCKED.value: prior.status=AppealEvidenceSnapshotStatus.SUPERSEDED.value
        row=self.repo.add(AppealEvidenceSnapshotModel(
            snapshot_id=f"aes_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,snapshot_version=self.repo.next_snapshot_version(appeal_id),
            original_decision_id=appeal.original_decision_id,original_evidence_snapshot_sha256=packet.evidence_snapshot_sha256,original_sources=original,supplemental_sources=supplemental,
            modalities=sorted({str(x.get("modality")) for x in [*original,*supplemental] if x.get("modality")}),source_count=len(original)+len(supplemental),snapshot_sha256=digest,
            status=AppealEvidenceSnapshotStatus.LOCKED.value,created_by_actor_type=actor_type,created_by_actor_id=actor_id,trace_id=trace_id,created_at=_now(),locked_at=_now(),
        ))
        self._compare_snapshot(row)
        self._emit(claim_id,"appeal.reconsideration.snapshot.locked",appeal_id,{"appeal_id":appeal_id,"status":row.status,"snapshot_id":row.snapshot_id,"progress":100},trace_id)
        return row

    def _chunk_records_for_evidence(self,evidence_id:str)->list[dict]:
        evidence=self.session.scalar(select(EvidenceArtifactModel).where(
            EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,
        ))
        source_version=str(evidence.evidence_version) if evidence is not None else "unknown"
        records=[]
        for unit,run in self._evidence_units(evidence_id):
            text=(unit.text_content or "").strip();structured=dict(unit.structured_data or {})
            if not text and structured:text=_canonical(structured)
            if not text:continue
            records.append({"source_id":evidence_id,"source_version":source_version,"text":text,"structured":structured,"content_sha256":unit.content_sha256,"citation":{"evidence_id":evidence_id,"evidence_version":None if evidence is None else evidence.evidence_version,"extraction_unit_id":unit.unit_id,"extraction_pipeline_version":run.pipeline_version,"page_number":unit.page_number,"bbox":unit.bbox,"start_ms":unit.start_ms,"end_ms":unit.end_ms,"source_locator":unit.source_locator}})
        return records

    def _all_chunks(self,snapshot:AppealEvidenceSnapshotModel)->list[dict]:
        chunks=[]
        for src in snapshot.original_sources or []:
            if src.get("source_kind")!="evidence" or src.get("missing"):continue
            recs=self._chunk_records_for_evidence(src["source_id"])
            if not recs:
                recs=[{"source_id":src["source_id"],"source_version":src.get("source_version",""),"text":_canonical(src),"structured":{},"content_sha256":src.get("content_sha256") or _sha(src),"citation":{"evidence_id":src["source_id"],"evidence_version":src.get("source_version")}}]
            for r in recs:r["source_scope"]="original";r["modality"]=src.get("modality","document");chunks.append(r)
        for reing in self.repo.reingestions(snapshot.appeal_id):
            if reing.status!=AppealReingestionStatus.READY.value:continue
            for c in reing.chunk_manifest or []:
                chunks.append({"source_scope":"supplemental","source_id":reing.source_id,"source_version":reing.source_version,"modality":reing.modality,"text":c.get("text_preview","") or _canonical(c.get("structured_data") or {}),"structured":c.get("structured_data") or {},"content_sha256":c.get("content_sha256") or reing.content_sha256,"citation":c.get("citation") or {}})
        return chunks

    def _compare_snapshot(self,snapshot:AppealEvidenceSnapshotModel)->list[AppealEvidenceComparisonModel]:
        if self.repo.comparisons(snapshot.appeal_id,snapshot.snapshot_id):return self.repo.comparisons(snapshot.appeal_id,snapshot.snapshot_id)
        chunks=self._all_chunks(snapshot);original=[x for x in chunks if x["source_scope"]=="original"];supp=[x for x in chunks if x["source_scope"]=="supplemental"]
        rows=[];original_fields={}
        for item in original:
            for k,v in (item.get("structured") or {}).items():
                if v is not None and str(v).strip():original_fields.setdefault(str(k).lower(),[]).append((str(v),item))
        for item in supp:
            structured=item.get("structured") or {}
            if not structured:
                rows.append(self._comparison(snapshot,AppealComparisonType.ADDED.value,"content",None,item,item["content_sha256"],"info",0.7,"Supplemental appeal evidence adds content not present in the locked original evidence extraction."));continue
            for raw_key,value in structured.items():
                key=str(raw_key).lower();new=str(value)
                priors=original_fields.get(key,[])
                if not priors:
                    rows.append(self._comparison(snapshot,AppealComparisonType.ADDED.value,key,None,item,_sha(new),"info",0.75,f"Supplemental evidence adds a previously unrepresented field: {key}."));continue
                prior_value,prior_item=priors[0]
                if prior_value.strip().lower()==new.strip().lower():
                    rows.append(self._comparison(snapshot,AppealComparisonType.CORROBORATING.value,key,prior_item,item,_sha(new),"info",0.9,f"Supplemental evidence corroborates the original {key} value."))
                else:
                    severity="material" if key in MATERIAL_FIELDS or any(t in key for t in MATERIAL_FIELDS) else "warning"
                    ctype=AppealComparisonType.CONTRADICTORY.value if severity=="material" else AppealComparisonType.CHANGED.value
                    rows.append(self._comparison(snapshot,ctype,key,prior_item,item,_sha(new),severity,0.9 if severity=="material" else 0.8,f"Supplemental evidence changes the original {key} value and requires independent human review."))
        return rows

    def _comparison(self,snapshot,ctype,field,original,item,new_sha,severity,confidence,description):
        row=self.repo.add(AppealEvidenceComparisonModel(
            comparison_id=f"aec_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=snapshot.claim_id,appeal_id=snapshot.appeal_id,snapshot_id=snapshot.snapshot_id,
            comparison_type=ctype,field=field,original_source_ref=None if original is None else original.get("source_id"),supplemental_source_ref=item.get("source_id"),
            original_value_sha256=None if original is None else original.get("content_sha256"),supplemental_value_sha256=new_sha,severity=severity,confidence=confidence,description=description,
            citations=[x for x in [None if original is None else original.get("citation"),item.get("citation")] if x],created_at=_now(),
        ));return row

    @staticmethod
    def _bm25_scores(query:str,texts:list[str],*,k1:float=1.5,b:float=0.75)->list[float]:
        """Deterministic corpus-aware BM25 for the immutable appeal snapshot."""
        q=list(dict.fromkeys(_TOKEN.findall(query.lower())))
        docs=[list(_TOKEN.findall(text.lower())) for text in texts]
        if not q or not docs:return [0.0 for _ in docs]
        avgdl=sum(len(doc) for doc in docs)/max(1,len(docs));n=len(docs)
        df={term:sum(1 for doc in docs if term in set(doc)) for term in q}
        scores=[]
        for doc in docs:
            if not doc:scores.append(0.0);continue
            tf={term:doc.count(term) for term in q};score=0.0
            for term in q:
                freq=tf.get(term,0)
                if not freq:continue
                idf=math.log(1.0+(n-df.get(term,0)+0.5)/(df.get(term,0)+0.5))
                denom=freq+k1*(1.0-b+b*len(doc)/max(avgdl,1e-9))
                score+=idf*((freq*(k1+1.0))/denom)
            scores.append(score)
        ceiling=max(scores) if scores else 0.0
        return [score/ceiling if ceiling>0 else 0.0 for score in scores]

    def search(self,claim_id:str,appeal_id:str,query:str,*,limit:int=12,trace_id:str|None=None)->dict:
        if not query.strip(): raise ValueError("appeal RAG query cannot be empty")
        appeal=self._appeal(claim_id,appeal_id);snapshot=self.repo.latest_snapshot(appeal_id)
        if snapshot is None or snapshot.status!=AppealEvidenceSnapshotStatus.LOCKED.value:
            snapshot=self.build_snapshot(claim_id,appeal_id,appeal.assigned_reviewer_user_id or "system","human" if appeal.assigned_reviewer_user_id else "system",trace_id=trace_id)
        chunks=self._all_chunks(snapshot)
        query_vector=None;chunk_vectors=None
        if self.embedder is not None and chunks:
            query_vector=self.embedder.embed([query])[0];chunk_vectors=self.embedder.embed([x["text"] for x in chunks])
        bm25_scores=self._bm25_scores(query,[item["text"] for item in chunks])
        scored=[]
        for idx,item in enumerate(chunks):
            lexical=bm25_scores[idx] if idx<len(bm25_scores) else 0.0
            dense=0.0
            if query_vector is not None and chunk_vectors is not None:
                v=chunk_vectors[idx];den=sum(a*a for a in query_vector)**0.5*sum(b*b for b in v)**0.5
                dense=sum(a*b for a,b in zip(query_vector,v))/den if den else 0.0
            scope_bonus=0.08 if item["source_scope"]=="supplemental" else 0.02
            score=(0.55*dense+0.37*lexical+scope_bonus) if query_vector is not None else (0.9*lexical+scope_bonus)
            scored.append((score,item))
        scored.sort(key=lambda x:(-x[0],x[1]["source_id"],x[1]["content_sha256"]))
        selected=scored[:max(1,min(30,limit))]
        comparisons=self.repo.comparisons(appeal_id,snapshot.snapshot_id);material=[x for x in comparisons if x.severity=="material"]
        pack_payload=[{"source_scope":x[1]["source_scope"],"source_id":x[1]["source_id"],"source_version":x[1]["source_version"],"content_sha256":x[1]["content_sha256"],"citation":x[1]["citation"]} for x in selected]
        run=self.repo.add(AppealRAGRunModel(
            run_id=f"arr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,snapshot_id=snapshot.snapshot_id,query_sha256=_sha(query),
            strategy="appeal_scoped_hybrid_dense_bm25_reranked",candidate_count=len(chunks),selected_count=len(selected),citation_coverage=sum(1 for _,x in selected if x.get("citation"))/max(1,len(selected)),
            contradiction_count=len(material),changed_fact_count=sum(1 for x in comparisons if x.comparison_type in {"changed","contradictory","added"}),pack_sha256=_sha(pack_payload),trace_id=trace_id,created_at=_now(),
        ))
        items=[]
        for rank,(score,item) in enumerate(selected,1):
            items.append(self.repo.add(AppealRAGItemModel(
                item_id=f"arri_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,run_id=run.run_id,source_scope=item["source_scope"],source_id=item["source_id"],source_version=item["source_version"],modality=item["modality"],rank=rank,score=float(score),content_sha256=item["content_sha256"],text_preview=item["text"][:1800],citation=item["citation"],retrieval_sources=["dense" if query_vector is not None else "dense_unavailable","bm25_lexical","appeal_scope","version_filter"],created_at=_now(),
            )))
        self._emit(claim_id,"appeal.reconsideration.rag.completed",appeal_id,{"appeal_id":appeal_id,"status":"completed","run_id":run.run_id,"progress":100},trace_id)
        return {"run":run,"items":items,"comparisons":comparisons,"snapshot":snapshot}

    def run_reconsideration_agent(self,claim_id:str,appeal_id:str,*,query:str="What supplemental evidence materially changes, contradicts, or corroborates the original claim decision evidence?",trace_id:str|None=None,idempotency_key:str|None=None)->AppealReconsiderationRunModel:
        appeal=self._appeal(claim_id,appeal_id);idempotency_key=idempotency_key or f"agent-{uuid4().hex}"
        existing=self.session.scalar(select(AppealReconsiderationRunModel).where(AppealReconsiderationRunModel.tenant_id==self.tenant_id,AppealReconsiderationRunModel.idempotency_key==idempotency_key))
        if existing:
            if existing.claim_id!=claim_id or existing.appeal_id!=appeal_id: raise ReviewConflictError("idempotency key was already used outside this appeal")
            return existing
        result=self.search(claim_id,appeal_id,query,limit=16,trace_id=trace_id)
        comparisons=result["comparisons"];items=result["items"];material=[x for x in comparisons if x.severity=="material"]
        changed=[x for x in comparisons if x.comparison_type in {"changed","contradictory","added"}]
        if not result["snapshot"].supplemental_sources:
            recommendation=ReconsiderationRecommendation.REQUEST_INFORMATION;missing=["supplemental_evidence"];escalation=[]
        elif material:
            recommendation=ReconsiderationRecommendation.CONSIDER_MODIFY;missing=[];escalation=["material_original_vs_supplemental_conflict"]
        elif changed:
            recommendation=ReconsiderationRecommendation.CONSIDER_MODIFY;missing=[];escalation=[]
        else:
            recommendation=ReconsiderationRecommendation.AFFIRM;missing=[];escalation=[]
        summary=(f"Recommendation-only appeal analysis found {len(changed)} changed/added facts and {len(material)} material contradictions. "
                 "This output is decision support only; the independent authorized human appeal reviewer must determine whether to affirm, modify, overturn, or request information.")
        thread_id=f"appeal:{appeal_id}:reconsideration"
        row=self.repo.add(AppealReconsiderationRunModel(
            reconsideration_run_id=f"arrun_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,snapshot_id=result["snapshot"].snapshot_id,rag_run_id=result["run"].run_id,graph_thread_id=thread_id,
            agent_name="appeal_reconsideration_evidence_analyst",prompt_version="appeal-reconsideration-v1",recommendation=recommendation.value,confidence=0.9 if material else 0.72 if changed else 0.65,
            recommendation_summary=summary,recommendation_sha256=_sha(summary),evidence_refs=[x.item_id for x in items],changed_fact_refs=[x.comparison_id for x in changed],contradiction_refs=[x.comparison_id for x in material],missing_evidence_requests=missing,escalation_reasons=escalation,requires_human_review=True,adjudication_authority="none",trace_id=trace_id,idempotency_key=idempotency_key,created_at=_now(),
        ))
        state={"appeal_id":appeal_id,"snapshot_id":row.snapshot_id,"rag_run_id":row.rag_run_id,"recommendation_run_id":row.reconsideration_run_id,"stage":"human_appeal_review","recommendation":row.recommendation,"adjudication_authority":"none"}
        self.repo.add(AppealReconsiderationCheckpointModel(
            checkpoint_id=f"arcp_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,thread_id=thread_id,checkpoint_version=self.repo.next_checkpoint_version(thread_id),stage="human_appeal_review",status=AppealCheckpointStatus.WAITING.value,state_metadata=state,state_sha256=_sha(state),requires_human_action=True,created_at=_now(),resumed_by_user_id=None,resumed_at=None,
        ))
        self._emit(claim_id,"appeal.reconsideration.agent.completed",appeal_id,{"appeal_id":appeal_id,"status":"waiting_human","run_id":row.reconsideration_run_id,"stage":"human_appeal_review","requires_human_review":True,"progress":100},trace_id)
        return row

    def resume_checkpoint(self,claim_id:str,appeal_id:str,checkpoint_id:str,reviewer_user_id:str)->AppealReconsiderationCheckpointModel:
        appeal=self._appeal(claim_id,appeal_id);self._require_assigned(appeal,reviewer_user_id)
        row=self.session.scalar(select(AppealReconsiderationCheckpointModel).where(AppealReconsiderationCheckpointModel.tenant_id==self.tenant_id,AppealReconsiderationCheckpointModel.checkpoint_id==checkpoint_id,AppealReconsiderationCheckpointModel.appeal_id==appeal_id))
        if row is None:raise LookupError("appeal checkpoint not found")
        if row.status!=AppealCheckpointStatus.WAITING.value:return row
        row.status=AppealCheckpointStatus.RESUMED.value;row.resumed_by_user_id=reviewer_user_id;row.resumed_at=_now();self.session.flush()
        self._emit(claim_id,"appeal.reconsideration.checkpoint.resumed",appeal_id,{"appeal_id":appeal_id,"status":row.status,"stage":row.stage,"requires_human_review":True},None)
        return row

    def add_annotation(self,claim_id:str,appeal_id:str,reviewer_user_id:str,*,target_type:str,target_id:str,body:str,anchor:dict,tags:list[str],idempotency_key:str)->AppealReviewerAnnotationModel:
        appeal=self._appeal(claim_id,appeal_id);self._require_assigned(appeal,reviewer_user_id)
        if len(body.strip())<3:raise ValueError("annotation body is required")
        existing=self.session.scalar(select(AppealReviewerAnnotationModel).where(AppealReviewerAnnotationModel.tenant_id==self.tenant_id,AppealReviewerAnnotationModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(AppealReviewerAnnotationModel(annotation_id=f"ara_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,reviewer_user_id=reviewer_user_id,target_type=target_type,target_id=target_id,body=body,body_sha256=_sha(body),anchor=anchor,tags=list(dict.fromkeys(tags)),idempotency_key=idempotency_key,created_at=_now()))
        self._emit(claim_id,"appeal.reconsideration.annotation.added",appeal_id,{"appeal_id":appeal_id,"status":"recorded"},None);return row

    def request_missing_evidence(self,claim_id:str,appeal_id:str,reviewer_user_id:str,*,document_types:list[str],rationale:str,idempotency_key:str|None=None)->AppealMissingEvidenceRequestModel:
        appeal=self._appeal(claim_id,appeal_id,for_update=True);self._require_assigned(appeal,reviewer_user_id);idempotency_key=idempotency_key or f"missing-{uuid4().hex}"
        existing=self.session.scalar(select(AppealMissingEvidenceRequestModel).where(AppealMissingEvidenceRequestModel.tenant_id==self.tenant_id,AppealMissingEvidenceRequestModel.idempotency_key==idempotency_key))
        if existing:
            if existing.appeal_id!=appeal_id: raise ReviewConflictError("idempotency key was already used outside this appeal")
            return existing
        row=self.repo.add(AppealMissingEvidenceRequestModel(request_id=f"amer_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,requested_by_user_id=reviewer_user_id,document_types=list(dict.fromkeys(document_types)),rationale=rationale,status="open",idempotency_key=idempotency_key,created_at=_now()))
        appeal.status=AppealStatus.WAITING_SUPPLEMENTAL_EVIDENCE.value;appeal.appeal_version+=1;appeal.updated_at=_now();self._emit(claim_id,"appeal.reconsideration.missing_evidence.requested",appeal_id,{"appeal_id":appeal_id,"status":appeal.status,"requires_human_review":True},None);return row

    def escalate(self,claim_id:str,appeal_id:str,reviewer_user_id:str,*,reason:str,assigned_queue:str="appeal_second_level",idempotency_key:str|None=None)->AppealEscalationModel:
        appeal=self._appeal(claim_id,appeal_id);self._require_assigned(appeal,reviewer_user_id);idempotency_key=idempotency_key or f"escalate-{uuid4().hex}"
        existing=self.session.scalar(select(AppealEscalationModel).where(AppealEscalationModel.tenant_id==self.tenant_id,AppealEscalationModel.idempotency_key==idempotency_key))
        if existing:
            if existing.appeal_id!=appeal_id: raise ReviewConflictError("idempotency key was already used outside this appeal")
            return existing
        row=self.repo.add(AppealEscalationModel(escalation_id=f"aresc_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,level=AppealEscalationLevel.SECOND_LEVEL.value,reason=reason,created_by_user_id=reviewer_user_id,assigned_queue=assigned_queue,status="open",idempotency_key=idempotency_key,created_at=_now()))
        self._emit(claim_id,"appeal.reconsideration.escalated",appeal_id,{"appeal_id":appeal_id,"status":"open","requires_human_review":True},None);return row

    def snapshot_view(self,claim_id:str,appeal_id:str)->dict:
        appeal=self._appeal(claim_id,appeal_id);snapshot=self.repo.latest_snapshot(appeal_id);comparisons=[] if snapshot is None else self.repo.comparisons(appeal_id,snapshot.snapshot_id)
        rag_runs=self.repo.rag_runs(appeal_id);latest_rag=rag_runs[0] if rag_runs else None
        return {
            "claim_id":claim_id,"appeal_id":appeal_id,"appeal_status":appeal.status,"assigned_reviewer_user_id":appeal.assigned_reviewer_user_id,"appeal_version":appeal.appeal_version,
            "evidence_snapshot":None if snapshot is None else {"snapshot_id":snapshot.snapshot_id,"snapshot_version":snapshot.snapshot_version,"status":snapshot.status,"snapshot_sha256":snapshot.snapshot_sha256,"original_evidence_snapshot_sha256":snapshot.original_evidence_snapshot_sha256,"original_sources":snapshot.original_sources,"supplemental_sources":snapshot.supplemental_sources,"modalities":snapshot.modalities,"source_count":snapshot.source_count,"locked_at":snapshot.locked_at},
            "reingestions":[{"reingestion_id":x.reingestion_id,"source_kind":x.source_kind,"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"media_type":x.media_type,"file_validation_status":x.file_validation_status,"malware_verdict":x.malware_verdict,"extraction_status":x.extraction_status,"chunk_count":x.chunk_count,"embedding_model":x.embedding_model,"embedding_dimensions":x.embedding_dimensions,"index_version":x.index_version,"status":x.status,"error_code":x.error_code} for x in self.repo.reingestions(appeal_id)],
            "comparisons":[{"comparison_id":x.comparison_id,"comparison_type":x.comparison_type,"field":x.field,"severity":x.severity,"confidence":x.confidence,"description":x.description,"original_source_ref":x.original_source_ref,"supplemental_source_ref":x.supplemental_source_ref,"citations":x.citations} for x in comparisons],
            "latest_rag":None if latest_rag is None else {"run_id":latest_rag.run_id,"snapshot_id":latest_rag.snapshot_id,"strategy":latest_rag.strategy,"selected_count":latest_rag.selected_count,"citation_coverage":latest_rag.citation_coverage,"contradiction_count":latest_rag.contradiction_count,"changed_fact_count":latest_rag.changed_fact_count,"pack_sha256":latest_rag.pack_sha256,"items":[{"item_id":i.item_id,"source_scope":i.source_scope,"source_id":i.source_id,"source_version":i.source_version,"modality":i.modality,"rank":i.rank,"score":i.score,"content_sha256":i.content_sha256,"text_preview":i.text_preview,"citation":i.citation,"retrieval_sources":i.retrieval_sources} for i in self.repo.rag_items(latest_rag.run_id)]},
            "recommendations":[{"reconsideration_run_id":x.reconsideration_run_id,"rag_run_id":x.rag_run_id,"graph_thread_id":x.graph_thread_id,"agent_name":x.agent_name,"recommendation":x.recommendation,"confidence":x.confidence,"recommendation_summary":x.recommendation_summary,"recommendation_sha256":x.recommendation_sha256,"evidence_refs":x.evidence_refs,"changed_fact_refs":x.changed_fact_refs,"contradiction_refs":x.contradiction_refs,"missing_evidence_requests":x.missing_evidence_requests,"escalation_reasons":x.escalation_reasons,"requires_human_review":x.requires_human_review,"adjudication_authority":x.adjudication_authority,"created_at":x.created_at} for x in self.repo.recommendations(appeal_id)],
            "checkpoints":[{"checkpoint_id":x.checkpoint_id,"thread_id":x.thread_id,"checkpoint_version":x.checkpoint_version,"stage":x.stage,"status":x.status,"state_sha256":x.state_sha256,"requires_human_action":x.requires_human_action,"created_at":x.created_at,"resumed_by_user_id":x.resumed_by_user_id,"resumed_at":x.resumed_at} for x in self.repo.checkpoints(appeal_id)],
            "annotations":[{"annotation_id":x.annotation_id,"reviewer_user_id":x.reviewer_user_id,"target_type":x.target_type,"target_id":x.target_id,"body":x.body,"body_sha256":x.body_sha256,"anchor":x.anchor,"tags":x.tags,"created_at":x.created_at} for x in self.repo.annotations(appeal_id)],
            "missing_evidence_requests":[{"request_id":x.request_id,"document_types":x.document_types,"rationale":x.rationale,"status":x.status,"created_at":x.created_at} for x in self.repo.missing_requests(appeal_id)],
            "escalations":[{"escalation_id":x.escalation_id,"level":x.level,"reason":x.reason,"assigned_queue":x.assigned_queue,"status":x.status,"created_at":x.created_at} for x in self.repo.escalations(appeal_id)],
            "traceability":self.traceability(claim_id,appeal_id),
            "human_authority":{"recommendation_only":True,"llm_can_affirm_modify_or_overturn":False,"langgraph_can_affirm_modify_or_overturn":False,"rag_can_affirm_modify_or_overturn":False,"mcp_can_affirm_modify_or_overturn":False,"independent_human_required":True},
        }

    def traceability(self,claim_id:str,appeal_id:str)->dict:
        appeal=self._appeal(claim_id,appeal_id);packet=self._packet(appeal);nodes=[];edges=[]
        for x in packet.evidence_snapshot or []:
            if x.get("evidence_id"):nodes.append({"id":x["evidence_id"],"type":"original_evidence","sha256":x.get("content_sha256")});edges.append({"from":x["evidence_id"],"to":packet.packet_id,"relationship":"locked_in_original_decision"})
        nodes.extend([{"id":packet.packet_id,"type":"original_locked_human_decision_packet"},{"id":appeal.appeal_id,"type":"appeal"}]);edges.append({"from":packet.packet_id,"to":appeal.appeal_id,"relationship":"appealed_by_human_participant"})
        snapshot=self.repo.latest_snapshot(appeal_id)
        if snapshot:
            nodes.append({"id":snapshot.snapshot_id,"type":"immutable_appeal_evidence_snapshot","sha256":snapshot.snapshot_sha256});edges.append({"from":appeal.appeal_id,"to":snapshot.snapshot_id,"relationship":"binds_reconsideration_evidence"})
        for x in self.repo.reingestions(appeal_id):nodes.append({"id":x.reingestion_id,"type":"validated_reingested_source","source_id":x.source_id,"status":x.status});edges.append({"from":x.source_id,"to":x.reingestion_id,"relationship":"validated_reingested_and_version_bound"})
        for x in self.repo.recommendations(appeal_id):nodes.append({"id":x.reconsideration_run_id,"type":"recommendation_only_agent","authority":"none"});edges.append({"from":x.rag_run_id,"to":x.reconsideration_run_id,"relationship":"supports_nonbinding_recommendation"})
        resolution=self.post.resolution(appeal_id)
        if resolution:nodes.append({"id":resolution.resolution_id,"type":"independent_human_appeal_resolution"});edges.append({"from":appeal_id,"to":resolution.resolution_id,"relationship":"resolved_only_by_authorized_independent_human"})
        return {"claim_id":claim_id,"appeal_id":appeal_id,"nodes":nodes,"edges":edges,"complete_lineage":True,"original_decision_immutable":True,"recommendation_agent_adjudication_authority":False,"final_resolution_human_only":True}

from __future__ import annotations
import hashlib,json,re
from datetime import UTC,date,datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.provider_dispute_intelligence import MISSING_EVIDENCE_TYPES,RECOMMENDATIONS
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.claims import ClaimModel,EvidenceArtifactModel
from app.models.document_intelligence import DocumentExtractionRunModel,ExtractionUnitModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.models.ingestion import EvidenceUploadSessionModel,MalwareScanModel
from app.models.provider_dispute_intelligence import *
from app.models.recovery_operations import ProviderDisputeModel,RecoveryCaseModel
from app.repositories.provider_dispute_intelligence import ProviderDisputeIntelligenceRepository
from app.repositories.recovery_operations import RecoveryOperationsRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.recovery_operations import RecoveryOperationsService
from app.services.review_workbench import ReviewConflictError

_TOKEN=re.compile(r"[a-z0-9]{2,}",re.I)
MATERIAL_FIELDS={"amount","total","total_amount","service_date","date","provider","provider_id","code","service_code","units","status"}

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _tokens(v):return set(_TOKEN.findall((v or "").lower()))
def _score(q,text):
    a,b=_tokens(q),_tokens(text)
    return 0.0 if not a or not b else len(a&b)/max(1,len(a))
def _flat(value,prefix=""):
    out={}
    if isinstance(value,dict):
        for k,v in value.items():
            key=f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v,(dict,list)):out.update(_flat(v,key))
            elif v is not None:out[key]=str(v)
    elif isinstance(value,list):
        for i,v in enumerate(value):out.update(_flat(v,f"{prefix}[{i}]") if isinstance(v,(dict,list)) else {f"{prefix}[{i}]":str(v)})
    return out

class ProviderDisputeIntelligenceService:
    """Evidence/RAG/agent decision support for provider recovery disputes.

    Deliberately does not import or call RecoveryOperationsService.resolve_dispute,
    accounting posting, payment authorization, collection, or fund movement APIs.
    """
    REVIEW_ROLES={"finance_operator","finance_analyst","finance_approver","auditor","tenant_admin"}
    MUTATE_ROLES={"finance_operator","finance_analyst"}
    def __init__(self,session:Session,tenant_id:str,*,embedding_model="text-embedding-3-large",embedding_dimensions=1536,index_version="provider-dispute-rag-v1"):
        self.session=session;self.tenant_id=tenant_id;self.repo=ProviderDisputeIntelligenceRepository(session,tenant_id);self.recovery=RecoveryOperationsRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.embedding_model=embedding_model;self.embedding_dimensions=embedding_dimensions;self.index_version=index_version
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active human tenant membership required")
        return m
    def _require_reader(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.REVIEW_ROLES:raise ReviewConflictError("authorized human finance reviewer required")
        return m
    def _require_mutator(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.MUTATE_ROLES:raise ReviewConflictError("human finance operator/analyst required")
        return m
    def _dispute(self,case_id,dispute_id):
        c=self.recovery.case(case_id)
        if c is None:raise LookupError("recovery case not found")
        d=self.session.scalar(select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id,ProviderDisputeModel.recovery_case_id==case_id,ProviderDisputeModel.dispute_id==dispute_id))
        if d is None:raise LookupError("provider dispute not found")
        return c,d
    def _provider_membership(self,user_id,d):
        m=self._membership(user_id)
        if m.role!="provider" or not d.provider_organization_id or m.provider_organization_id!=d.provider_organization_id:raise ReviewConflictError("provider membership is not related to this dispute")
        return m
    def _emit(self,c,d,event_type,payload,trace_id=None):
        safe={k:v for k,v in payload.items() if k in {"dispute_id","status","stage","snapshot_id","run_id","modality","progress","requires_human_review","request_id"}}
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"pdi_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=c.claim_id,aggregate_type="provider_dispute_intelligence",aggregate_id=d.dispute_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-provider-dispute-intelligence",payload=payload,metadata=safe),topic=EventTopic.CLAIMS.value)
    @staticmethod
    def _modality(media_type,document_type=""):
        m=(media_type or "").lower();d=(document_type or "").lower()
        if "fhir" in m or "fhir" in d:return "fhir"
        if m.startswith("image/"):return "image"
        if m.startswith("audio/"):return "audio"
        if m.startswith("video/"):return "video"
        if "csv" in m or "spreadsheet" in m or "invoice" in d or "bill" in d:return "table"
        return "document"
    def _malware_verdict(self,evidence):
        upload=self.session.scalar(select(EvidenceUploadSessionModel).where(EvidenceUploadSessionModel.tenant_id==self.tenant_id,EvidenceUploadSessionModel.evidence_id==evidence.evidence_id).order_by(EvidenceUploadSessionModel.created_at.desc()).limit(1))
        if upload is None:return "accepted_boundary_inherited"
        scan=self.session.scalar(select(MalwareScanModel).where(MalwareScanModel.tenant_id==self.tenant_id,MalwareScanModel.upload_session_id==upload.upload_session_id).order_by(MalwareScanModel.attempt_number.desc()).limit(1))
        return "missing_scan" if scan is None else str(scan.verdict)
    def _evidence_units(self,evidence_id):
        return list(self.session.execute(select(ExtractionUnitModel,DocumentExtractionRunModel).join(DocumentExtractionRunModel,DocumentExtractionRunModel.run_id==ExtractionUnitModel.run_id).where(ExtractionUnitModel.tenant_id==self.tenant_id,ExtractionUnitModel.source_evidence_id==evidence_id,DocumentExtractionRunModel.tenant_id==self.tenant_id,DocumentExtractionRunModel.status=="succeeded").order_by(DocumentExtractionRunModel.completed_at.desc(),ExtractionUnitModel.sequence)).all())
    def register_evidence(self,case_id,dispute_id,evidence_id,user_id,*,trace_id=None):
        c,d=self._dispute(case_id,dispute_id);m=self._membership(user_id)
        if m.role=="provider":
            self._provider_membership(user_id,d)
        elif m.role not in self.MUTATE_ROLES:raise ReviewConflictError("provider or human finance operator/analyst required")
        ev=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,EvidenceArtifactModel.claim_id==c.claim_id))
        if ev is None:raise LookupError("provider dispute evidence not found")
        if m.role=="provider" and ev.uploaded_by_user_id not in {None,user_id}:raise ReviewConflictError("provider may register only evidence submitted through its authorized evidence path")
        existing=self.repo.reingestion(dispute_id,"evidence",ev.evidence_id,str(ev.evidence_version))
        if existing:return existing
        row=self.repo.add(DisputeEvidenceReingestionModel(reingestion_id=f"pdri_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,claim_id=c.claim_id,source_kind="evidence",source_id=ev.evidence_id,source_version=str(ev.evidence_version),modality=self._modality(ev.media_type,ev.document_type),media_type=ev.media_type,content_sha256=ev.content_sha256,file_validation_status="pending",malware_verdict="pending",extraction_status="pending",chunk_count=0,chunk_manifest=[],embedding_model=self.embedding_model,embedding_dimensions=self.embedding_dimensions,embedding_input_sha256s=[],index_version=self.index_version,retrieval_namespace=f"provider-dispute:{dispute_id}",status="pending",error_code=None,error_detail=None,trace_id=trace_id,started_at=_now(),completed_at=None))
        self._emit(c,d,"provider_dispute_intelligence.reingestion.queued",{"dispute_id":dispute_id,"status":"pending","modality":row.modality,"progress":0},trace_id);return row
    def process_evidence(self,case_id,dispute_id,evidence_id,user_id,*,trace_id=None):
        c,d=self._dispute(case_id,dispute_id)
        if user_id is None:
            ev0=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,EvidenceArtifactModel.claim_id==c.claim_id))
            if ev0 is None:raise LookupError("provider dispute evidence not found")
            row=self.repo.reingestion(dispute_id,"evidence",evidence_id,str(ev0.evidence_version))
            if row is None:raise ReviewConflictError("background processing requires prior authorized evidence registration")
        else:
            self._membership(user_id);row=self.register_evidence(case_id,dispute_id,evidence_id,user_id,trace_id=trace_id)
        if row.status=="ready":return row
        ev=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.evidence_id==evidence_id,EvidenceArtifactModel.claim_id==c.claim_id))
        if ev is None:raise LookupError("provider dispute evidence not found")
        row.status="validating"
        if ev.status!="ready" or len(ev.content_sha256)!=64 or ev.byte_size<=0:
            row.status="blocked";row.file_validation_status="blocked";row.malware_verdict="not_evaluated";row.error_code="evidence_not_ready";row.error_detail="provider evidence must pass quarantine/file validation";row.completed_at=_now();self.session.flush();return row
        verdict=self._malware_verdict(ev);row.malware_verdict=verdict
        if verdict.lower() in {"infected","malicious","suspicious","error","missing_scan"}:
            row.status="blocked";row.file_validation_status="blocked";row.error_code="malware_validation_failed";row.error_detail="provider evidence did not satisfy malware validation";row.completed_at=_now();self.session.flush();return row
        row.file_validation_status="passed";row.status="extracting";chunks=[];seen=set()
        for unit,run in self._evidence_units(evidence_id):
            text=(unit.text_content or "").strip();structured=dict(unit.structured_data or {})
            if not text and structured:text=_canon(structured)
            if not text:continue
            key=(unit.unit_id,run.pipeline_version)
            if key in seen:continue
            seen.add(key);citation={"evidence_id":ev.evidence_id,"evidence_version":ev.evidence_version,"extraction_unit_id":unit.unit_id,"page_number":unit.page_number,"bbox":unit.bbox,"start_ms":unit.start_ms,"end_ms":unit.end_ms,"source_locator":unit.source_locator}
            chunks.append({"chunk_id":f"provider-dispute:{dispute_id}:{unit.unit_id}","source_version":str(ev.evidence_version),"pipeline_version":run.pipeline_version,"text":text[:12000],"content_sha256":unit.content_sha256,"structured_data":structured,"citation":citation})
        if not chunks:
            text=_canon({"document_type":ev.document_type,"media_type":ev.media_type,"source_system":ev.source_system,"source_locator":ev.source_locator,"media_metadata":ev.media_metadata});chunks=[{"chunk_id":f"provider-dispute:{dispute_id}:metadata:{ev.evidence_id}:v{ev.evidence_version}","source_version":str(ev.evidence_version),"pipeline_version":"metadata-fallback-v1","text":text,"content_sha256":_sha(text),"structured_data":dict(ev.media_metadata or {}),"citation":{"evidence_id":ev.evidence_id,"evidence_version":ev.evidence_version,"source_locator":ev.source_locator}}];row.extraction_status="metadata_only"
        else:row.extraction_status="succeeded"
        row.chunk_manifest=[{k:v for k,v in x.items() if k!="text"}|{"text_preview":x["text"][:1000]} for x in chunks];row.chunk_count=len(chunks);row.embedding_input_sha256s=[_sha(f"{self.embedding_model}|{self.embedding_dimensions}|{x['text'].strip()}") for x in chunks];row.status="ready";row.completed_at=_now();self.session.flush();self._emit(c,d,"provider_dispute_intelligence.reingestion.completed",{"dispute_id":dispute_id,"status":"ready","modality":row.modality,"progress":100},trace_id);return row
    def register_fhir(self,case_id,dispute_id,snapshot_id,user_id,*,trace_id=None):
        c,d=self._dispute(case_id,dispute_id);self._require_mutator(user_id);f=self.session.scalar(select(FHIRResourceSnapshotModel).where(FHIRResourceSnapshotModel.tenant_id==self.tenant_id,FHIRResourceSnapshotModel.snapshot_id==snapshot_id,FHIRResourceSnapshotModel.claim_id==c.claim_id))
        if f is None:raise LookupError("FHIR snapshot not found")
        existing=self.repo.reingestion(dispute_id,"fhir",f.snapshot_id,f.version_id)
        if existing:return existing
        text=_canon(f.canonical_resource or f.raw_resource or {});citation={"fhir_snapshot_id":f.snapshot_id,"fhir_resource_type":f.resource_type,"fhir_logical_id":f.logical_id,"fhir_version_id":f.version_id}
        row=self.repo.add(DisputeEvidenceReingestionModel(reingestion_id=f"pdri_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,claim_id=c.claim_id,source_kind="fhir",source_id=f.snapshot_id,source_version=f.version_id,modality="fhir",media_type="application/fhir+json",content_sha256=f.content_sha256,file_validation_status="trusted_fhir_gateway",malware_verdict="not_applicable",extraction_status="canonical_fhir",chunk_count=1,chunk_manifest=[{"chunk_id":f"provider-dispute:{dispute_id}:fhir:{f.snapshot_id}","source_version":f.version_id,"pipeline_version":"fhir-canonical-v1","content_sha256":_sha(text),"structured_data":f.canonical_resource or {},"citation":citation,"text_preview":text[:1000]}],embedding_model=self.embedding_model,embedding_dimensions=self.embedding_dimensions,embedding_input_sha256s=[_sha(f"{self.embedding_model}|{self.embedding_dimensions}|{text}")],index_version=self.index_version,retrieval_namespace=f"provider-dispute:{dispute_id}",status="ready",error_code=None,error_detail=None,trace_id=trace_id,started_at=_now(),completed_at=_now()));self._emit(c,d,"provider_dispute_intelligence.fhir.ready",{"dispute_id":dispute_id,"status":"ready","modality":"fhir","progress":100},trace_id);return row
    def add_provider_agreement(self,user_id,*,provider_organization_id,agreement_key,version,title,effective_from,effective_to,content_text,metadata=None):
        self._require_mutator(user_id);existing=self.session.scalar(select(ProviderAgreementVersionModel).where(ProviderAgreementVersionModel.tenant_id==self.tenant_id,ProviderAgreementVersionModel.provider_organization_id==provider_organization_id,ProviderAgreementVersionModel.agreement_key==agreement_key,ProviderAgreementVersionModel.version==version))
        if existing:return existing
        return self.repo.add(ProviderAgreementVersionModel(agreement_version_id=f"pagr_{uuid4().hex}",tenant_id=self.tenant_id,provider_organization_id=provider_organization_id,agreement_key=agreement_key,version=version,title=title,effective_from=effective_from,effective_to=effective_to,status="approved",content_text=content_text,metadata_json=metadata or {},content_sha256=_sha(content_text),created_at=_now()))
    def add_reimbursement_policy(self,user_id,*,policy_key,version,title,effective_from,effective_to,content_text,metadata=None):
        self._require_mutator(user_id);existing=self.session.scalar(select(ReimbursementPolicyVersionModel).where(ReimbursementPolicyVersionModel.tenant_id==self.tenant_id,ReimbursementPolicyVersionModel.policy_key==policy_key,ReimbursementPolicyVersionModel.version==version))
        if existing:return existing
        return self.repo.add(ReimbursementPolicyVersionModel(policy_version_id=f"rpol_{uuid4().hex}",tenant_id=self.tenant_id,policy_key=policy_key,version=version,title=title,effective_from=effective_from,effective_to=effective_to,status="approved",content_text=content_text,metadata_json=metadata or {},content_sha256=_sha(content_text),created_at=_now()))
    def _effective_knowledge(self,c):
        claim=self.session.get(ClaimModel,c.claim_id);svc_date=claim.service_from if claim else date.today();agreements=[a for a in self.repo.agreements(c.provider_organization_id) if a.effective_from<=svc_date and (a.effective_to is None or a.effective_to>=svc_date)];policies=[p for p in self.repo.policies() if p.effective_from<=svc_date and (p.effective_to is None or p.effective_to>=svc_date)];return agreements,policies
    def build_snapshot(self,case_id,dispute_id,user_id,*,trace_id=None):
        c,d=self._dispute(case_id,dispute_id);self._require_mutator(user_id);ready=[x for x in self.repo.reingestions(dispute_id) if x.status=="ready"]
        if not ready:raise ReviewConflictError("at least one validated provider dispute evidence source is required")
        pack=self.recovery.pack(case_id)
        if pack is None:raise ReviewConflictError("immutable recovery evidence pack required")
        agreements,policies=self._effective_knowledge(c);provider_sources=[{"source_kind":x.source_kind,"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"content_sha256":x.content_sha256} for x in ready];policy_sources=[{"source_kind":"provider_agreement","source_id":x.agreement_version_id,"source_version":x.version,"title":x.title,"content_sha256":x.content_sha256,"effective_from":str(x.effective_from),"effective_to":None if x.effective_to is None else str(x.effective_to)} for x in agreements]+[{"source_kind":"reimbursement_policy","source_id":x.policy_version_id,"source_version":x.version,"title":x.title,"content_sha256":x.content_sha256,"effective_from":str(x.effective_from),"effective_to":None if x.effective_to is None else str(x.effective_to)} for x in policies]
        if not policy_sources:raise ReviewConflictError("effective provider agreement or reimbursement policy evidence is required")
        version=self.repo.next_snapshot_version(dispute_id);payload={"dispute_id":dispute_id,"recovery_pack_sha256":pack.payload_sha256,"provider_sources":provider_sources,"policy_sources":policy_sources,"modalities":sorted({x.modality for x in ready}),"version":version};row=self.repo.add(DisputeEvidenceSnapshotModel(snapshot_id=f"pdsnap_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,claim_id=c.claim_id,recovery_evidence_pack_sha256=pack.payload_sha256,provider_sources=provider_sources,policy_sources=policy_sources,modalities=payload["modalities"],source_count=len(provider_sources)+len(policy_sources),snapshot_version=version,snapshot_sha256=_sha(payload),status="locked",created_by_actor_type="human_finance",created_by_actor_id=user_id,trace_id=trace_id,created_at=_now(),locked_at=_now()));self._compare(c,d,row,ready,pack,agreements,policies);self._emit(c,d,"provider_dispute_intelligence.snapshot.locked",{"dispute_id":dispute_id,"snapshot_id":row.snapshot_id,"status":"locked","progress":100},trace_id);return row
    def _compare(self,c,d,snapshot,ready,pack,agreements,policies):
        existing={x.provider_source_ref for x in self.repo.comparisons(d.dispute_id)};recovery_amount=str(c.target_recovery_amount)
        for r in ready:
            for ch in r.chunk_manifest:
                source=f"{r.source_kind}:{r.source_id}:v{r.source_version}:{ch.get('chunk_id')}";structured=_flat(ch.get("structured_data") or {});preview=str(ch.get("text_preview") or "")
                for k,v in structured.items():
                    leaf=k.split(".")[-1].lower().replace("[","")
                    if any(x in leaf for x in MATERIAL_FIELDS):
                        typ="changed";severity="material" if any(x in leaf for x in {"amount","total","units","code","service_date"}) else "moderate"
                        if "amount" in leaf or "total" in leaf:
                            try:
                                typ="unchanged" if Decimal(v)==Decimal(recovery_amount) else "contradictory"
                            except Exception:pass
                        key=f"{source}:{k}"
                        if key not in existing:self.repo.add(DisputeEvidenceComparisonModel(comparison_id=f"pdcmp_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,dispute_id=d.dispute_id,snapshot_id=snapshot.snapshot_id,comparison_type=typ,field=k,recovery_source_ref=f"recovery_case:{c.recovery_case_id}",provider_source_ref=source,recovery_value_sha256=_sha(recovery_amount),provider_value_sha256=_sha(v),severity=severity,confidence=.88,description=f"Provider dispute evidence value for {k} is compared with the governed recovery position.",citations=[ch.get("citation") or {},{"recovery_evidence_pack_sha256":pack.payload_sha256}],created_at=_now()))
                policy_text=" ".join([x.content_text for x in agreements+policies]).lower();prov=preview.lower()
                contradiction=("not subject to recoupment" in prov or "recovery not owed" in prov or "no overpayment" in prov) and any(t in policy_text for t in ["recoup","overpayment","recovery"])
                if contradiction:
                    key=f"policy:{source}"
                    if key not in existing:self.repo.add(DisputeEvidenceComparisonModel(comparison_id=f"pdcmp_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,dispute_id=d.dispute_id,snapshot_id=snapshot.snapshot_id,comparison_type="contradictory",field="payment_policy",recovery_source_ref=pack.evidence_pack_id,provider_source_ref=source,recovery_value_sha256=_sha(policy_text),provider_value_sha256=_sha(preview),severity="material",confidence=.9,description="Provider assertion conflicts with effective agreement/policy recovery language and requires independent human interpretation.",citations=[ch.get("citation") or {}]+[{"source_id":x.agreement_version_id if hasattr(x,"agreement_version_id") else x.policy_version_id,"source_version":x.version,"content_sha256":x.content_sha256} for x in agreements+policies],created_at=_now()))
    def search(self,case_id,dispute_id,user_id,query,*,limit=12,trace_id=None):
        c,d=self._dispute(case_id,dispute_id);self._require_reader(user_id);snap=self.repo.latest_snapshot(dispute_id)
        if snap is None or snap.status!="locked":raise ReviewConflictError("locked dispute evidence snapshot required")
        candidates=[]
        for r in self.repo.reingestions(dispute_id):
            if r.status!="ready":continue
            for ch in r.chunk_manifest:
                text=str(ch.get("text_preview") or "");candidates.append((max(.01,_score(query,text)),"provider_evidence",r.source_id,r.source_version,r.modality,r.content_sha256,text,ch.get("citation") or {},["lexical","dispute_snapshot"]))
        agreements,policies=self._effective_knowledge(c)
        for x in agreements:
            candidates.append((max(.01,_score(query,x.content_text)),"provider_agreement",x.agreement_version_id,x.version,"policy",x.content_sha256,x.content_text[:1600],{"agreement_key":x.agreement_key,"version":x.version,"effective_from":str(x.effective_from)},["lexical","effective_date","provider_filter"]))
        for x in policies:
            candidates.append((max(.01,_score(query,x.content_text)),"reimbursement_policy",x.policy_version_id,x.version,"policy",x.content_sha256,x.content_text[:1600],{"policy_key":x.policy_key,"version":x.version,"effective_from":str(x.effective_from)},["lexical","effective_date"]))
        candidates=sorted(candidates,key=lambda x:(-x[0],x[2]))[:max(1,min(limit,30))];comparisons=self.repo.comparisons(dispute_id);run_id=f"pdrag_{uuid4().hex}";pack_payload=[]
        for rank,x in enumerate(candidates,1):
            score,scope,sid,sv,mod,sha,text,citation,sources=x;item=self.repo.add(DisputeRAGItemModel(item_id=f"pdri_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,run_id=run_id,source_scope=scope,source_id=sid,source_version=sv,modality=mod,rank=rank,score=round(float(score),6),content_sha256=sha,text_preview=text,citation=citation,retrieval_sources=sources,created_at=_now()));pack_payload.append({"source":sid,"version":sv,"rank":rank,"score":item.score,"sha256":sha,"citation":citation})
        run=self.repo.add(DisputeRAGRunModel(run_id=run_id,tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,snapshot_id=snap.snapshot_id,query_sha256=_sha(query),strategy="provider_dispute_hybrid_lexical_policy_reranked",candidate_count=len(candidates),selected_count=len(candidates),citation_coverage=1.0 if candidates else 0.0,contradiction_count=sum(x.comparison_type=="contradictory" for x in comparisons),changed_fact_count=sum(x.comparison_type in {"changed","contradictory","added"} for x in comparisons),pack_sha256=_sha(pack_payload),trace_id=trace_id,created_at=_now()));self._emit(c,d,"provider_dispute_intelligence.rag.completed",{"dispute_id":dispute_id,"run_id":run_id,"status":"completed","progress":100},trace_id);return {"run":run,"items":self.repo.rag_items(run_id)}
    def run_recommendation(self,case_id,dispute_id,user_id,*,query="Assess the provider dispute against the governed recovery evidence, effective provider agreement and reimbursement policy.",idempotency_key,trace_id=None):
        c,d=self._dispute(case_id,dispute_id);self._require_mutator(user_id);existing=self.session.scalar(select(DisputeRecommendationRunModel).where(DisputeRecommendationRunModel.tenant_id==self.tenant_id,DisputeRecommendationRunModel.idempotency_key==idempotency_key))
        if existing:return existing
        rag=self.search(case_id,dispute_id,user_id,query,limit=12,trace_id=trace_id);snap=self.repo.latest_snapshot(dispute_id);comps=self.repo.comparisons(dispute_id);material=[x for x in comps if x.comparison_type=="contradictory" and x.severity=="material"];changed=[x for x in comps if x.comparison_type in {"changed","contradictory","added"}];policy_refs=[{"source_id":x.source_id,"source_version":x.source_version,"citation":x.citation} for x in rag["items"] if x.source_scope in {"provider_agreement","reimbursement_policy"}];evidence_refs=[{"source_id":x.source_id,"source_version":x.source_version,"citation":x.citation} for x in rag["items"] if x.source_scope=="provider_evidence"]
        open_missing=[x for x in self.repo.missing_requests(dispute_id) if x.status=="open"]
        if open_missing:recommendation="request_information";confidence=.92
        elif material:recommendation="escalate";confidence=.86
        elif changed:recommendation="consider_reduce_recovery";confidence=.74
        else:recommendation="uphold_recovery";confidence=.72
        thread=f"provider-dispute:{dispute_id}";summary=f"Recommendation-only analysis found {len(changed)} changed facts and {len(material)} material contradictions across provider evidence and effective policy/contract sources. Independent human dispute resolution remains required.";payload={"recommendation":recommendation,"snapshot":snap.snapshot_sha256,"rag":rag["run"].pack_sha256,"evidence_refs":evidence_refs,"policy_refs":policy_refs,"comparison_refs":[x.comparison_id for x in material]}
        row=self.repo.add(DisputeRecommendationRunModel(recommendation_run_id=f"pdrec_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,snapshot_id=snap.snapshot_id,rag_run_id=rag["run"].run_id,graph_thread_id=thread,agent_name="provider_dispute_recommendation_agent",prompt_version="release45-v1",recommendation=recommendation,confidence=confidence,summary=summary,recommendation_sha256=_sha(payload),evidence_refs=evidence_refs,policy_refs=policy_refs,contradiction_refs=[x.comparison_id for x in material],changed_fact_refs=[x.comparison_id for x in changed],missing_evidence=[x.request_id for x in open_missing],requires_human_review=True,adjudication_authority="none",idempotency_key=idempotency_key,trace_id=trace_id,created_at=_now()));state={"dispute_id":dispute_id,"recommendation_run_id":row.recommendation_run_id,"snapshot_id":snap.snapshot_id,"rag_run_id":rag["run"].run_id,"requires_human_resolution":True,"adjudication_authority":"none"};cp=self.repo.add(DisputeReviewCheckpointModel(checkpoint_id=f"pdcp_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,thread_id=thread,checkpoint_version=self.repo.next_checkpoint_version(thread),stage="independent_human_dispute_review",status="waiting_human",state_metadata=state,state_sha256=_sha(state),requires_human_action=True,created_at=_now(),resumed_by_user_id=None,resumed_at=None));self._emit(c,d,"provider_dispute_intelligence.agent.completed",{"dispute_id":dispute_id,"run_id":row.recommendation_run_id,"status":"waiting_human","requires_human_review":True,"progress":100},trace_id);return row
    def request_missing_evidence(self,case_id,dispute_id,user_id,*,document_types,rationale,idempotency_key):
        c,d=self._dispute(case_id,dispute_id);self._require_mutator(user_id)
        bad=set(document_types)-set(MISSING_EVIDENCE_TYPES)
        if bad:raise ValueError(f"unsupported dispute evidence types: {sorted(bad)}")
        existing=self.session.scalar(select(DisputeMissingEvidenceRequestModel).where(DisputeMissingEvidenceRequestModel.tenant_id==self.tenant_id,DisputeMissingEvidenceRequestModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(DisputeMissingEvidenceRequestModel(request_id=f"pdmr_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,requested_by_user_id=user_id,document_types=document_types,rationale=rationale,status="open",idempotency_key=idempotency_key,created_at=_now(),satisfied_at=None));self._emit(c,d,"provider_dispute_intelligence.missing_evidence.requested",{"dispute_id":dispute_id,"request_id":row.request_id,"status":"open"});return row
    def provider_response(self,case_id,dispute_id,user_id,*,request_id,statement,evidence_refs,idempotency_key):
        c,d=self._dispute(case_id,dispute_id);self._provider_membership(user_id,d);existing=self.session.scalar(select(ProviderDisputeResponseModel).where(ProviderDisputeResponseModel.tenant_id==self.tenant_id,ProviderDisputeResponseModel.idempotency_key==idempotency_key))
        if existing:return existing
        req=None
        if request_id:
            req=self.session.scalar(select(DisputeMissingEvidenceRequestModel).where(DisputeMissingEvidenceRequestModel.tenant_id==self.tenant_id,DisputeMissingEvidenceRequestModel.request_id==request_id,DisputeMissingEvidenceRequestModel.dispute_id==dispute_id))
            if req is None:raise LookupError("missing-evidence request not found")
        row=self.repo.add(ProviderDisputeResponseModel(response_id=f"pdresp_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,request_id=request_id,provider_user_id=user_id,statement=statement,evidence_refs=evidence_refs,body_sha256=_sha({"statement":statement,"evidence_refs":evidence_refs}),idempotency_key=idempotency_key,created_at=_now()))
        if req is not None:req.status="satisfied";req.satisfied_at=_now()
        self._emit(c,d,"provider_dispute_intelligence.provider_response.received",{"dispute_id":dispute_id,"request_id":request_id or "","status":"received"});return row
    def resume_checkpoint(self,case_id,dispute_id,checkpoint_id,user_id):
        c,d=self._dispute(case_id,dispute_id);self._require_reader(user_id);cp=self.session.scalar(select(DisputeReviewCheckpointModel).where(DisputeReviewCheckpointModel.tenant_id==self.tenant_id,DisputeReviewCheckpointModel.checkpoint_id==checkpoint_id,DisputeReviewCheckpointModel.dispute_id==dispute_id))
        if cp is None:raise LookupError("dispute review checkpoint not found")
        if cp.status=="completed":return cp
        cp.status="completed";cp.requires_human_action=False;cp.resumed_by_user_id=user_id;cp.resumed_at=_now();self._emit(c,d,"provider_dispute_intelligence.checkpoint.resumed",{"dispute_id":dispute_id,"status":"completed","stage":cp.stage});return cp
    def workbench(self,case_id,dispute_id,user_id):
        c,d=self._dispute(case_id,dispute_id);self._require_reader(user_id);snap=self.repo.latest_snapshot(dispute_id);runs=self.repo.rag_runs(dispute_id);latest=runs[-1] if runs else None;recs=self.repo.recommendation_runs(dispute_id)
        return {"recovery_case_id":case_id,"dispute":RecoveryOperationsService._view_dispute(d),"snapshot":None if snap is None else {"snapshot_id":snap.snapshot_id,"snapshot_version":snap.snapshot_version,"snapshot_sha256":snap.snapshot_sha256,"recovery_evidence_pack_sha256":snap.recovery_evidence_pack_sha256,"provider_sources":snap.provider_sources,"policy_sources":snap.policy_sources,"modalities":snap.modalities,"source_count":snap.source_count,"status":snap.status,"locked_at":snap.locked_at},"reingestions":[{"reingestion_id":x.reingestion_id,"source_kind":x.source_kind,"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"media_type":x.media_type,"content_sha256":x.content_sha256,"file_validation_status":x.file_validation_status,"malware_verdict":x.malware_verdict,"extraction_status":x.extraction_status,"chunk_count":x.chunk_count,"status":x.status,"error_code":x.error_code} for x in self.repo.reingestions(dispute_id)],"comparisons":[{"comparison_id":x.comparison_id,"comparison_type":x.comparison_type,"field":x.field,"severity":x.severity,"confidence":x.confidence,"description":x.description,"recovery_source_ref":x.recovery_source_ref,"provider_source_ref":x.provider_source_ref,"citations":x.citations} for x in self.repo.comparisons(dispute_id)],"latest_rag":None if latest is None else {"run_id":latest.run_id,"snapshot_id":latest.snapshot_id,"strategy":latest.strategy,"selected_count":latest.selected_count,"citation_coverage":latest.citation_coverage,"contradiction_count":latest.contradiction_count,"changed_fact_count":latest.changed_fact_count,"pack_sha256":latest.pack_sha256,"items":[{"item_id":x.item_id,"source_scope":x.source_scope,"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"rank":x.rank,"score":x.score,"content_sha256":x.content_sha256,"text_preview":x.text_preview,"citation":x.citation} for x in self.repo.rag_items(latest.run_id)]},"recommendations":[{"recommendation_run_id":x.recommendation_run_id,"recommendation":x.recommendation,"confidence":x.confidence,"summary":x.summary,"recommendation_sha256":x.recommendation_sha256,"evidence_refs":x.evidence_refs,"policy_refs":x.policy_refs,"contradiction_refs":x.contradiction_refs,"changed_fact_refs":x.changed_fact_refs,"missing_evidence":x.missing_evidence,"requires_human_review":x.requires_human_review,"adjudication_authority":x.adjudication_authority,"created_at":x.created_at} for x in recs],"checkpoints":[{"checkpoint_id":x.checkpoint_id,"thread_id":x.thread_id,"checkpoint_version":x.checkpoint_version,"stage":x.stage,"status":x.status,"state_sha256":x.state_sha256,"requires_human_action":x.requires_human_action,"resumed_by_user_id":x.resumed_by_user_id,"resumed_at":x.resumed_at} for x in self.repo.checkpoints(dispute_id)],"missing_evidence_requests":[{"request_id":x.request_id,"document_types":x.document_types,"rationale":x.rationale,"status":x.status,"requested_by_user_id":x.requested_by_user_id,"created_at":x.created_at,"satisfied_at":x.satisfied_at} for x in self.repo.missing_requests(dispute_id)],"provider_responses":[{"response_id":x.response_id,"request_id":x.request_id,"provider_user_id":x.provider_user_id,"statement":x.statement,"evidence_refs":x.evidence_refs,"body_sha256":x.body_sha256,"created_at":x.created_at} for x in self.repo.responses(dispute_id)],"human_authority":{"recommendation_only":True,"llm_can_resolve_dispute":False,"langgraph_can_resolve_dispute":False,"rag_can_resolve_dispute":False,"mcp_can_resolve_dispute":False,"automation_can_change_accounting_or_payment":False,"independent_human_finance_approver_required":True}}


    def reviewer_queue(self,user_id):
        self._require_reader(user_id)
        disputes=list(self.session.scalars(select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id).order_by(ProviderDisputeModel.submitted_at.desc())))
        return [{"recovery_case_id":d.recovery_case_id,"dispute_id":d.dispute_id,"external_reference":d.external_reference,"provider_organization_id":d.provider_organization_id,"disputed_amount":str(d.disputed_amount),"currency":d.currency,"reason_code":d.reason_code,"status":d.status,"material":d.material,"submitted_at":d.submitted_at,"evidence_sources":len(self.repo.reingestions(d.dispute_id)),"recommendation_runs":len(self.repo.recommendation_runs(d.dispute_id)),"open_missing_evidence":sum(x.status=="open" for x in self.repo.missing_requests(d.dispute_id))} for d in disputes]

    def provider_queue(self,user_id):
        m=self._membership(user_id)
        if m.role!="provider" or not m.provider_organization_id:raise ReviewConflictError("active provider membership required")
        disputes=list(self.session.scalars(select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id,ProviderDisputeModel.provider_organization_id==m.provider_organization_id).order_by(ProviderDisputeModel.submitted_at.desc())))
        return [{"recovery_case_id":d.recovery_case_id,"dispute_id":d.dispute_id,"external_reference":d.external_reference,"disputed_amount":str(d.disputed_amount),"currency":d.currency,"reason_code":d.reason_code,"status":d.status,"submitted_at":d.submitted_at,"missing_evidence_requests":[{"request_id":x.request_id,"document_types":x.document_types,"rationale":x.rationale,"status":x.status} for x in self.repo.missing_requests(d.dispute_id)]} for d in disputes]
    def provider_workbench(self,case_id,dispute_id,user_id):
        c,d=self._dispute(case_id,dispute_id);self._provider_membership(user_id,d)
        return {"recovery_case_id":case_id,"dispute_id":dispute_id,"external_reference":d.external_reference,"status":d.status,"disputed_amount":str(d.disputed_amount),"currency":d.currency,"reason_code":d.reason_code,"missing_evidence_requests":[{"request_id":x.request_id,"document_types":x.document_types,"rationale":x.rationale,"status":x.status,"created_at":x.created_at,"satisfied_at":x.satisfied_at} for x in self.repo.missing_requests(dispute_id)],"responses":[{"response_id":x.response_id,"request_id":x.request_id,"statement":x.statement,"evidence_refs":x.evidence_refs,"body_sha256":x.body_sha256,"created_at":x.created_at} for x in self.repo.responses(dispute_id)],"evidence_processing":[{"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"status":x.status,"file_validation_status":x.file_validation_status,"malware_verdict":x.malware_verdict} for x in self.repo.reingestions(dispute_id)],"notice":"Provider evidence is analysis input only. Final dispute resolution is performed by an independent authorized human finance approver."}

    def traceability(self,case_id,dispute_id,user_id):
        wb=self.workbench(case_id,dispute_id,user_id);up=RecoveryOperationsService(self.session,self.tenant_id).traceability(case_id,user_id);nodes=[{"id":dispute_id,"type":"provider_dispute"}];edges=[]
        if wb["snapshot"]:nodes.append({"id":wb["snapshot"]["snapshot_id"],"type":"dispute_evidence_snapshot"});edges.append({"from":dispute_id,"to":wb["snapshot"]["snapshot_id"],"relation":"locks_evidence"})
        if wb["latest_rag"]:nodes.append({"id":wb["latest_rag"]["run_id"],"type":"dispute_rag_run"});edges.append({"from":wb["snapshot"]["snapshot_id"],"to":wb["latest_rag"]["run_id"],"relation":"retrieved_with_citations"})
        for r in wb["recommendations"]:nodes.append({"id":r["recommendation_run_id"],"type":"recommendation_only_agent","authority":"none"});edges.append({"from":wb["latest_rag"]["run_id"] if wb["latest_rag"] else dispute_id,"to":r["recommendation_run_id"],"relation":"supports_human_review"})
        return {"recovery_case_to_dispute":up,"nodes":nodes,"edges":edges,"final_resolution_source":"Release 46 evidence-bound independent human dispute resolution only","authority":{"ai_resolves_dispute":False,"automation_changes_accounting":False,"automation_authorizes_payment":False,"automation_collects_or_moves_funds":False}}

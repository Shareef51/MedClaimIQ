from __future__ import annotations
import hashlib, hmac, json, os
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.financial_handoff import FinancialPacketStatus, PaymentIntentStatus, SettlementStatus, FinancialTaskType, FINANCIAL_AUTHORITY
from app.models.claims import ClaimLineModel, ClaimModel
from app.models.governed_closure import ReviewDecisionPacketModel
from app.models.appeal_resolution import AppealFinalResolutionModel
from app.models.post_decision import DecisionHistoryVersionModel
from app.models.financial_handoff import *
from app.repositories.financial_handoff import FinancialHandoffRepository
from app.repositories.post_decision import PostDecisionRepository
from app.repositories.tenancy import MembershipRepository
from app.financial.adapters import FinancialAdapterRegistry
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)
def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canonical(v)).encode()).hexdigest()
def _money(v): return Decimal(str(v)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)

class FinancialHandoffService:
    """Stages financial instructions only after human adjudication + separate human finance authorization.

    This service never executes fund movement. Adapters only acknowledge/stage an already authorized instruction.
    """
    def __init__(self,session:Session,tenant_id:str,adapter_registry:FinancialAdapterRegistry|None=None):
        self.session=session; self.tenant_id=tenant_id; self.repo=FinancialHandoffRepository(session,tenant_id); self.post=PostDecisionRepository(session,tenant_id); self.adapters=adapter_registry or FinancialAdapterRegistry()
    def _membership(self,user_id):
        m=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if m is None or m.status!="active": raise ReviewConflictError("active tenant membership required")
        return m
    def _require_preparer(self,user_id):
        m=self._membership(user_id)
        if m.role not in {"finance_operator","finance_analyst"}: raise ReviewConflictError("human finance operator or analyst membership required")
        return m
    def _require_approver(self,user_id):
        m=self._membership(user_id)
        if m.role!="finance_approver": raise ReviewConflictError("independent human finance approver membership required")
        return m
    def _claim(self,claim_id):
        c=self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id))
        if c is None: raise LookupError("claim not found")
        return c
    def _controlling(self,claim_id):
        history=self.post.history(claim_id)
        if not history: raise ReviewConflictError("controlling human decision history is required before financial handoff")
        h=history[-1]
        if h.source_type=="appeal_final_resolution":
            r=self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.resolution_id==h.source_id))
            if r is None: raise ReviewConflictError("controlling appeal resolution missing")
            return h,r.controlling_decision,_money(r.reconsidered_approved_amount),"appeal_final_resolution",r.resolution_id
        if h.source_type=="original_decision":
            p=self.session.scalar(select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.decision_id==h.source_id,ReviewDecisionPacketModel.status=="closed"))
            if p is None: raise ReviewConflictError("controlling original human decision packet missing")
            c=self._claim(claim_id); approved=_money(c.total_amount if p.decision=="approve" else (p.approved_amount or 0))
            return h,p.decision,approved,"original_decision",p.decision_id
        raise ReviewConflictError("unsupported controlling decision history source")
    def _line_reconciliation(self,claim_id,approved,total):
        lines=list(self.session.scalars(select(ClaimLineModel).where(ClaimLineModel.tenant_id==self.tenant_id,ClaimLineModel.claim_id==claim_id).order_by(ClaimLineModel.line_number)))
        if not lines:
            return [{"line_number":1,"service_code":"claim_total","billed_amount":str(total),"allowed_amount":str(total),"payer_responsibility":str(approved),"member_responsibility":str(_money(total-approved)),"adjustment_reason":"claim_level_allocation"}]
        total_line=sum((_money(x.amount) for x in lines),Decimal("0.00")); allocated=Decimal("0.00"); out=[]
        for idx,line in enumerate(lines):
            billed=_money(line.amount)
            if idx==len(lines)-1: payer=_money(approved-allocated)
            else: payer=_money(approved*(billed/total_line)) if total_line else Decimal("0.00"); allocated+=payer
            payer=max(Decimal("0.00"),min(billed,payer)); member=_money(billed-payer)
            out.append({"claim_line_id":line.claim_line_id,"line_number":line.line_number,"code_system":line.code_system,"service_code":line.service_code,"billed_amount":str(billed),"allowed_amount":str(billed),"payer_responsibility":str(payer),"member_responsibility":str(member),"adjustment_reason":"controlling_human_decision_allocation"})
        return out
    def _audit(self,claim_id,event_type,actor_type,actor_id,payload,idempotency_key):
        existing=self.session.scalar(select(FinancialAuditEventModel).where(FinancialAuditEventModel.tenant_id==self.tenant_id,FinancialAuditEventModel.idempotency_key==idempotency_key))
        if existing:return existing
        prior=self.repo.audit(claim_id); seq=self.repo.next_audit_sequence(claim_id); prev=prior[-1].event_sha256 if prior else None; now=_now(); digest=_sha({"claim_id":claim_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"payload":payload,"previous":prev,"occurred_at":now})
        return self.repo.add(FinancialAuditEventModel(audit_event_id=f"finaud_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,payload=payload,previous_event_sha256=prev,event_sha256=digest,idempotency_key=idempotency_key,occurred_at=now))
    def _emit(self,claim_id,event_type,aggregate_type,aggregate_id,payload,trace_id=None):
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"fin_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type=aggregate_type,aggregate_id=aggregate_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-financial-handoff",payload=payload,metadata={k:v for k,v in payload.items() if k in {"status","packet_id","payment_intent_id","exception_id","task_type"}}),topic=EventTopic.CLAIMS.value)
    def _task(self,claim_id,task_type,key,*,payment_intent_id=None,due_hours=24,priority=50):
        existing=self.session.scalar(select(FinancialTaskModel).where(FinancialTaskModel.tenant_id==self.tenant_id,FinancialTaskModel.idempotency_key==key))
        if existing:return existing
        return self.repo.add(FinancialTaskModel(task_id=f"fintask_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,task_type=task_type,status="open",priority=priority,due_at=_now()+timedelta(hours=due_hours),assigned_user_id=None,idempotency_key=key,created_at=_now(),completed_at=None))
    def _complete_tasks(self,claim_id,task_type,payment_intent_id=None):
        q=select(FinancialTaskModel).where(FinancialTaskModel.tenant_id==self.tenant_id,FinancialTaskModel.claim_id==claim_id,FinancialTaskModel.task_type==task_type,FinancialTaskModel.status=="open")
        if payment_intent_id:q=q.where(FinancialTaskModel.payment_intent_id==payment_intent_id)
        for t in self.session.scalars(q):t.status="completed";t.completed_at=_now()
    def _artifacts(self,p):
        if self.repo.artifacts(p.packet_id):return self.repo.artifacts(p.packet_id)
        eob={"artifact":"EOB","version":"release40-v1","claim_id":p.claim_id,"decision":p.controlling_decision,"claim_total":str(p.claim_total_amount),"payer_responsibility":str(p.payer_responsibility),"member_responsibility":str(p.member_responsibility),"currency":p.currency,"lines":p.line_reconciliation,"decision_history_sha256":p.decision_history_sha256,"human_authority":"controlling outcome created by authorized human adjudication"}
        x835={"artifact":"X12-835-style","version":"release40-v1","BPR":{"amount":str(p.payer_responsibility),"currency":p.currency},"CLP":{"claim_id":p.claim_id,"status":p.controlling_decision,"total_charge":str(p.claim_total_amount),"payment_amount":str(p.payer_responsibility),"patient_responsibility":str(p.member_responsibility)},"SVC":[{"service_code":x.get("service_code"),"charge":x["billed_amount"],"paid":x["payer_responsibility"],"patient_responsibility":x["member_responsibility"]} for x in p.line_reconciliation],"note":"835-style mapping for integration development; trading-partner validation/certification remains external"}
        out=[]
        for typ,content in (("eob_json",eob),("x12_835_style",x835)):
            out.append(self.repo.add(RemittanceArtifactModel(artifact_id=f"remit_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=p.claim_id,packet_id=p.packet_id,artifact_type=typ,format_version="release40-v1",content=content,content_sha256=_sha(content),created_at=_now())))
        return out
    def prepare_packet(self,claim_id,user_id,*,expected_packet_version=None,idempotency_key,trace_id=None):
        self._require_preparer(user_id)
        existing=self.session.scalar(select(FinancialAuthorizationPacketModel).where(FinancialAuthorizationPacketModel.tenant_id==self.tenant_id,FinancialAuthorizationPacketModel.idempotency_key==idempotency_key))
        if existing:return existing
        prior=self.repo.latest_packet(claim_id)
        if prior and expected_packet_version is not None and prior.packet_version!=expected_packet_version: raise ReviewConflictError("stale financial packet version")
        h,decision,approved,source_type,source_id=self._controlling(claim_id); claim=self._claim(claim_id); total=_money(claim.total_amount)
        if approved<0 or approved>total: raise ReviewConflictError("controlling approved amount is outside claim total")
        lines=self._line_reconciliation(claim_id,approved,total); member=_money(total-approved); version=(prior.packet_version+1 if prior else 1); now=_now()
        p=self.repo.add(FinancialAuthorizationPacketModel(packet_id=f"finpkt_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_version=version,status=FinancialPacketStatus.DRAFT.value,controlling_source_type=source_type,controlling_source_id=source_id,decision_history_version_id=h.history_version_id,decision_history_sha256=h.version_sha256,evidence_snapshot_sha256=h.evidence_snapshot_sha256,controlling_decision=decision,claim_total_amount=total,approved_amount=approved,member_responsibility=member,payer_responsibility=approved,currency=claim.currency,line_reconciliation=lines,prepared_by_user_id=user_id,authorized_by_user_id=None,authorization_rationale=None,locked_payload_sha256=None,authorized_payload_sha256=None,idempotency_key=idempotency_key,trace_id=trace_id,created_at=now,locked_at=None,authorized_at=None))
        self._artifacts(p); self._task(claim_id,FinancialTaskType.PACKET_AUTHORIZATION.value,f"fin-auth-task:{p.packet_id}",due_hours=8,priority=80); self._audit(claim_id,"financial.packet.prepared","human",user_id,{"packet_id":p.packet_id,"decision_history_sha256":h.version_sha256,"approved_amount":str(approved)},f"audit:{idempotency_key}"); self._emit(claim_id,"financial.packet.prepared","financial_packet",p.packet_id,{"packet_id":p.packet_id,"status":p.status},trace_id); return p
    def lock_packet(self,claim_id,packet_id,user_id,*,expected_packet_version,idempotency_key,trace_id=None):
        self._require_preparer(user_id); p=self.repo.packet(packet_id,for_update=True)
        if p is None or p.claim_id!=claim_id: raise LookupError("financial packet not found")
        if p.prepared_by_user_id!=user_id: raise ReviewConflictError("only the packet preparer may lock this packet")
        if p.packet_version!=expected_packet_version: raise ReviewConflictError("stale financial packet version")
        current=self._controlling(claim_id)[0]
        if current.history_version_id!=p.decision_history_version_id or current.version_sha256!=p.decision_history_sha256: raise ReviewConflictError("controlling human decision changed; rebuild financial packet")
        payload={"claim_id":claim_id,"packet_id":p.packet_id,"packet_version":p.packet_version,"decision_history_sha256":p.decision_history_sha256,"evidence_snapshot_sha256":p.evidence_snapshot_sha256,"decision":p.controlling_decision,"approved_amount":str(p.approved_amount),"member_responsibility":str(p.member_responsibility),"payer_responsibility":str(p.payer_responsibility),"currency":p.currency,"lines":p.line_reconciliation}
        p.locked_payload_sha256=_sha(payload); p.status=FinancialPacketStatus.PENDING_AUTHORIZATION.value;p.locked_at=_now();self._audit(claim_id,"financial.packet.locked","human",user_id,{"packet_id":p.packet_id,"locked_payload_sha256":p.locked_payload_sha256},f"audit:{idempotency_key}");self._emit(claim_id,"financial.packet.locked","financial_packet",p.packet_id,{"packet_id":p.packet_id,"status":p.status},trace_id);return p
    def authorize_packet(self,claim_id,packet_id,approver_user_id,*,rationale,idempotency_key,trace_id=None):
        self._require_approver(approver_user_id); p=self.repo.packet(packet_id,for_update=True)
        if p is None or p.claim_id!=claim_id: raise LookupError("financial packet not found")
        if p.status==FinancialPacketStatus.AUTHORIZED.value:return p
        if p.status!=FinancialPacketStatus.PENDING_AUTHORIZATION.value or not p.locked_payload_sha256: raise ReviewConflictError("locked financial packet awaiting authorization required")
        if p.prepared_by_user_id==approver_user_id: raise ReviewConflictError("segregation of duties requires a different finance approver")
        if len((rationale or "").strip())<20: raise ReviewConflictError("human finance authorization rationale required")
        if self.repo.active_holds(claim_id): raise ReviewConflictError("active fraud/payment hold blocks financial authorization")
        current=self._controlling(claim_id)[0]
        if current.version_sha256!=p.decision_history_sha256: raise ReviewConflictError("controlling human decision changed after financial packet lock")
        p.authorized_by_user_id=approver_user_id;p.authorization_rationale=rationale;p.authorized_at=_now();p.status=FinancialPacketStatus.AUTHORIZED.value;p.authorized_payload_sha256=_sha({"locked_payload_sha256":p.locked_payload_sha256,"authorized_by":approver_user_id,"rationale":rationale,"authorized_at":p.authorized_at})
        self._complete_tasks(claim_id,FinancialTaskType.PACKET_AUTHORIZATION.value);self._task(claim_id,FinancialTaskType.PAYMENT_HANDOFF.value,f"fin-handoff-task:{p.packet_id}",due_hours=8,priority=75);self._audit(claim_id,"financial.packet.authorized","human_finance_approver",approver_user_id,{"packet_id":p.packet_id,"authorized_payload_sha256":p.authorized_payload_sha256},f"audit:{idempotency_key}");self._emit(claim_id,"financial.packet.authorized","financial_packet",p.packet_id,{"packet_id":p.packet_id,"status":p.status},trace_id);return p
    def place_hold(self,claim_id,user_id,*,hold_type,reason_code,rationale,idempotency_key):
        self._require_preparer(user_id); existing=self.session.scalar(select(PaymentHoldModel).where(PaymentHoldModel.tenant_id==self.tenant_id,PaymentHoldModel.claim_id==claim_id,PaymentHoldModel.reason_code==reason_code,PaymentHoldModel.active.is_(True)))
        if existing:return existing
        row=self.repo.add(PaymentHoldModel(hold_id=f"hold_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,hold_type=hold_type,reason_code=reason_code,rationale=rationale,active=True,placed_by_user_id=user_id,released_by_user_id=None,created_at=_now(),released_at=None));self._audit(claim_id,"financial.hold.placed","human",user_id,{"hold_id":row.hold_id,"reason_code":reason_code},f"audit:{idempotency_key}");return row
    def release_hold(self,claim_id,hold_id,approver_user_id,*,rationale,idempotency_key):
        self._require_approver(approver_user_id);h=self.session.scalar(select(PaymentHoldModel).where(PaymentHoldModel.tenant_id==self.tenant_id,PaymentHoldModel.hold_id==hold_id,PaymentHoldModel.claim_id==claim_id))
        if h is None:raise LookupError("payment hold not found")
        if not h.active:return h
        if len(rationale.strip())<20:raise ReviewConflictError("hold release rationale required")
        h.active=False;h.released_by_user_id=approver_user_id;h.released_at=_now();self._audit(claim_id,"financial.hold.released","human_finance_approver",approver_user_id,{"hold_id":h.hold_id,"rationale":rationale},f"audit:{idempotency_key}");return h
    def stage_payment_intent(self,claim_id,packet_id,user_id,*,payee_ref,idempotency_key,trace_id=None):
        self._require_preparer(user_id);p=self.repo.packet(packet_id)
        if p is None or p.claim_id!=claim_id:raise LookupError("financial packet not found")
        existing=self.repo.intent_for_packet(packet_id)
        if existing:return existing
        if p.status!=FinancialPacketStatus.AUTHORIZED.value or not p.authorized_payload_sha256:raise ReviewConflictError("human-finance-authorized packet required")
        if self.repo.active_holds(claim_id):raise ReviewConflictError("active fraud/payment hold blocks payment intent staging")
        if self._controlling(claim_id)[0].version_sha256!=p.decision_history_sha256: raise ReviewConflictError("controlling human decision superseded the authorized financial packet; rebuild required")
        if _money(p.payer_responsibility)<=0:raise ReviewConflictError("zero-value/denied claim has remittance only and cannot create a payment intent")
        fp=_sha({"tenant":self.tenant_id,"claim":claim_id,"decision_history":p.decision_history_sha256,"amount":str(p.payer_responsibility),"currency":p.currency,"payee_ref":payee_ref})
        duplicate=self.session.scalar(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.payment_fingerprint==fp))
        if duplicate:return duplicate
        row=self.repo.add(PaymentIntentModel(payment_intent_id=f"pay_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=packet_id,amount=p.payer_responsibility,currency=p.currency,payee_ref=payee_ref,status=PaymentIntentStatus.READY.value,payment_fingerprint=fp,external_instruction_id=None,adapter_name=None,idempotency_key=idempotency_key,created_at=_now(),submitted_at=None,settled_at=None));self._audit(claim_id,"payment.intent.staged","human",user_id,{"payment_intent_id":row.payment_intent_id,"packet_id":packet_id,"fingerprint":fp},f"audit:{idempotency_key}");self._emit(claim_id,"financial.payment_intent.staged","payment_intent",row.payment_intent_id,{"payment_intent_id":row.payment_intent_id,"status":row.status},trace_id);return row
    def handoff(self,claim_id,payment_intent_id,*,adapter_name="sandbox-financial-ledger",actor_id="financial-handoff-worker",idempotency_key,trace_id=None):
        if actor_id!="financial-handoff-worker": self._require_preparer(actor_id)
        existing=self.session.scalar(select(FinancialHandoffModel).where(FinancialHandoffModel.tenant_id==self.tenant_id,FinancialHandoffModel.idempotency_key==idempotency_key))
        if existing:return existing
        intent=self.repo.intent(payment_intent_id,for_update=True)
        if intent is None or intent.claim_id!=claim_id:raise LookupError("payment intent not found")
        p=self.repo.packet(intent.packet_id)
        if p is None or p.status!=FinancialPacketStatus.AUTHORIZED.value or not p.authorized_by_user_id:raise ReviewConflictError("worker cannot hand off an instruction without prior human finance authorization")
        if self.repo.active_holds(claim_id):raise ReviewConflictError("active fraud/payment hold blocks outbound handoff")
        if self._controlling(claim_id)[0].version_sha256!=p.decision_history_sha256: raise ReviewConflictError("controlling human decision superseded the financial instruction; outbound handoff blocked")
        if intent.status not in {PaymentIntentStatus.READY.value,PaymentIntentStatus.STAGED.value}:raise ReviewConflictError("payment intent is not eligible for outbound handoff")
        instruction={"instruction_type":"authorized_claim_payment","claim_id":claim_id,"payment_intent_id":intent.payment_intent_id,"packet_id":p.packet_id,"authorized_payload_sha256":p.authorized_payload_sha256,"amount":str(intent.amount),"currency":intent.currency,"payee_ref":intent.payee_ref,"payment_fingerprint":intent.payment_fingerprint,"fund_movement_authority":"external_financial_system_under_separate_controls"}
        instruction_sha=_sha(instruction);adapter=self.adapters.get(adapter_name);result=adapter.stage_instruction(instruction)
        row=self.repo.add(FinancialHandoffModel(handoff_id=f"handoff_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=intent.payment_intent_id,adapter_name=adapter_name,instruction_sha256=instruction_sha,external_instruction_id=result.external_instruction_id,status=result.status,idempotency_key=idempotency_key,trace_id=trace_id,created_at=_now()));intent.status=PaymentIntentStatus.SUBMITTED.value;intent.external_instruction_id=result.external_instruction_id;intent.adapter_name=adapter_name;intent.submitted_at=_now();self._complete_tasks(claim_id,FinancialTaskType.PAYMENT_HANDOFF.value,intent.payment_intent_id);self._task(claim_id,FinancialTaskType.SETTLEMENT_RECONCILIATION.value,f"settlement-recon:{intent.payment_intent_id}",payment_intent_id=intent.payment_intent_id,due_hours=72,priority=70);self._audit(claim_id,"financial.instruction.handed_off","background_worker",actor_id,{"payment_intent_id":intent.payment_intent_id,"external_instruction_id":result.external_instruction_id,"human_authorized_by":p.authorized_by_user_id,"instruction_sha256":instruction_sha},f"audit:{idempotency_key}");self._emit(claim_id,"financial.handoff.submitted","payment_intent",intent.payment_intent_id,{"payment_intent_id":intent.payment_intent_id,"status":intent.status},trace_id);return row
    def ingest_settlement(self,claim_id,payment_intent_id,*,provider_event_id,status,settled_amount=None,currency=None,external_reference=None,payload=None,actor_user_id=None):
        if actor_user_id is not None: self._require_preparer(actor_user_id)
        prior=self.repo.settlement_by_provider_event(provider_event_id)
        if prior:return prior
        intent=self.repo.intent(payment_intent_id,for_update=True)
        if intent is None or intent.claim_id!=claim_id:raise LookupError("payment intent not found")
        if status not in {x.value for x in SettlementStatus}:raise ValueError("unsupported settlement status")
        now=_now();obs_amount=None if settled_amount is None else _money(settled_amount); body=payload or {"provider_event_id":provider_event_id,"status":status,"settled_amount":None if obs_amount is None else str(obs_amount),"currency":currency,"external_reference":external_reference}
        row=self.repo.add(SettlementEventModel(settlement_event_id=f"settle_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,provider_event_id=provider_event_id,status=status,settled_amount=obs_amount,currency=currency,external_reference=external_reference,payload_sha256=_sha(body),occurred_at=now,received_at=now))
        if status==SettlementStatus.SETTLED.value:intent.status=PaymentIntentStatus.SETTLED.value;intent.settled_at=now
        elif status==SettlementStatus.ACCEPTED.value:intent.status=PaymentIntentStatus.ACCEPTED.value
        elif status==SettlementStatus.RETURNED.value:intent.status=PaymentIntentStatus.RETURNED.value
        elif status==SettlementStatus.VOIDED.value:intent.status=PaymentIntentStatus.VOIDED.value
        else:intent.status=PaymentIntentStatus.FAILED.value
        self.reconcile(claim_id,payment_intent_id,actor_id="settlement-ingestion",idempotency_key=f"reconcile:{provider_event_id}");self._audit(claim_id,"settlement.status.ingested","external_financial_system","provider",{"payment_intent_id":payment_intent_id,"provider_event_id":provider_event_id,"status":status},f"audit:settlement:{provider_event_id}");self._emit(claim_id,"financial.settlement.updated","payment_intent",payment_intent_id,{"payment_intent_id":payment_intent_id,"status":intent.status});return row
    def reconcile(self,claim_id,payment_intent_id,*,actor_id,idempotency_key):
        intent=self.repo.intent(payment_intent_id)
        if intent is None or intent.claim_id!=claim_id:raise LookupError("payment intent not found")
        settlements=self.repo.settlements(payment_intent_id);latest=settlements[-1] if settlements else None;created=[]
        def exc(kind,expected,observed):
            existing=self.session.scalar(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,FinancialReconciliationExceptionModel.payment_intent_id==payment_intent_id,FinancialReconciliationExceptionModel.exception_type==kind,FinancialReconciliationExceptionModel.status=="open"))
            if existing:return existing
            row=self.repo.add(FinancialReconciliationExceptionModel(exception_id=f"finexc_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,exception_type=kind,expected=expected,observed=observed,status="open",created_at=_now(),resolved_at=None,resolved_by_user_id=None));self._task(claim_id,FinancialTaskType.EXCEPTION_REVIEW.value,f"fin-exc-task:{row.exception_id}",payment_intent_id=payment_intent_id,due_hours=24,priority=90);created.append(row);return row
        p=self.repo.packet(intent.packet_id)
        if p is not None and self._controlling(claim_id)[0].version_sha256!=p.decision_history_sha256: exc("controlling_decision_superseded",{"decision_history_sha256":self._controlling(claim_id)[0].version_sha256},{"payment_packet_decision_history_sha256":p.decision_history_sha256})
        if latest and latest.status==SettlementStatus.SETTLED.value:
            if latest.settled_amount is None or _money(latest.settled_amount)!=_money(intent.amount):exc("settled_amount_mismatch",{"amount":str(intent.amount)}, {"amount":None if latest.settled_amount is None else str(latest.settled_amount)})
            if latest.currency and latest.currency!=intent.currency:exc("settled_currency_mismatch",{"currency":intent.currency},{"currency":latest.currency})
            if not created:self._complete_tasks(claim_id,FinancialTaskType.SETTLEMENT_RECONCILIATION.value,payment_intent_id)
        elif latest and latest.status in {SettlementStatus.FAILED.value,SettlementStatus.RETURNED.value}:exc("terminal_settlement_status",{"status":"settled"},{"status":latest.status})
        self._audit(claim_id,"financial.reconciliation.completed","deterministic_system",actor_id,{"payment_intent_id":payment_intent_id,"exception_count":len(created),"latest_status":None if latest is None else latest.status},f"audit:{idempotency_key}");return created
    def request_void_reissue(self,claim_id,payment_intent_id,user_id,*,action,reason,idempotency_key):
        self._require_preparer(user_id)
        existing=self.session.scalar(select(PaymentVoidReissueModel).where(PaymentVoidReissueModel.tenant_id==self.tenant_id,PaymentVoidReissueModel.idempotency_key==idempotency_key))
        if existing:return existing
        intent=self.repo.intent(payment_intent_id)
        if intent is None or intent.claim_id!=claim_id:raise LookupError("payment intent not found")
        if action not in {"void","reissue"}:raise ValueError("action must be void or reissue")
        row=self.repo.add(PaymentVoidReissueModel(request_id=f"vr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,action=action,status="pending_approval",reason=reason,requested_by_user_id=user_id,approved_by_user_id=None,replacement_payment_intent_id=None,idempotency_key=idempotency_key,created_at=_now(),approved_at=None));self._task(claim_id,FinancialTaskType.VOID_REISSUE.value,f"void-reissue-task:{row.request_id}",payment_intent_id=payment_intent_id,due_hours=8,priority=95);return row
    def approve_void_reissue(self,claim_id,request_id,approver_user_id,*,idempotency_key):
        self._require_approver(approver_user_id); row=self.session.scalar(select(PaymentVoidReissueModel).where(PaymentVoidReissueModel.tenant_id==self.tenant_id,PaymentVoidReissueModel.request_id==request_id,PaymentVoidReissueModel.claim_id==claim_id))
        if row is None:raise LookupError("void/reissue request not found")
        if row.status=="approved":return row
        if row.requested_by_user_id==approver_user_id:raise ReviewConflictError("void/reissue approval requires a different human finance approver")
        intent=self.repo.intent(row.payment_intent_id,for_update=True);row.status="approved";row.approved_by_user_id=approver_user_id;row.approved_at=_now()
        if row.action=="void":intent.status=PaymentIntentStatus.VOID_PENDING.value
        else:
            intent.status=PaymentIntentStatus.REISSUE_PENDING.value
            replacement_fingerprint=_sha({"original_payment_fingerprint":intent.payment_fingerprint,"reissue_request_id":row.request_id,"human_approved_by":approver_user_id})
            replacement=self.repo.add(PaymentIntentModel(payment_intent_id=f"pay_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=intent.packet_id,amount=intent.amount,currency=intent.currency,payee_ref=intent.payee_ref,status=PaymentIntentStatus.READY.value,payment_fingerprint=replacement_fingerprint,external_instruction_id=None,adapter_name=None,idempotency_key=f"reissue:{row.request_id}",created_at=_now(),submitted_at=None,settled_at=None))
            row.replacement_payment_intent_id=replacement.payment_intent_id
            self._task(claim_id,FinancialTaskType.PAYMENT_HANDOFF.value,f"fin-handoff-task:{replacement.payment_intent_id}",payment_intent_id=replacement.payment_intent_id,due_hours=8,priority=90)
        self._complete_tasks(claim_id,FinancialTaskType.VOID_REISSUE.value,intent.payment_intent_id);self._audit(claim_id,"financial.void_reissue.approved","human_finance_approver",approver_user_id,{"request_id":row.request_id,"action":row.action,"payment_intent_id":intent.payment_intent_id},f"audit:{idempotency_key}");return row
    def traceability(self,claim_id):
        self._claim(claim_id);p=self.repo.latest_packet(claim_id);intents=self.repo.intents(claim_id)
        if p is None:return {"claim_id":claim_id,"nodes":[],"edges":[],"human_finance_authorization_required":True}
        nodes=[{"id":p.evidence_snapshot_sha256,"type":"evidence_snapshot"},{"id":p.decision_history_version_id,"type":"controlling_human_decision","sha256":p.decision_history_sha256},{"id":p.packet_id,"type":"financial_authorization_packet","sha256":p.locked_payload_sha256},{"id":f"finance-authorization:{p.packet_id}","type":"human_finance_authorization","actor_id":p.authorized_by_user_id,"sha256":p.authorized_payload_sha256}]
        edges=[{"from":p.evidence_snapshot_sha256,"to":p.decision_history_version_id,"relationship":"bound_to_human_adjudication"},{"from":p.decision_history_version_id,"to":p.packet_id,"relationship":"controls_financial_packet"},{"from":p.packet_id,"to":f"finance-authorization:{p.packet_id}","relationship":"requires_distinct_human_authorization"}]
        for i in intents:
            nodes.append({"id":i.payment_intent_id,"type":"authorized_financial_instruction","status":i.status,"amount":str(i.amount),"currency":i.currency});edges.append({"from":f"finance-authorization:{p.packet_id}","to":i.payment_intent_id,"relationship":"permits_staging_only"})
            for h in self.repo.handoffs(i.payment_intent_id):nodes.append({"id":h.handoff_id,"type":"external_handoff","external_instruction_id":h.external_instruction_id,"sha256":h.instruction_sha256});edges.append({"from":i.payment_intent_id,"to":h.handoff_id,"relationship":"idempotent_outbound_handoff"})
            for e in self.repo.settlements(i.payment_intent_id):nodes.append({"id":e.settlement_event_id,"type":"settlement_status","status":e.status,"sha256":e.payload_sha256});edges.append({"from":i.payment_intent_id,"to":e.settlement_event_id,"relationship":"external_settlement_status"})
        return {"claim_id":claim_id,"nodes":nodes,"edges":edges,"human_finance_authorization_required":True,"automatic_fund_movement":False}

    def snapshot(self,claim_id):
        self._claim(claim_id);p=self.repo.latest_packet(claim_id);intents=self.repo.intents(claim_id);return {"claim_id":claim_id,"authority":FINANCIAL_AUTHORITY,"traceability":self.traceability(claim_id),"packet":None if p is None else self.packet_view(p),"remittance_artifacts":[] if p is None else [{"artifact_id":a.artifact_id,"artifact_type":a.artifact_type,"format_version":a.format_version,"content_sha256":a.content_sha256,"content":a.content} for a in self.repo.artifacts(p.packet_id)],"active_holds":[{"hold_id":h.hold_id,"hold_type":h.hold_type,"reason_code":h.reason_code,"rationale":h.rationale,"active":h.active} for h in self.repo.active_holds(claim_id)],"payment_intents":[{"payment_intent_id":i.payment_intent_id,"packet_id":i.packet_id,"amount":str(i.amount),"currency":i.currency,"payee_ref":i.payee_ref,"status":i.status,"external_instruction_id":i.external_instruction_id,"payment_fingerprint":i.payment_fingerprint} for i in intents],"settlements":[{"settlement_event_id":s.settlement_event_id,"payment_intent_id":s.payment_intent_id,"provider_event_id":s.provider_event_id,"status":s.status,"settled_amount":None if s.settled_amount is None else str(s.settled_amount),"currency":s.currency,"external_reference":s.external_reference} for i in intents for s in self.repo.settlements(i.payment_intent_id)],"exceptions":[{"exception_id":x.exception_id,"payment_intent_id":x.payment_intent_id,"exception_type":x.exception_type,"expected":x.expected,"observed":x.observed,"status":x.status} for x in self.repo.exceptions(claim_id)],"tasks":[{"task_id":t.task_id,"task_type":t.task_type,"status":t.status,"priority":t.priority,"due_at":t.due_at.isoformat()} for t in self.repo.tasks(claim_id)],"audit":[{"sequence":a.sequence,"event_type":a.event_type,"actor_type":a.actor_type,"actor_id":a.actor_id,"event_sha256":a.event_sha256,"previous_event_sha256":a.previous_event_sha256} for a in self.repo.audit(claim_id)]}
    def packet_view(self,p):
        return {"packet_id":p.packet_id,"packet_version":p.packet_version,"status":p.status,"controlling_source_type":p.controlling_source_type,"controlling_source_id":p.controlling_source_id,"decision_history_version_id":p.decision_history_version_id,"decision_history_sha256":p.decision_history_sha256,"evidence_snapshot_sha256":p.evidence_snapshot_sha256,"controlling_decision":p.controlling_decision,"claim_total_amount":str(p.claim_total_amount),"approved_amount":str(p.approved_amount),"payer_responsibility":str(p.payer_responsibility),"member_responsibility":str(p.member_responsibility),"currency":p.currency,"line_reconciliation":p.line_reconciliation,"prepared_by_user_id":p.prepared_by_user_id,"authorized_by_user_id":p.authorized_by_user_id,"locked_payload_sha256":p.locked_payload_sha256,"authorized_payload_sha256":p.authorized_payload_sha256}

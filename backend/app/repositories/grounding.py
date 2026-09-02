from __future__ import annotations

from datetime import UTC, datetime
import uuid

from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.domain.grounding import GroundingResult, StatementSupport
from app.models.grounding import (
    RAGGuardrailRunModel, RAGPromptInjectionFindingModel, RAGRepairAttemptModel,
    RAGStatementGroundingModel, RAGHumanReviewEscalationModel,
)


class GroundingGuardrailRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def save_result(
        self,
        result: GroundingResult,
        *,
        query_sha256: str,
        query_length: int,
        candidate_sha256: str | None,
        trace_id: str | None,
    ) -> None:
        if result.pack.claim_id != result.claim_id:
            raise ValueError("guardrail result claim mismatch")
        now = datetime.now(UTC)
        supported = sum(1 for check in result.statement_checks if check.support == StatementSupport.SUPPORTED)
        unsupported = sum(1 for check in result.statement_checks if check.support in {StatementSupport.UNSUPPORTED, StatementSupport.CONTRADICTED})
        invalid_citations = sum(1 for check in result.statement_checks if check.citation.invalid_evidence_keys)
        self.session.add(RAGGuardrailRunModel(
            run_id=result.run_id, tenant_id=self.tenant_id, claim_id=result.claim_id,
            pack_id=result.pack.pack_id, query_sha256=query_sha256, query_length=query_length,
            candidate_sha256=candidate_sha256, guardrail_version=result.guardrail_version,
            decision=result.decision.value, answerable=result.answerability.answerable,
            answerability_score=result.answerability.score, evidence_quality=result.evidence_quality.score,
            safe_evidence_count=len(result.screened.safe_items),
            excluded_injection_count=len(result.screened.excluded_evidence_keys),
            supported_statement_count=supported, unsupported_statement_count=unsupported,
            invalid_citation_count=invalid_citations,
            unresolved_material_contradictions=result.evidence_quality.unresolved_material_contradictions,
            repair_attempt_count=len(result.repairs), escalation_reasons=list(result.escalation_reasons),
            trace_id=trace_id, created_at=now,
        ))
        for finding in result.screened.findings:
            self.session.add(RAGPromptInjectionFindingModel(
                finding_id=f"inj_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=result.claim_id,
                run_id=result.run_id, evidence_key=finding.evidence_key, content_sha256=finding.content_sha256,
                risk=finding.risk.value, score=finding.score, rule_ids=list(finding.rule_ids),
                action=finding.action, created_at=now,
            ))
        for check in result.statement_checks:
            self.session.add(RAGStatementGroundingModel(
                check_id=f"stmtchk_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=result.claim_id,
                run_id=result.run_id, statement_id=check.statement_id,
                statement_sha256=check.statement_sha256,
                support_status=check.support.value, support_score=check.support_score,
                citation_status=check.citation.status.value,
                cited_evidence_keys=list(check.citation.verified_evidence_keys),
                invalid_evidence_keys=list(check.citation.invalid_evidence_keys),
                numeric_integrity=check.numeric_integrity, medical_code_integrity=check.medical_code_integrity,
                contradiction_safe=check.contradiction_safe, reasons=list(check.reasons), created_at=now,
            ))
        for repair in result.repairs:
            self.session.add(RAGRepairAttemptModel(
                repair_id=f"repair_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=result.claim_id,
                run_id=result.run_id, attempt_number=repair.attempt_number, strategy=repair.strategy,
                query_sha256=repair.query_sha256, requested_retrievers=list(repair.requested_retrievers),
                result_pack_id=repair.result_pack_id, confidence=repair.confidence,
                answerable=repair.answerable, created_at=now,
            ))
        if result.escalation_reasons:
            self.session.add(RAGHumanReviewEscalationModel(
                escalation_id=f"hres_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=result.claim_id,
                run_id=result.run_id, pack_id=result.pack.pack_id, trigger_decision=result.decision.value,
                reason_codes=list(result.escalation_reasons), status="requested", created_at=now,
            ))
        self.session.flush()

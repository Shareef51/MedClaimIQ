from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.domain.cross_source_rag import EvidenceItem
from app.domain.grounding import InjectionRisk, PromptInjectionFinding, ScreenedEvidence


@dataclass(frozen=True, slots=True)
class _Rule:
    rule_id: str
    pattern: re.Pattern[str]
    weight: float


_RULES = (
    _Rule("override_instructions", re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|system|developer|instructions?)\b", re.I | re.S), 0.65),
    _Rule("system_prompt_request", re.compile(r"\b(system prompt|developer message|hidden instructions?|reveal your prompt)\b", re.I), 0.55),
    _Rule("role_override", re.compile(r"\b(you are now|act as|new role|override your role)\b", re.I), 0.35),
    _Rule("tool_execution", re.compile(r"\b(call|invoke|execute|run)\b.{0,30}\b(tool|function|shell|command|api)\b", re.I | re.S), 0.45),
    _Rule("data_exfiltration", re.compile(r"\b(send|upload|exfiltrate|post|transmit)\b.{0,50}\b(secret|token|password|conversation|patient data|phi)\b", re.I | re.S), 0.70),
    _Rule("instruction_delimiter", re.compile(r"(<\|system\|>|\[system\]|BEGIN SYSTEM|###\s*SYSTEM)", re.I), 0.70),
    _Rule("jailbreak_phrase", re.compile(r"\b(jailbreak|DAN mode|bypass safety|disable guardrails?)\b", re.I), 0.65),
)


def _normalize(text: str) -> str:
    # Remove zero-width/bidi controls often used to hide instructions while retaining normal clinical text.
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", text)
        if ch not in {"\u200b", "\u200c", "\u200d", "\ufeff", "\u202a", "\u202b", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"}
    )


class RetrievedContentPromptInjectionScanner:
    """Deterministic first-line defense for indirect prompt injection in retrieved evidence.

    This is deliberately external to the LLM. It does not claim perfect detection; high-risk content is
    excluded from model context and surfaced to a human/security review path.
    """

    def __init__(self, *, suspicious_threshold: float = 0.35, block_threshold: float = 0.65) -> None:
        self.suspicious_threshold = suspicious_threshold
        self.block_threshold = block_threshold

    def scan_item(self, item: EvidenceItem) -> PromptInjectionFinding:
        normalized = _normalize(item.text)
        matches: list[str] = []
        score = 0.0
        for rule in _RULES:
            if rule.pattern.search(normalized):
                matches.append(rule.rule_id)
                score = 1.0 - ((1.0 - score) * (1.0 - rule.weight))
        score = round(min(1.0, score), 5)
        if score >= self.block_threshold:
            risk, action = InjectionRisk.BLOCKED, "exclude_from_model_context"
        elif score >= self.suspicious_threshold:
            risk, action = InjectionRisk.SUSPICIOUS, "quarantine_for_review"
        else:
            risk, action = InjectionRisk.CLEAN, "allow_as_untrusted_evidence"
        return PromptInjectionFinding(
            evidence_key=item.evidence_key,
            risk=risk,
            score=score,
            rule_ids=tuple(matches),
            action=action,
            content_sha256=item.content_sha256,
        )

    def screen(self, items: tuple[EvidenceItem, ...]) -> ScreenedEvidence:
        findings = tuple(self.scan_item(item) for item in items)
        by_key = {finding.evidence_key: finding for finding in findings}
        safe = tuple(item for item in items if by_key[item.evidence_key].risk == InjectionRisk.CLEAN)
        excluded = tuple(
            finding.evidence_key for finding in findings
            if finding.risk in {InjectionRisk.SUSPICIOUS, InjectionRisk.BLOCKED}
        )
        return ScreenedEvidence(safe_items=safe, findings=findings, excluded_evidence_keys=excluded)

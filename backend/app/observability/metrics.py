from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _meter():
    try:
        from opentelemetry import metrics
        return metrics.get_meter("medclaimiq")
    except ImportError:
        return None


@lru_cache(maxsize=1)
def _instruments():
    meter = _meter()
    if meter is None:
        return None
    return {
        "operations": meter.create_counter("medclaimiq.ai.operations", description="AI/RAG/tool operations"),
        "tokens": meter.create_counter("medclaimiq.ai.tokens", description="LLM token usage"),
        "latency": meter.create_histogram("medclaimiq.ai.operation.latency", unit="ms"),
        "errors": meter.create_counter("medclaimiq.ai.errors", description="AI/RAG/tool operation errors"),
        "financial_intelligence": meter.create_histogram("medclaimiq.financial.intelligence.value", description="Read-only financial intelligence measurements"),
        "recovery_settlement_intelligence": meter.create_histogram("medclaimiq.recovery.settlement.intelligence.value", description="Read-only recovery settlement intelligence measurements"),
        "recovery_control_assurance": meter.create_histogram("medclaimiq.recovery.control.assurance.value", description="Governed recovery control-assurance measurements; never a certification or payment authority"),
        "regulatory_transport": meter.create_histogram("medclaimiq.regulatory.transport.value", description="Regulatory transport operational measurements; never report-certification or financial authority"),
        "regulatory_supervision": meter.create_histogram("medclaimiq.regulatory.supervision.value", description="Regulatory supervisory reconciliation measurements; monitoring only and never a certification/submission/payment authority"),
        "regulatory_examination": meter.create_histogram("medclaimiq.regulatory.examination.value", description="Regulatory examination/inquiry measurements; AI drafts are never response approval or financial authority"),
        "regulatory_remediation": meter.create_histogram("medclaimiq.regulatory.remediation.value", description="Regulatory remediation/control-retest measurements; monitoring and recommendation only, never approval or financial authority"),
        "regulatory_portfolio_oversight": meter.create_histogram("medclaimiq.regulatory.portfolio.oversight.value", description="Cross-finding/systemic-control portfolio measurements; analysis only and never certification or financial authority"),
    }


def record_operation(*, operation: str, latency_ms: float | None = None, status: str = "ok", attributes: dict[str, str | int | float | bool] | None = None) -> None:
    instruments = _instruments()
    if instruments is None: return
    attrs = {"operation": operation, **(attributes or {})}
    instruments["operations"].add(1, attrs)
    if latency_ms is not None: instruments["latency"].record(float(latency_ms), attrs)
    if status not in {"ok", "success", "succeeded", "completed", "dry_run", "approval_required"}:
        instruments["errors"].add(1, attrs)


def record_tokens(*, model: str, input_tokens: int | None, output_tokens: int | None) -> None:
    instruments = _instruments()
    if instruments is None: return
    if input_tokens: instruments["tokens"].add(int(input_tokens), {"model": model, "direction": "input"})
    if output_tokens: instruments["tokens"].add(int(output_tokens), {"model": model, "direction": "output"})


def record_financial_intelligence(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit analytics-only measurements; this function has no financial/accounting mutation authority."""
    instruments = _instruments()
    if instruments is None: return
    attrs = {"metric": metric, **(attributes or {})}
    instruments["financial_intelligence"].record(float(value), attrs)


def record_recovery_settlement_intelligence(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit read-only settlement intelligence metrics; never a financial control signal."""
    instruments = _instruments()
    if instruments is None: return
    instruments["recovery_settlement_intelligence"].record(float(value), {"metric": metric, **(attributes or {})})


def record_recovery_control_assurance(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit control-assurance telemetry only; metrics cannot certify, submit, post journals, or move funds."""
    instruments = _instruments()
    if instruments is None: return
    instruments["recovery_control_assurance"].record(float(value), {"metric": metric, **(attributes or {})})


def record_regulatory_transport(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit transport/SLA telemetry only; metrics never authorize release, certification, payments, collections, or fund movement."""
    instruments = _instruments()
    if instruments is None: return
    instruments["regulatory_transport"].record(float(value), {"metric": metric, **(attributes or {})})


def record_regulatory_supervision(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit supervisory reconciliation telemetry only; metrics can never certify, submit, alter accounting, authorize payment, collect, or move funds."""
    instruments = _instruments()
    if instruments is None: return
    instruments["regulatory_supervision"].record(float(value), {"metric": metric, **(attributes or {})})


def record_regulatory_examination(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit examination/inquiry operations telemetry only; metrics never approve responses or mutate governed finance/accounting state."""
    instruments = _instruments()
    if instruments is None: return
    instruments["regulatory_examination"].record(float(value), {"metric": metric, **(attributes or {})})


def record_regulatory_remediation(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit remediation monitoring telemetry only; metrics never approve remediation, certify closure, alter accounting, authorize payment, collect, or move funds."""
    instruments = _instruments()
    if instruments is None: return
    instruments["regulatory_remediation"].record(float(value), {"metric": metric, **(attributes or {})})


def record_regulatory_portfolio_oversight(*, metric: str, value: float, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Emit portfolio oversight telemetry only; metrics never attest management, certify controls, mutate finance/accounting, authorize payment, collect, or move funds."""
    instruments = _instruments()
    if instruments is None: return
    instruments["regulatory_portfolio_oversight"].record(float(value), {"metric": metric, **(attributes or {})})

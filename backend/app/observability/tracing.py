from __future__ import annotations

import contextlib
import contextvars
import time
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from app.observability.redaction import sanitize_attributes

_fallback_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("llmops_fallback_trace_id", default=None)
_fallback_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("llmops_fallback_span_id", default=None)


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str
    traceparent: str


def _otel():
    try:
        from opentelemetry import trace
        return trace
    except ImportError:
        return None


def current_trace_id() -> str | None:
    trace = _otel()
    if trace is not None:
        ctx = trace.get_current_span().get_span_context()
        if getattr(ctx, "is_valid", False):
            return format(ctx.trace_id, "032x")
    return _fallback_trace_id.get()


def current_span_id() -> str | None:
    trace = _otel()
    if trace is not None:
        ctx = trace.get_current_span().get_span_context()
        if getattr(ctx, "is_valid", False):
            return format(ctx.span_id, "016x")
    return _fallback_span_id.get()


def current_trace_context() -> TraceContext | None:
    trace_id = current_trace_id(); span_id = current_span_id()
    if not trace_id or not span_id:
        return None
    return TraceContext(trace_id, span_id, f"00-{trace_id}-{span_id}-01")


def inject_trace_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    carrier = dict(headers or {})
    trace = _otel()
    if trace is not None:
        try:
            from opentelemetry import propagate
            propagate.inject(carrier)
            return carrier
        except Exception:
            pass
    ctx = current_trace_context()
    if ctx and "traceparent" not in carrier:
        carrier["traceparent"] = ctx.traceparent
    return carrier


@contextlib.contextmanager
def traced_operation(name: str, *, attributes: Mapping[str, Any] | None = None, kind: str = "internal") -> Iterator[dict[str, Any]]:
    safe = sanitize_attributes(dict(attributes or {}))
    trace = _otel()
    started = time.perf_counter()
    if trace is not None:
        tracer = trace.get_tracer("medclaimiq")
        kind_map = {
            "server": trace.SpanKind.SERVER, "client": trace.SpanKind.CLIENT,
            "producer": trace.SpanKind.PRODUCER, "consumer": trace.SpanKind.CONSUMER,
        }
        with tracer.start_as_current_span(name, kind=kind_map.get(kind, trace.SpanKind.INTERNAL), attributes=_flatten_attributes(safe)) as span:
            state = {"trace_id": current_trace_id(), "span_id": current_span_id(), "started": started}
            try:
                yield state
                span.set_attribute("medclaimiq.latency_ms", round((time.perf_counter() - started) * 1000, 2))
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.Status(trace.StatusCode.ERROR, type(exc).__name__))
                raise
        return
    trace_token = None; span_token = None
    if _fallback_trace_id.get() is None:
        trace_token = _fallback_trace_id.set(uuid.uuid4().hex)
    span_token = _fallback_span_id.set(uuid.uuid4().hex[:16])
    try:
        yield {"trace_id": current_trace_id(), "span_id": current_span_id(), "started": started}
    finally:
        _fallback_span_id.reset(span_token)
        if trace_token is not None: _fallback_trace_id.reset(trace_token)




@contextlib.contextmanager
def extracted_trace_operation(name: str, *, carrier: Mapping[str, str], attributes: Mapping[str, Any] | None = None, kind: str = "consumer"):
    trace = _otel()
    if trace is None:
        with traced_operation(name, attributes=attributes, kind=kind) as state:
            yield state
        return
    try:
        from opentelemetry import propagate
        ctx = propagate.extract(carrier=carrier)
        tracer = trace.get_tracer("medclaimiq")
        kind_map = {"consumer": trace.SpanKind.CONSUMER, "server": trace.SpanKind.SERVER}
        with tracer.start_as_current_span(name, context=ctx, kind=kind_map.get(kind, trace.SpanKind.INTERNAL), attributes=_flatten_attributes(sanitize_attributes(dict(attributes or {})))):
            yield {"trace_id": current_trace_id(), "span_id": current_span_id()}
    except Exception:
        with traced_operation(name, attributes=attributes, kind=kind) as state:
            yield state

def _flatten_attributes(value: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, bool, int, float)) or item is None:
            if item is not None: out[f"medclaimiq.{key}"] = item
        elif isinstance(item, list):
            out[f"medclaimiq.{key}"] = [str(v)[:200] for v in item]
        else:
            out[f"medclaimiq.{key}"] = str(item)[:512]
    return out


def configure_observability(app, settings) -> dict[str, object]:
    """Configure OTel if installed. Falls back to local correlation if dependencies are absent."""
    result: dict[str, object] = {"otel": False, "exporters": []}
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError:
        return result

    provider = TracerProvider(resource=Resource.create({
        "service.name": settings.service_name,
        "deployment.environment.name": settings.environment,
        "openinference.project.name": settings.phoenix_project,
    }), sampler=_build_sampler(settings))
    for endpoint, headers, label in _exporter_specs(settings):
        if not endpoint: continue
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers or None)))
        result["exporters"].append(label)
    trace.set_tracer_provider(provider)
    result["otel"] = True
    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            metric_endpoint=settings.otel_exporter_otlp_endpoint.rstrip("/")
            if not metric_endpoint.endswith("/v1/metrics"): metric_endpoint += "/v1/metrics"
            reader=PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=metric_endpoint),export_interval_millis=30000)
            metrics.set_meter_provider(MeterProvider(resource=provider.resource,metric_readers=[reader]))
            result["metrics"] = True
        except ImportError:
            result["metrics"] = False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider, excluded_urls="/api/v1/health")
        result["fastapi"] = True
    except ImportError:
        result["fastapi"] = False
    return result


def _build_sampler(settings):
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    ratio = min(1.0, max(0.0, float(settings.otel_trace_sample_ratio)))
    return ParentBased(TraceIdRatioBased(ratio))


def _exporter_specs(settings):
    specs: list[tuple[str | None, dict[str, str], str]] = []
    if settings.otel_exporter_otlp_endpoint:
        endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
        if not endpoint.endswith("/v1/traces"): endpoint += "/v1/traces"
        specs.append((endpoint, {}, "otlp"))
    if settings.phoenix_enabled and settings.phoenix_collector_endpoint:
        endpoint = settings.phoenix_collector_endpoint.rstrip("/")
        if not endpoint.endswith("/v1/traces"): endpoint += "/v1/traces"
        headers = {"x-project-name": settings.phoenix_project}
        if settings.phoenix_api_key:
            headers["authorization"] = f"Bearer {settings.phoenix_api_key.get_secret_value()}"
        specs.append((endpoint, headers, "phoenix"))
    if settings.langsmith_enabled and settings.langsmith_api_key:
        specs.append((settings.langsmith_otel_endpoint, {
            "x-api-key": settings.langsmith_api_key.get_secret_value(),
            "Langsmith-Project": settings.langsmith_project,
        }, "langsmith"))
    return specs

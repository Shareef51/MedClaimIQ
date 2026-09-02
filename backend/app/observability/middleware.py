from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.redaction import safe_identifier
from app.observability.tracing import current_span_id, current_trace_id, traced_operation
from app.observability.metrics import record_operation
import time


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        route = request.url.path
        started=time.perf_counter()
        with traced_operation("http.request", kind="server", attributes={"http_method": request.method, "http_route": route}) as ctx:
            request.state.trace_id = ctx.get("trace_id")
            request.state.span_id = ctx.get("span_id")
            response = await call_next(request)
            response.headers["X-Trace-Id"] = current_trace_id() or request.state.trace_id or ""
            response.headers["X-Span-Id"] = current_span_id() or request.state.span_id or ""
            tenant = getattr(request.state, "tenant_id", None)
            if tenant:
                response.headers["X-Tenant-Correlation"] = safe_identifier(tenant) or ""
            record_operation(operation="http.request",latency_ms=(time.perf_counter()-started)*1000,status="ok" if response.status_code<500 else "error",attributes={"method":request.method,"route":route,"status_code":response.status_code})
            return response

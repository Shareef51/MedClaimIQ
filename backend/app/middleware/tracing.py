from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.tracing import traced_operation


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Establishes a request-scoped trace context and echoes it back for client-side correlation."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        with traced_operation(f"http.{request.method.lower()}", kind="server") as state:
            response = await call_next(request)
            trace_id = state.get("trace_id")
            if trace_id:
                response.headers.setdefault("x-trace-id", trace_id)
            return response

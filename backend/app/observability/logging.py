from __future__ import annotations

import json
import logging
from app.observability.redaction import sanitize_attributes
from app.observability.tracing import current_span_id, current_trace_id


class CorrelationJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = sanitize_attributes({
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "trace_id": current_trace_id(),
            "span_id": current_span_id(),
        })
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(level: str = "INFO") -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for handler in root.handlers:
        handler.setFormatter(CorrelationJSONFormatter())
    try:
        import structlog
    except ImportError:
        return

    def correlate(_, __, event_dict):
        event_dict["trace_id"] = current_trace_id()
        event_dict["span_id"] = current_span_id()
        return sanitize_attributes(event_dict)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            correlate,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        cache_logger_on_first_use=True,
    )


def correlated_log_payload(event: str, **attributes):
    return json.dumps(sanitize_attributes({"event":event,"trace_id":current_trace_id(),"span_id":current_span_id(),**attributes}), sort_keys=True)

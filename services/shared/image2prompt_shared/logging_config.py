"""Centralized logging setup. Services call ``configure_logging`` once at startup
and use ``get_logger(__name__)`` everywhere. Supports plain or JSON output and
injects the active OTEL trace/span id into each record when available.
"""

from __future__ import annotations

import json
import logging
import sys

_CONFIGURED = False


class _TraceContextFilter(logging.Filter):
    """Attach trace_id/span_id from the current OTEL span, if any (best-effort)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = "-"
        record.span_id = "-"
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context() if span else None
            if ctx and getattr(ctx, "is_valid", False):
                record.trace_id = format(ctx.trace_id, "032x")
                record.span_id = format(ctx.span_id, "016x")
        except Exception:
            pass
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(*, service_name: str, level: str = "INFO", as_json: bool = False) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_TraceContextFilter())
    if as_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                f"%(asctime)s %(levelname)s [{service_name}] "
                "[trace=%(trace_id)s span=%(span_id)s] %(name)s: %(message)s"
            )
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

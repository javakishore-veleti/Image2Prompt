"""Observability: OpenTelemetry tracing + metrics (the Python analogue of
Micrometer), driven entirely by feature toggles and designed to NEVER raise.

Guarantees:
- If ``otel_enabled`` is false, or the SDK isn't installed, or the collector is
  unreachable, everything degrades to a no-op. Business code is never affected.
- ``@observe`` wraps a method in a span + latency histogram + call counter, and
  adds feature-toggled span attributes. It re-raises *business* exceptions (so
  behavior is unchanged) but swallows any *observability* failure.
- ``Metrics`` exposes counters/histograms for critical points; recording is
  always safe even when metrics are disabled or the SDK is absent.
"""

from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable

from .logging_config import get_logger

log = get_logger(__name__)

# Resolved once by init_observability(); until then everything is a safe no-op.
_ENABLED = False
_TRACES = False
_METRICS = False
_SPAN_ATTRS = False
_tracer = None
_meter = None
_metric_cache: dict[str, Any] = {}


def init_observability(settings) -> None:
    """Best-effort OTEL setup. Any failure logs a warning and falls back to no-op."""
    global _ENABLED, _TRACES, _METRICS, _SPAN_ATTRS, _tracer, _meter
    _ENABLED = bool(getattr(settings, "otel_enabled", False))
    _TRACES = _ENABLED and bool(getattr(settings, "otel_traces_enabled", True))
    _METRICS = _ENABLED and bool(getattr(settings, "otel_metrics_enabled", True))
    _SPAN_ATTRS = bool(getattr(settings, "otel_span_attrs_enabled", True))

    if not _ENABLED:
        log.info("observability: OTEL disabled (otel_enabled=false) — using no-op")
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create(
            {
                "service.name": getattr(settings, "service_name", "service"),
                "service.namespace": getattr(settings, "otel_service_namespace", "image2prompt"),
            }
        )
        endpoint = getattr(settings, "otel_exporter_otlp_endpoint", None)
        console = bool(getattr(settings, "otel_console_fallback", False))

        if _TRACES:
            _setup_traces(trace, resource, endpoint, console)
            _tracer = trace.get_tracer("image2prompt")
        if _METRICS:
            _setup_metrics(metrics, resource, endpoint, console)
            _meter = metrics.get_meter("image2prompt")
        log.info("observability: OTEL initialized (traces=%s metrics=%s)", _TRACES, _METRICS)
    except Exception as exc:  # SDK missing / exporter init failed — never fatal
        _TRACES = _METRICS = False
        _tracer = _meter = None
        log.warning("observability: OTEL init failed, continuing without it: %s", exc)


def _setup_traces(trace, resource, endpoint, console) -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=resource)
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    except Exception as exc:
        log.warning("observability: OTLP trace exporter unavailable: %s", exc)
        if console:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def _setup_metrics(metrics, resource, endpoint, console) -> None:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

    readers = []
    try:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint)))
    except Exception as exc:
        log.warning("observability: OTLP metric exporter unavailable: %s", exc)
        if console:
            readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))


# --------------------------------------------------------------------------- #
# Metrics facade (critical-point counters/histograms)
# --------------------------------------------------------------------------- #
class Metrics:
    @staticmethod
    def counter_add(name: str, value: int = 1, attrs: dict | None = None) -> None:
        if not _METRICS or _meter is None:
            return
        try:
            inst = _metric_cache.get(f"c:{name}")
            if inst is None:
                inst = _meter.create_counter(name)
                _metric_cache[f"c:{name}"] = inst
            inst.add(value, attributes=attrs or {})
        except Exception:
            pass

    @staticmethod
    def histogram_record(name: str, value: float, attrs: dict | None = None) -> None:
        if not _METRICS or _meter is None:
            return
        try:
            inst = _metric_cache.get(f"h:{name}")
            if inst is None:
                inst = _meter.create_histogram(name)
                _metric_cache[f"h:{name}"] = inst
            inst.record(value, attributes=attrs or {})
        except Exception:
            pass


def set_span_attributes(attrs: dict[str, Any]) -> None:
    """Add attributes to the current span, gated by the span-attrs feature toggle."""
    if not _TRACES or not _SPAN_ATTRS:
        return
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        for k, v in attrs.items():
            span.set_attribute(k, v)
    except Exception:
        pass


def observe(span_name: str | None = None, *, metric: str | None = None) -> Callable:
    """Decorate a (sync or async) layer method to emit a span + latency histogram
    + invocation counter. Observability failures are swallowed; business
    exceptions propagate unchanged."""

    def decorator(func: Callable) -> Callable:
        name = span_name or func.__qualname__
        metric_base = metric or name.replace(".", "_").lower()

        def _record(start: float, status: str) -> None:
            Metrics.counter_add(f"{metric_base}.calls", 1, {"status": status})
            Metrics.histogram_record(f"{metric_base}.duration_ms", (time.perf_counter() - start) * 1000, {"status": status})

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def awrapper(*args, **kwargs):
                start = time.perf_counter()
                cm = _span(name)
                with cm:
                    try:
                        result = await func(*args, **kwargs)
                        _record(start, "ok")
                        return result
                    except Exception:
                        _record(start, "error")
                        raise

            return awrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            with _span(name):
                try:
                    result = func(*args, **kwargs)
                    _record(start, "ok")
                    return result
                except Exception:
                    _record(start, "error")
                    raise

        return wrapper

    return decorator


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _span(name: str):
    if not _TRACES or _tracer is None:
        return _NullCtx()
    try:
        return _tracer.start_as_current_span(name)
    except Exception:
        return _NullCtx()

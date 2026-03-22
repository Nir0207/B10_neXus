from __future__ import annotations

import atexit
import contextlib
import contextvars
import logging
import os
import queue
import sys
import threading
from dataclasses import dataclass
from typing import Any, Iterator

from loguru import logger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


_DEFAULT_SERVICE_NAME = "bionexus"
_DEFAULT_ENVIRONMENT = "local"
_GENE_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("gene_context", default=None)
_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False
_ASYNC_SINK: "_AsyncOTelSink | None" = None
_STANDARD_LOG_RECORD_KEYS = frozenset(
    logging.LogRecord(
        name="bionexus",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__.keys()
)


def _default_otlp_logs_endpoint() -> str:
    explicit_logs_endpoint = os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT")
    if explicit_logs_endpoint:
        return explicit_logs_endpoint.rstrip("/")
    generic_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if generic_endpoint:
        return f"{generic_endpoint.rstrip('/')}/v1/logs"
    return "http://localhost:4318/v1/logs"


def _otlp_headers() -> dict[str, str]:
    raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers


def _patch_record(record: dict[str, Any]) -> None:
    extra = record["extra"]
    extra.setdefault("service_name", _DEFAULT_SERVICE_NAME)
    extra.setdefault("environment", _DEFAULT_ENVIRONMENT)
    extra.setdefault("gene_context", _GENE_CONTEXT.get())


@dataclass(frozen=True, slots=True)
class _QueuedLogRecord:
    logger_name: str
    level_number: int
    message: str
    pathname: str
    lineno: int
    exception: Any
    extra: dict[str, Any]


class _AsyncOTelSink:
    def __init__(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        queue_capacity: int,
        service_name: str,
        environment: str,
    ) -> None:
        resource = Resource.create(
            {
                "service.name": service_name,
                "deployment.environment": environment,
            }
        )
        exporter = OTLPLogExporter(endpoint=endpoint, headers=headers)
        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        self._provider = provider
        self._handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
        self._queue: queue.Queue[_QueuedLogRecord] = queue.Queue(maxsize=queue_capacity)
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run, name="ops-otel-log-worker", daemon=True)
        self._worker.start()

    def enqueue(self, message: Any) -> None:
        record = message.record
        try:
            self._queue.put_nowait(
                _QueuedLogRecord(
                    logger_name=str(record["name"]),
                    level_number=int(record["level"].no),
                    message=str(record["message"]),
                    pathname=str(record["file"].path),
                    lineno=int(record["line"]),
                    exception=record["exception"],
                    extra=dict(record["extra"]),
                )
            )
        except queue.Full:
            return

    def shutdown(self) -> None:
        self._stop_event.set()
        self._worker.join(timeout=2.0)
        with contextlib.suppress(Exception):
            self._provider.force_flush()
        with contextlib.suppress(Exception):
            self._provider.shutdown()

    def _run(self) -> None:
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                payload = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._emit(payload)
            except Exception:
                continue
            finally:
                self._queue.task_done()

    def _emit(self, payload: _QueuedLogRecord) -> None:
        log_record = logging.LogRecord(
            name=payload.logger_name,
            level=payload.level_number,
            pathname=payload.pathname,
            lineno=payload.lineno,
            msg=payload.message,
            args=(),
            exc_info=self._exc_info(payload.exception),
        )
        for key, value in payload.extra.items():
            setattr(log_record, key, value)
        self._handler.emit(log_record)

    @staticmethod
    def _exc_info(exception: Any) -> tuple[type[BaseException], BaseException, Any] | None:
        if exception is None:
            return None
        exception_type = getattr(exception, "type", None)
        exception_value = getattr(exception, "value", None)
        exception_traceback = getattr(exception, "traceback", None)
        if exception_type is None or exception_value is None:
            return None
        return (exception_type, exception_value, exception_traceback)


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("opentelemetry"):
            return

        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        extra = {
            "service_name": getattr(record, "service_name", _DEFAULT_SERVICE_NAME),
            "environment": getattr(record, "environment", _DEFAULT_ENVIRONMENT),
            "gene_context": getattr(record, "gene_context", _GENE_CONTEXT.get()),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_KEYS or key in extra:
                continue
            extra[key] = value
        logger.bind(**extra).opt(exception=record.exc_info, depth=6).log(level, record.getMessage())


@contextlib.contextmanager
def gene_context(value: str | None) -> Iterator[None]:
    token = _GENE_CONTEXT.set(value)
    try:
        yield
    finally:
        _GENE_CONTEXT.reset(token)


def configure_logging(
    *,
    service_name: str,
    environment: str = "local",
    console_level: str = "INFO",
    queue_capacity: int = 2048,
) -> Any:
    global _ASYNC_SINK, _CONFIGURED, _DEFAULT_ENVIRONMENT, _DEFAULT_SERVICE_NAME

    _DEFAULT_SERVICE_NAME = service_name
    _DEFAULT_ENVIRONMENT = environment

    with _CONFIG_LOCK:
        if _CONFIGURED:
            return logger.bind(service_name=service_name, environment=environment)

        logger.remove()
        logger.configure(patcher=_patch_record)
        logger.add(
            sys.stderr,
            level=console_level,
            enqueue=True,
            backtrace=True,
            diagnose=False,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | "
                "{extra[service_name]} | gene={extra[gene_context]} | {message}"
            ),
        )

        otlp_endpoint = _default_otlp_logs_endpoint()
        try:
            _ASYNC_SINK = _AsyncOTelSink(
                endpoint=otlp_endpoint,
                headers=_otlp_headers(),
                queue_capacity=queue_capacity,
                service_name=service_name,
                environment=environment,
            )
        except Exception:
            _ASYNC_SINK = None
        else:
            logger.add(_ASYNC_SINK.enqueue, catch=True)

        logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
        _mute_noisy_loggers()
        _CONFIGURED = True

    return logger.bind(service_name=service_name, environment=environment)


def _mute_noisy_loggers() -> None:
    for logger_name in (
        "asyncio",
        "httpcore",
        "httpx",
        "multipart",
        "uvicorn.access",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


@atexit.register
def _shutdown_logging() -> None:
    if _ASYNC_SINK is not None:
        _ASYNC_SINK.shutdown()

"""
Request ID middleware for tracking requests across logs and metrics.

Adds a unique request_id to each HTTP request and makes it available
in structlog context for correlation across distributed logs.
"""
import logging
import uuid
from types import SimpleNamespace

from django.utils.deprecation import MiddlewareMixin

try:
    import structlog  # type: ignore
    _STRUCTLOG_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback quando structlog não instalado
    _STRUCTLOG_AVAILABLE = False
    structlog = SimpleNamespace(  # type: ignore
        contextvars=SimpleNamespace(
            bind_contextvars=lambda **kwargs: None,
            clear_contextvars=lambda: None,
        ),
        get_logger=lambda name=None: logging.getLogger(name or __name__),
    )

class _StdLoggerProxy:
    """Allow stdlib logging to accept structured keyword arguments similar to structlog."""

    def __init__(self, base_logger: logging.Logger):
        self._logger = base_logger

    def __getattr__(self, item):
        return getattr(self._logger, item)

    def _emit(self, level: str, event: str, *args, **kwargs):
        extra = kwargs.pop("extra", {})
        standard_kwargs = {}
        for param in ("exc_info", "stack_info", "stacklevel"):
            if param in kwargs:
                standard_kwargs[param] = kwargs.pop(param)
        extra.update(kwargs)
        if extra:
            standard_kwargs["extra"] = extra
        getattr(self._logger, level)(event, *args, **standard_kwargs)

    def error(self, event: str, *args, **kwargs):
        self._emit("error", event, *args, **kwargs)

    def warning(self, event: str, *args, **kwargs):
        self._emit("warning", event, *args, **kwargs)

    def info(self, event: str, *args, **kwargs):
        self._emit("info", event, *args, **kwargs)

    def debug(self, event: str, *args, **kwargs):
        self._emit("debug", event, *args, **kwargs)

    def critical(self, event: str, *args, **kwargs):
        self._emit("critical", event, *args, **kwargs)


logger = (
    structlog.get_logger(__name__)  # type: ignore[attr-defined]
    if _STRUCTLOG_AVAILABLE
    else _StdLoggerProxy(logging.getLogger(__name__))
)


def _clear_context() -> None:
    structlog.contextvars.clear_contextvars()  # type: ignore[attr-defined]


def _bind_context(**kwargs) -> None:
    structlog.contextvars.bind_contextvars(**kwargs)  # type: ignore[attr-defined]


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware that adds a unique request_id to each request.

    The request_id is:
    - Added to request.META as 'HTTP_X_REQUEST_ID'
    - Bound to structlog context for all logs in that request
    - Added as response header 'X-Request-ID' for client tracking

    Usage:
        Add to MIDDLEWARE in settings:
        MIDDLEWARE = [
            ...
            'core.middleware.request_id.RequestIDMiddleware',
            ...
        ]

        In views/services:
        import structlog
        logger = structlog.get_logger(__name__)

        logger.info("processing_order", order_id=123)
        # Automatically includes request_id in log output
    """

    def process_request(self, request):
        """Generate or extract request ID before view processing."""
        # Check if client sent X-Request-ID header (for tracing)
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        if not request_id:
            # Generate new UUID
            request_id = str(uuid.uuid4())

        # Store in request
        request.request_id = request_id
        request.META['HTTP_X_REQUEST_ID'] = request_id

        # Bind to structlog context for this request
        _clear_context()
        _bind_context(
            request_id=request_id,
            request_method=request.method,
            request_path=request.path,
            remote_addr=self._get_client_ip(request),
        )

        return None

    def process_response(self, request, response):
        """Add request ID to response headers."""
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id

        # Clear context after request completes
        _clear_context()

        return response

    def process_exception(self, request, exception):
        """Log exceptions with request context."""
        if hasattr(request, 'request_id'):
            logger.error(
                "request_exception",
                exception=str(exception),
                exception_type=type(exception).__name__,
                request_id=request.request_id,
                request_path=request.path,
                request_method=request.method,
            )

        _clear_context()
        return None

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request, considering proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take first IP if multiple (client, proxy1, proxy2, ...)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

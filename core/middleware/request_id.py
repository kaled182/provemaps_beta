"""
Request ID middleware for tracking requests across logs and metrics.

Adds a unique request_id to each HTTP request and makes it available
in structlog context for correlation across distributed logs.
"""
import uuid

import structlog
from django.utils.deprecation import MiddlewareMixin


logger = structlog.get_logger(__name__)


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
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
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
        structlog.contextvars.clear_contextvars()

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

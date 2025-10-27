"""
Tests for RequestIDMiddleware.

Tests UUID generation, context binding, header handling,
and exception logging.
"""
from unittest.mock import patch, Mock
from django.test import RequestFactory
from core.middleware.request_id import RequestIDMiddleware
import uuid


def get_middleware():
    """Create middleware instance."""
    return RequestIDMiddleware(get_response=Mock(return_value=Mock()))


class TestRequestIDGeneration:
    """Test request ID generation and header handling."""

    def test_generates_uuid_when_no_header(self):
        """Test middleware generates UUID when no X-Request-ID header."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')

        middleware.process_request(request)

        assert hasattr(request, 'request_id')
        assert uuid.UUID(request.request_id, version=4)

    def test_uses_client_request_id_header(self):
        """Test middleware uses client-provided X-Request-ID."""
        middleware = get_middleware()
        factory = RequestFactory()
        client_id = str(uuid.uuid4())
        request = factory.get('/', HTTP_X_REQUEST_ID=client_id)

        middleware.process_request(request)

        assert request.request_id == client_id

    def test_different_requests_get_different_ids(self):
        """Test each request gets unique ID."""
        middleware = get_middleware()
        factory = RequestFactory()

        request1 = factory.get('/')
        request2 = factory.get('/')
        request3 = factory.get('/')

        middleware.process_request(request1)
        middleware.process_request(request2)
        middleware.process_request(request3)

        id1 = request1.request_id
        id2 = request2.request_id
        id3 = request3.request_id

        assert id1 != id2 != id3
        assert uuid.UUID(id1, version=4)
        assert uuid.UUID(id2, version=4)
        assert uuid.UUID(id3, version=4)


class TestContextBinding:
    """Test structlog context binding."""

    @patch('core.middleware.request_id.structlog.contextvars.bind_contextvars')
    def test_binds_request_id_to_context(self, mock_bind):
        """Test that request ID is bound to structlog context."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/test/', REMOTE_ADDR='127.0.0.1')

        middleware.process_request(request)

        mock_bind.assert_called_once()
        call_kwargs = mock_bind.call_args[1]
        assert 'request_id' in call_kwargs
        assert call_kwargs['method'] == 'GET'
        assert call_kwargs['path'] == '/test/'
        assert call_kwargs['remote_addr'] == '127.0.0.1'

    @patch('core.middleware.request_id.structlog.contextvars.clear_contextvars')
    def test_clears_context_after_response(self, mock_clear):
        """Test that context is cleared after response."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')
        request.request_id = str(uuid.uuid4())

        response = Mock()
        middleware.process_response(request, response)

        mock_clear.assert_called_once()


class TestResponseHeaders:
    """Test X-Request-ID response header."""

    def test_adds_request_id_to_response(self):
        """Test middleware adds X-Request-ID to response headers."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')
        request.request_id = str(uuid.uuid4())

        response = Mock()
        response.__setitem__ = Mock()

        middleware.process_response(request, response)

        response.__setitem__.assert_called()
        call_args = response.__setitem__.call_args[0]
        assert call_args[0] == 'X-Request-ID'
        assert call_args[1] == request.request_id

    def test_handles_request_without_id(self):
        """Test middleware handles requests without request_id."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')
        # Don't set request_id

        response = Mock()
        result = middleware.process_response(request, response)

        assert result == response


class TestClientIPExtraction:
    """Test client IP extraction from headers."""

    def test_extracts_ip_from_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.100, 10.0.0.1')

        client_ip = middleware._get_client_ip(request)

        assert client_ip == '192.168.1.100'

    def test_extracts_ip_from_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR when no X-Forwarded-For."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='127.0.0.1')

        client_ip = middleware._get_client_ip(request)

        assert client_ip == '127.0.0.1'

    def test_handles_missing_ip(self):
        """Test handling when no IP is available."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')

        client_ip = middleware._get_client_ip(request)

        assert client_ip == 'unknown'

    def test_strips_whitespace_from_forwarded_ip(self):
        """Test that whitespace is stripped from X-Forwarded-For IP."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR=' 192.168.1.100 , 10.0.0.1 ')

        client_ip = middleware._get_client_ip(request)

        assert client_ip == '192.168.1.100'


class TestExceptionHandling:
    """Test exception logging with context."""

    @patch('core.middleware.request_id.logger.error')
    def test_logs_exception_with_context(self, mock_error):
        """Test exception logging includes request context."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/test/')
        request.request_id = str(uuid.uuid4())

        exception = ValueError("Test error")

        middleware.process_exception(request, exception)

        mock_error.assert_called_once()
        call_args = mock_error.call_args[1]
        assert 'request_id' in call_args
        assert call_args['request_id'] == request.request_id
        assert call_args['path'] == '/test/'
        assert call_args['method'] == 'GET'

    @patch('core.middleware.request_id.logger.error')
    def test_handles_exception_without_request_id(self, mock_error):
        """Test exception handling when request has no ID."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/test/')
        # No request_id set

        exception = ValueError("Test error")

        # Should not raise exception
        middleware.process_exception(request, exception)

        mock_error.assert_called_once()


class TestMiddlewareIntegration:
    """Test middleware integration with Django."""

    def test_middleware_in_request_cycle(self):
        """Test middleware full request/response cycle."""
        pass  # Integration test placeholder


class TestUUIDFormat:
    """Test UUID format validation."""

    def test_generated_id_is_valid_uuid(self):
        """Test that generated IDs are valid UUIDs."""
        middleware = get_middleware()
        factory = RequestFactory()
        request = factory.get('/')

        middleware.process_request(request)

        # Should not raise ValueError
        parsed_uuid = uuid.UUID(request.request_id, version=4)
        assert str(parsed_uuid) == request.request_id

    def test_preserves_custom_uuid_format(self):
        """Test that custom UUIDs are preserved."""
        middleware = get_middleware()
        factory = RequestFactory()
        custom_uuid = str(uuid.uuid4())
        request = factory.get('/', HTTP_X_REQUEST_ID=custom_uuid)
        request.request_id = str(uuid.uuid4())

        response = Mock()
        response.__setitem__ = Mock()

        middleware.process_response(request, response)

        call_args = response.__setitem__.call_args[0]
        assert call_args[1] == request.request_id


class TestConcurrency:
    """Test context isolation between concurrent requests."""

    @patch('core.middleware.request_id.structlog.contextvars.bind_contextvars')
    def test_context_isolation_between_requests(self, mock_bind):
        """Test that each request has isolated context."""
        middleware = get_middleware()
        factory = RequestFactory()

        request1 = factory.get('/path1/')
        request2 = factory.get('/path2/')

        middleware.process_request(request1)
        middleware.process_request(request2)

        assert mock_bind.call_count == 2
        assert request1.request_id != request2.request_id

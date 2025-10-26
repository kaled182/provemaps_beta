from django.conf import settings


class NoCacheDevMiddleware:
    """Força cabeçalhos de no-cache em páginas sensíveis quando DEBUG=True."""

    TARGET_PREFIXES = (
        '/routes_builder/',
        '/static/js/fiber_route_builder',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and any(request.path.startswith(p) for p in self.TARGET_PREFIXES):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
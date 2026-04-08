"""
Middleware que desativa CSRF para rotas de API que usam autenticação própria.
Deve ser posicionado ANTES do CsrfViewMiddleware no settings.
"""
from django.http import HttpRequest, HttpResponse
from typing import Callable


_EXEMPT_PREFIXES = (
    '/setup/api/cron',
)


class CsrfApiExemptMiddleware:
    """
    Marca requisições para APIs internas como csrf_processing_done=True,
    impedindo que o CsrfViewMiddleware as processe.
    Usado para endpoints que têm autenticação própria (_cron_auth).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if any(request.path.startswith(p) for p in _EXEMPT_PREFIXES):
            request.csrf_processing_done = True
        return self.get_response(request)

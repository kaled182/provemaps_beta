"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# EV-0025: `core.settings` nunca existiu. Servidores arrancam em produção por
# omissão (fail-safe: `settings.prod` recusa SECRET_KEY de desenvolvimento);
# `manage.py` e o Celery continuam a assumir `settings.dev`. O Docker define a
# variável explicitamente.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.prod")

django_asgi_app = get_asgi_application()

try:
    import core.routing  # noqa: F401
except ModuleNotFoundError:
    websocket_patterns = []
else:
    from core import routing

    websocket_patterns = getattr(routing, "websocket_urlpatterns", [])

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_patterns)),
    }
)

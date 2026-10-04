"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# EV-0025: `core.settings` nunca existiu. Servidores arrancam em produção por
# omissão (fail-safe: `settings.prod` recusa SECRET_KEY de desenvolvimento);
# `manage.py` e o Celery continuam a assumir `settings.dev`. O Docker define a
# variável explicitamente.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.prod")

application = get_wsgi_application()

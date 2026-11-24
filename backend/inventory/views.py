from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from setup_app.services.runtime_settings import get_runtime_config


@login_required
def fiber_route_builder(request: HttpRequest) -> HttpResponse:
    """Projeto de rede: serve sempre o SPA.

    EV-0084: o construtor legado (``inventory/fiber_route_builder.html`` e o JS estático
    ``js/fiber_route_builder.js`` + ``js/modules/``) saiu; respondia só a ``?legacy=1`` e o
    script já nem carregava (importava o alias ``@/`` do Vite fora do build).
    """
    config = get_runtime_config()
    google_maps_key = config.google_maps_api_key or getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    return render(request, "spa.html", {"GOOGLE_MAPS_API_KEY": google_maps_key})

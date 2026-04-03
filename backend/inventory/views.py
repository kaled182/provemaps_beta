from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from inventory.usecases import devices as device_usecases
from setup_app.services.runtime_settings import get_runtime_config


@login_required
def fiber_route_builder(request: HttpRequest) -> HttpResponse:
    config = get_runtime_config()
    google_maps_key = (
        config.google_maps_api_key
        or getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    )

    use_vue = getattr(settings, "USE_VUE_DASHBOARD", False)
    force_legacy = request.GET.get("legacy") == "1"

    if use_vue and not force_legacy:
        return render(
            request,
            "spa.html",
            {
                "GOOGLE_MAPS_API_KEY": google_maps_key,
            },
        )

    device_options = device_usecases.list_device_select_options()

    return render(
        request,
        "inventory/fiber_route_builder.html",
        {
            "maps_api_key": google_maps_key,
            "GOOGLE_MAPS_API_KEY": google_maps_key,
            "page_title": "Network Design",
            "devices": device_options,
        },
    )

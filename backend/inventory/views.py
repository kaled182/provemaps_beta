from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from setup_app.services.runtime_settings import get_runtime_config
from inventory.models import Device


@login_required
def fiber_route_builder(request: HttpRequest) -> HttpResponse:
    config = get_runtime_config()

    devices = (
        Device.objects.select_related("site")
        .order_by("name")
        .all()
    )

    return render(
        request,
        "inventory/fiber_route_builder.html",
        {
            "page_title": "Fiber Route Builder",
            "maps_api_key": config.google_maps_api_key,
            "devices": devices,
        },
    )

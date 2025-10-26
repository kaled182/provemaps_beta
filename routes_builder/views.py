from django.shortcuts import render
from django.conf import settings
from setup_app.services import runtime_settings
from django.contrib.auth.decorators import login_required
from inventory.models import Device

@login_required
def fiber_route_builder_view(request):
    devices = Device.objects.all().select_related('site').order_by('name')
    return render(request, 'fiber_route_builder.html', {
        "GOOGLE_MAPS_API_KEY": runtime_settings.get_runtime_config().google_maps_api_key or getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        "devices": devices,
    })
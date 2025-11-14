"""DRF ViewSets for Inventory API."""

from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from inventory.models import Device, FiberCable, Port, Site

from .serializers import (
    DeviceSerializer,
    FiberCableSerializer,
    PortSerializer,
    SiteSerializer,
)


class SiteViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Site CRUD operations."""

    queryset = (
        Site.objects.annotate(device_count=Count("devices", distinct=True))
        .order_by("display_name")
    )
    serializer_class = SiteSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def devices(self, request, pk=None):
        """Return devices associated with a site."""

        site = self.get_object()
        devices_qs = site.devices.select_related("site").order_by("name")
        serializer = DeviceSerializer(devices_qs, many=True)

        payload = {
            "site_id": site.id,
            "site_name": site.display_name,
            "site_city": site.city,
            "latitude": float(site.latitude)
            if site.latitude is not None
            else None,
            "longitude": float(site.longitude)
            if site.longitude is not None
            else None,
            "device_count": devices_qs.count(),
            "devices": serializer.data,
        }

        return Response(payload)


class DeviceViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Device CRUD operations"""

    queryset = Device.objects.select_related("site").order_by(
        "site__display_name", "name"
    )
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard


class PortViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Port CRUD operations"""

    queryset = Port.objects.select_related("device__site").order_by("name")
    serializer_class = PortSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard


class FiberCableViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for FiberCable CRUD operations"""

    queryset = FiberCable.objects.select_related(
        "origin_port__device__site", "destination_port__device__site"
    ).order_by("name")
    serializer_class = FiberCableSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

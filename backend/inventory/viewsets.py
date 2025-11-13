"""
DRF ViewSets for Inventory API
"""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from inventory.models import Site, Device, Port, FiberCable
from .serializers import (
    SiteSerializer,
    DeviceSerializer,
    PortSerializer,
    FiberCableSerializer,
)


class SiteViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Site CRUD operations"""

    queryset = Site.objects.all().order_by("display_name")
    serializer_class = SiteSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard


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

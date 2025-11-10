"""
REST API URLs for Inventory
Maps /api/v1/ endpoints for DRF ViewSets
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    SiteViewSet,
    DeviceViewSet,
    PortViewSet,
    FiberCableViewSet,
)

router = DefaultRouter()
router.register(r"sites", SiteViewSet, basename="site")
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"ports", PortViewSet, basename="port")
router.register(r"fiber-cables", FiberCableViewSet, basename="fibercable")

urlpatterns = [
    path("", include(router.urls)),
]

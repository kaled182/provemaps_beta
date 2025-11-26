"""
REST API URLs for Inventory
Maps /api/v1/ endpoints for DRF ViewSets
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    SiteViewSet,
    DeviceViewSet,
    DeviceGroupViewSet,
    PortViewSet,
    FiberCableViewSet,
    ImportRuleViewSet,
)

router = DefaultRouter()
router.register(r"sites", SiteViewSet, basename="site")
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"device-groups", DeviceGroupViewSet, basename="devicegroup")
router.register(r"ports", PortViewSet, basename="port")
router.register(r"fiber-cables", FiberCableViewSet, basename="fibercable")
router.register(r"import-rules", ImportRuleViewSet, basename="importrule")

urlpatterns = [
    path("", include(router.urls)),
]

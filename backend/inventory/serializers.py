"""
DRF Serializers for Inventory Models
Exposes Site, Device, Port via REST API for Vue 3 frontend
"""

from rest_framework import serializers
from inventory.models import Site, Device, Port, FiberCable


class SiteSerializer(serializers.ModelSerializer):
    """Site serializer with backward-compatible name field"""

    name = serializers.CharField(
        source="display_name", read_only=False, required=True
    )

    class Meta:
        model = Site
        fields = [
            "id",
            "name",  # Maps to display_name
            "slug",
            "address",
            "city",
            "state",
            "zip_code",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["id", "slug"]


class DeviceSerializer(serializers.ModelSerializer):
    """Device serializer with nested site"""

    site_name = serializers.CharField(
        source="site.display_name", read_only=True
    )

    class Meta:
        model = Device
        fields = [
            "id",
            "site",
            "site_name",
            "name",
            "vendor",
            "model",
            "zabbix_hostid",
        ]
        read_only_fields = ["id"]


class PortSerializer(serializers.ModelSerializer):
    """Port serializer with nested device and site info"""

    device_name = serializers.CharField(source="device.name", read_only=True)
    site_name = serializers.CharField(
        source="device.site.display_name", read_only=True
    )

    class Meta:
        model = Port
        fields = [
            "id",
            "device",
            "device_name",
            "site_name",
            "name",
            "zabbix_item_key",
        ]
        read_only_fields = ["id"]


class FiberCableSerializer(serializers.ModelSerializer):
    """Fiber cable serializer"""

    origin_site_name = serializers.CharField(
        source="origin_port.device.site.display_name", read_only=True
    )
    destination_site_name = serializers.CharField(
        source="destination_port.device.site.display_name",
        read_only=True,
    )

    class Meta:
        model = FiberCable
        fields = [
            "id",
            "name",
            "origin_port",
            "origin_site_name",
            "destination_port",
            "destination_site_name",
            "length_km",
            "status",
            "last_status_update",
        ]
        read_only_fields = ["id"]

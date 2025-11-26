"""
DRF Serializers for Inventory Models
Exposes Site, Device, Port via REST API for Vue 3 frontend
"""

from rest_framework import serializers
from inventory.models import (
    Site,
    Device,
    DeviceGroup,
    Port,
    FiberCable,
    ImportRule,
)


class SiteSerializer(serializers.ModelSerializer[Site]):
    """Site serializer with backward-compatible name field"""

    name = serializers.CharField(
        source="display_name", read_only=False, required=True
    )
    address = serializers.CharField(
        source="address_line1", allow_blank=True, required=False
    )
    address_line2 = serializers.CharField(
        allow_blank=True, required=False
    )
    address_line3 = serializers.CharField(
        allow_blank=True, required=False
    )
    zip_code = serializers.CharField(
        source="postal_code", allow_blank=True, required=False
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Site
        fields = [
            "id",
            "name",  # Maps to display_name
            "slug",
            "address",
            "address_line2",
            "address_line3",
            "city",
            "state",
            "zip_code",
            "latitude",
            "longitude",
            "device_count",
        ]
        read_only_fields = ["id", "slug"]


class DeviceGroupSerializer(serializers.ModelSerializer[DeviceGroup]):
    """DeviceGroup serializer for dropdown lists"""

    class Meta:
        model = DeviceGroup
        fields = ["id", "name"]
        read_only_fields = ["id"]


class DeviceSerializer(serializers.ModelSerializer[Device]):
    """Device serializer with nested site and monitoring group info"""

    site_name = serializers.CharField(
        source="site.display_name", read_only=True
    )
    # Traz o nome do grupo para exibir na lista
    group_name = serializers.CharField(
        source="monitoring_group.name", read_only=True, allow_null=True
    )
    # Alerts como objeto (para compatibilidade com o frontend)
    alerts = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "site",
            "site_name",
            "name",
            "vendor",
            "model",
            "primary_ip",
            "zabbix_hostid",
            "uptime_item_key",
            "cpu_usage_item_key",
            # Device Import System Fields
            "category",
            "monitoring_group",  # ID para gravação
            "group_name",  # Nome para leitura
            "enable_screen_alert",
            "enable_whatsapp_alert",
            "enable_email_alert",
            "alerts",  # Objeto consolidado {screen, whatsapp, email}
        ]
        read_only_fields = [
            "id",
            "site_name",
            "group_name",
            "alerts"
        ]

    def get_alerts(self, obj: Device) -> dict[str, bool]:
        """Retorna alertas como objeto para compatibilidade com frontend"""
        return {
            "screen": obj.enable_screen_alert,
            "whatsapp": obj.enable_whatsapp_alert,
            "email": obj.enable_email_alert,
        }


class PortSerializer(serializers.ModelSerializer[Port]):
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


class FiberCableSerializer(serializers.ModelSerializer[FiberCable]):
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


class ImportRuleSerializer(serializers.ModelSerializer[ImportRule]):
    """Serializer for auto-import rules with regex pattern validation."""

    group_name = serializers.CharField(
        source="group.name", read_only=True, allow_null=True
    )

    class Meta:
        model = ImportRule
        fields = [
            "id",
            "pattern",
            "category",
            "group",
            "group_name",
            "is_active",
            "priority",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "group_name"]

    def validate_pattern(self, value: str) -> str:
        """Validate that pattern is a valid regex."""
        import re

        try:
            re.compile(value, re.IGNORECASE)
        except re.error as e:
            raise serializers.ValidationError(
                f"Invalid regex pattern: {e}"
            )
        return value

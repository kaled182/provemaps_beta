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
    FiberProfile,
    BufferTube,
    FiberStrand,
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
    type = serializers.CharField(
        source="address_line2",
        allow_blank=True,
        required=False,
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
            "type",
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

    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DeviceGroup
        fields = ["id", "name", "device_count"]
        read_only_fields = ["id", "device_count"]


class DeviceSerializer(serializers.ModelSerializer[Device]):
    """Device serializer with nested site and monitoring group info"""

    site_name = serializers.CharField(
        source="site.display_name", read_only=True
    )
    # Alias para o frontend: mapeia category -> role (read-only)
    role = serializers.CharField(source="category", read_only=True)
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
            "role",
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
    device_id = serializers.IntegerField(source="device.id", read_only=True)
    site_name = serializers.CharField(
        source="device.site.display_name", read_only=True
    )
    site_id = serializers.IntegerField(source="device.site.id", read_only=True)

    class Meta:
        model = Port
        fields = [
            "id",
            "device",
            "device_id",
            "device_name",
            "site_id",
            "site_name",
            "name",
            "zabbix_item_key",
            "zabbix_item_id_traffic_in",
            "zabbix_item_id_traffic_out",
            "zabbix_interfaceid",
            "zabbix_itemid",
            "rx_power_item_key",
            "tx_power_item_key",
            "notes",
            "last_rx_power",
            "last_tx_power",
            "last_optical_check",
        ]
        read_only_fields = ["id", "device_id", "site_id"]


class FiberCableSerializer(serializers.ModelSerializer[FiberCable]):
    """Fiber cable serializer with 'Inventory First, Routing Later' support

    Supports two modes:
    1. Floating inventory: cable without sites/ports (cadastro técnico)
    2. Connected: cable with sites and optionally ports (rota lógica)

    Campos extras:
    - site_a_name / site_b_name (logical connection sites)
    - origin_device_id / destination_device_id (physical termination)
    - is_connected / connection_status (computed state)
    """

    # Logical Connection (Sites - may exist without ports)
    site_a_name = serializers.SerializerMethodField()
    site_b_name = serializers.SerializerMethodField()
    
    # Physical Termination (Devices - only when ports defined)
    origin_device_id = serializers.IntegerField(
        source="origin_port.device.id", read_only=True, allow_null=True
    )
    origin_device_name = serializers.CharField(
        source="origin_port.device.name", read_only=True, allow_null=True
    )
    destination_device_id = serializers.IntegerField(
        source="destination_port.device.id", read_only=True, allow_null=True
    )
    destination_device_name = serializers.CharField(
        source="destination_port.device.name", read_only=True, allow_null=True
    )

    # Port names (optional)
    origin_port_name = serializers.CharField(
        source="origin_port.name", read_only=True, allow_null=True
    )
    destination_port_name = serializers.CharField(
        source="destination_port.name", read_only=True, allow_null=True
    )
    
    # Connection state (computed)
    is_connected = serializers.SerializerMethodField()
    connection_status = serializers.SerializerMethodField()

    # Site geolocation for map airline and centering
    site_a_location = serializers.SerializerMethodField()
    site_b_location = serializers.SerializerMethodField()
    infrastructure_points = serializers.SerializerMethodField()
    
    def get_site_a_name(self, obj: FiberCable) -> str | None:
        """Get site A name from site_a or origin_port.device.site"""
        if obj.site_a:
            return obj.site_a.display_name
        if (
            obj.origin_port
            and obj.origin_port.device
            and obj.origin_port.device.site
        ):
            return obj.origin_port.device.site.display_name
        return None
    
    def get_site_b_name(self, obj: FiberCable) -> str | None:
        """Get site B name from site_b or destination_port.device.site"""
        if obj.site_b:
            return obj.site_b.display_name
        if (
            obj.destination_port
            and obj.destination_port.device
            and obj.destination_port.device.site
        ):
            return obj.destination_port.device.site.display_name
        return None
    
    def get_is_connected(self, obj: FiberCable) -> bool:
        """Check if cable has logical connection (sites/ports defined)"""
        return bool(
            obj.site_a
            or obj.site_b
            or obj.origin_port
            or obj.destination_port
        )
    
    def get_connection_status(self, obj: FiberCable) -> str:
        """Return connection status: floating, logical, physical"""
        has_ports = bool(obj.origin_port and obj.destination_port)
        has_sites = bool(obj.site_a or obj.site_b)
        
        if has_ports:
            return "physical"  # Physically terminated on ports
        if has_sites:
            return "logical"   # Logically connected between sites
        return "floating"      # Inventory only, not connected

    def get_site_a_location(self, obj: FiberCable) -> dict[str, float] | None:
        """Return lat/lng dict for Site A when available."""
        site = getattr(obj, "site_a", None)
        if site and site.latitude is not None and site.longitude is not None:
            try:
                return {
                    "lat": float(site.latitude),
                    "lng": float(site.longitude),
                }
            except Exception:
                return None
        # Fallback: origin port device site
        dev_site = getattr(
            getattr(getattr(obj, "origin_port", None), "device", None),
            "site",
            None,
        )
        if (
            dev_site
            and dev_site.latitude is not None
            and dev_site.longitude is not None
        ):
            try:
                return {
                    "lat": float(dev_site.latitude),
                    "lng": float(dev_site.longitude),
                }
            except Exception:
                return None
        return None

    def get_site_b_location(self, obj: FiberCable) -> dict[str, float] | None:
        """Return lat/lng dict for Site B when available."""
        site = getattr(obj, "site_b", None)
        if site and site.latitude is not None and site.longitude is not None:
            try:
                return {
                    "lat": float(site.latitude),
                    "lng": float(site.longitude),
                }
            except Exception:
                return None
        # Fallback: destination port device site
        dev_site = getattr(
            getattr(getattr(obj, "destination_port", None), "device", None),
            "site",
            None,
        )
        if (
            dev_site
            and dev_site.latitude is not None
            and dev_site.longitude is not None
        ):
            try:
                return {
                    "lat": float(dev_site.latitude),
                    "lng": float(dev_site.longitude),
                }
            except Exception:
                return None
        return None

    def get_infrastructure_points(self, obj: FiberCable) -> list[dict]:
        """Return infra points without importing models to avoid cycles."""
        points_qs = getattr(obj, "infrastructure_points", None)
        if not points_qs:
            return []
        result = []
        for p in points_qs.all():
            loc = None
            try:
                loc = {
                    "type": "Point",
                    "coordinates": [p.location.x, p.location.y],
                }
            except Exception:
                loc = None
            type_label = getattr(p, "get_type_display", lambda: None)()
            result.append({
                "id": p.id,
                "type": p.type,
                "type_display": type_label,
                "name": p.name,
                "location": loc,
                "distance_from_origin": p.distance_from_origin,
                "metadata": p.metadata,
                "created_at": p.created_at,
            })
        return result

    class Meta:
        model = FiberCable
        fields = [
            "id",
            "name",
            "profile",
            # Logical Connection (Sites)
            "site_a",
            "site_a_name",
            "site_a_location",
            "site_b",
            "site_b_name",
            "site_b_location",
            # Physical Termination (Ports)
            "origin_port",
            "origin_port_name",
            "destination_port",
            "destination_port_name",
            # Device info
            "origin_device_id",
            "origin_device_name",
            "destination_device_id",
            "destination_device_name",
            # Connection state
            "is_connected",
            "connection_status",
            # Geometry/Path
            "path_coordinates",
            # Infraestrutura
            "infrastructure_points",
            # Metadata
            "length_km",
            "status",
            "last_status_update",
        ]
        read_only_fields = [
            "id",
            "site_a_name",
            "site_b_name",
            "site_a_location",
            "site_b_location",
            "origin_port_name",
            "destination_port_name",
            "origin_device_id",
            "origin_device_name",
            "destination_device_id",
            "destination_device_name",
            "is_connected",
            "connection_status",
        ]


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


# --- FIBER PHYSICAL HIERARCHY SERIALIZERS (Phase 11.5) ---


class FiberProfileSerializer(serializers.ModelSerializer):
    """Fiber profile (factory template) for cable construction"""

    class Meta:
        model = FiberProfile
        fields = [
            "id",
            "name",
            "total_fibers",
            "tube_count",
            "fibers_per_tube",
            "manufacturer",
        ]


class FiberStrandSerializer(serializers.ModelSerializer):
    """Individual fiber strand within a buffer tube"""

    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = FiberStrand
        fields = [
            "id",
            "number",
            "absolute_number",
            "color",
            "color_hex",
            "status",
            "status_display",
            "connected_device_port",
            "fused_to",
            "attenuation_db",
            "last_test_date",
            "full_address",
        ]

    def get_full_address(self, obj):
        """Return structured address (Cabo/Tubo/Fibra notation)"""
        return obj.full_address


class BufferTubeSerializer(serializers.ModelSerializer):
    """Buffer tube (loose tube) containing fiber strands"""

    strands = FiberStrandSerializer(many=True, read_only=True)

    class Meta:
        model = BufferTube
        fields = [
            "id",
            "number",
            "color",
            "color_hex",
            "strands",
        ]


class FiberCableStructureSerializer(serializers.ModelSerializer):
    """
    Heavy serializer for detailed cable structure visualization (X-ray view).
    Use only for detail endpoints, not for list views.
    Returns nested hierarchy: Cable -> Tubes -> Strands
    """

    tubes = BufferTubeSerializer(many=True, read_only=True)
    profile_name = serializers.CharField(
        source="profile.name", read_only=True, allow_null=True
    )
    profile_id = serializers.IntegerField(
        source="profile.id", read_only=True, allow_null=True
    )

    class Meta:
        model = FiberCable
        fields = [
            "id",
            "name",
            "origin_port",
            "destination_port",
            "length_km",
            "status",
            "profile_id",
            "profile_name",
            "tubes",
        ]



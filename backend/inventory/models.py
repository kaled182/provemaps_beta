"""
Inventory models for network infrastructure management.

These models were migrated from zabbix_api app but preserve the original
database table names using Meta.db_table to avoid data migration issues.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Site(models.Model):
    """Physical location/site containing network devices."""

    display_name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=160, unique=True, editable=False)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    address_line3 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=160, blank=True)
    state = models.CharField(max_length=160, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    country = models.CharField(max_length=160, blank=True)
    rack_location = models.CharField(max_length=160, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["display_name"]
        db_table = "zabbix_api_site"  # Preserve original table name

    def __str__(self) -> str:
        return self.display_name

    @property
    def name(self) -> str:
        """Backward compatible alias for the previous field name."""

        return self.display_name

    @name.setter
    def name(self, value: str) -> None:
        self.display_name = value

    @staticmethod
    def _build_base_slug(source: str | None) -> str:
        base = slugify(source or "")
        if base:
            return base[:120]
        return "site"

    def _ensure_slug(self) -> None:
        if self.slug and slugify(self.slug) == self.slug:
            return

        base_slug = self._build_base_slug(self.display_name or self.city)
        candidate = base_slug
        suffix = 2
        while Site.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
            suffix_str = f"-{suffix}"
            candidate = f"{base_slug[:120 - len(suffix_str)]}{suffix_str}"
            suffix += 1
        self.slug = candidate

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.display_name:
            # Fall back to a human friendly version of the slug
            fallback = self.city or self.address_line1 or self.slug or "Site"
            self.display_name = fallback
        self._ensure_slug()
        super().save(*args, **kwargs)


class Device(models.Model):
    """
    Network device (router, switch, OLT, etc.) at a site.
    Original table: zabbix_api_device
    """
    site = models.ForeignKey(
        Site,
        related_name="devices",
        on_delete=models.CASCADE,
    )
    device_icon = models.ImageField(
        upload_to="img/device_icons/",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    vendor = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    zabbix_hostid = models.CharField(
        max_length=32,
        blank=True,
        help_text="hostid inside Zabbix",
    )
    uptime_item_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Zabbix item key for uptime (e.g. system.uptime)",
    )
    cpu_usage_item_key = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Zabbix item key for CPU usage "
            "(e.g. system.cpu.util[,user])"
        ),
    )

    class Meta:
        unique_together = ("site", "name")
        ordering = ["site__display_name", "name"]
        db_table = "zabbix_api_device"  # Preserve original table name

    def __str__(self) -> str:
        site_label = self.site.display_name if self.site_id else None
        return f"{site_label} - {self.name}" if site_label else self.name

    if TYPE_CHECKING:
        site_id: int | None


class Port(models.Model):
    """
    Network port/interface on a device.
    Original table: zabbix_api_port
    """
    device = models.ForeignKey(
        Device,
        related_name="ports",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=64)
    zabbix_item_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Zabbix interface item key (e.g. net.if.in[ether10])",
    )
    # Traffic monitoring item IDs (db_column maintains DB compatibility)
    zabbix_item_id_traffic_in = models.CharField(
        max_length=32,
        blank=True,
        db_column="zabbix_item_id_trafego_in",
        help_text="Zabbix itemid for ingress traffic",
    )
    zabbix_item_id_traffic_out = models.CharField(
        max_length=32,
        blank=True,
        db_column="zabbix_item_id_trafego_out",
        help_text="Zabbix itemid for egress traffic",
    )
    zabbix_interfaceid = models.CharField(
        max_length=32, blank=True, help_text="interfaceid inside Zabbix"
    )
    zabbix_itemid = models.CharField(
        max_length=32, blank=True, help_text="Generic itemid inside Zabbix"
    )
    # Optional optical power items (RX/TX) when ifOperStatus is missing
    rx_power_item_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optical RX power (e.g. hwEntityOpticalLaneRxPower[ID])",
    )
    tx_power_item_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optical TX power (e.g. hwEntityOpticalLaneTxPower[ID])",
    )
    notes = models.CharField(max_length=255, blank=True)

    # Cached optical power values populated asynchronously by Celery
    # These fields allow REST APIs to serve data instantly without
    # performing synchronous Zabbix calls during the web request.
    last_rx_power = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Último valor RX dBm coletado do Zabbix (cache assíncrono)",
    )
    last_tx_power = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Último valor TX dBm coletado do Zabbix (cache assíncrono)",
    )
    last_optical_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp da última coleta óptica assíncrona",
    )

    class Meta:
        unique_together = ("device", "name")
        ordering = ["device__site__display_name", "device__name", "name"]
        db_table = "zabbix_api_port"  # Preserve original table name

    def __str__(self) -> str:
        return f"{self.device}::{self.name}"


class FiberCable(models.Model):
    """
    Fiber optic cable connecting two ports.
    Original table: zabbix_api_fibercable
    """
    STATUS_UP = "up"
    STATUS_DOWN = "down"
    STATUS_DEGRADED = "degraded"
    STATUS_UNKNOWN = "unknown"
    STATUS_CHOICES = [
        (STATUS_UP, "Operational"),
        (STATUS_DOWN, "Unavailable"),
        (STATUS_DEGRADED, "Degraded"),
        (STATUS_UNKNOWN, "Unknown"),
    ]

    name = models.CharField(max_length=150, unique=True)
    origin_port = models.ForeignKey(
        Port,
        related_name="fiber_origin",
        on_delete=models.PROTECT,
    )
    destination_port = models.ForeignKey(
        Port,
        related_name="fiber_destination",
        on_delete=models.PROTECT,
    )
    length_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # Intermediate coordinates when plotting (may include origin/destination)
    path_coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text="Coordinate list e.g. [{'lat': -16.6, 'lng': -49.2}, ...]. Deprecated: use path field.",
    )
    # Spatial field for PostGIS (Phase 10)
    # SRID 4326 = WGS84 (GPS coordinates)
    # Populated by data migration from path_coordinates
    path = gis_models.LineStringField(
        srid=4326,
        blank=True,
        null=True,
        help_text="Spatial path geometry for PostGIS spatial queries (bbox filtering).",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
    )
    last_status_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Cached operational status values (Phase 9.1)
    # Populated asynchronously by refresh_cables_oper_status Celery task
    last_status_origin = models.CharField(
        max_length=20,
        blank=True,
        help_text="Último status operacional da porta de origem (cache)",
    )
    last_status_dest = models.CharField(
        max_length=20,
        blank=True,
        help_text="Último status operacional da porta de destino (cache)",
    )
    last_status_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp da última verificação de status operacional",
    )

    # Cached live status (computed from multiple sources)
    last_live_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="Último status 'live' calculado (agregação de fontes)",
    )
    last_live_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp do último cálculo de status live",
    )

    class Meta:
        ordering = ["name"]
        db_table = "zabbix_api_fibercable"  # Preserve original table name

    def __str__(self) -> str:
        return self.name

    def update_status(self, new_status: str) -> None:
        """Update fiber status with timestamp."""
        if new_status not in dict(self.STATUS_CHOICES):
            new_status = self.STATUS_UNKNOWN
        self.status = new_status
        self.last_status_update = timezone.now()
        self.save(update_fields=["status", "last_status_update"])


class FiberEvent(models.Model):
    """
    Event log for fiber status changes.
    Original table: zabbix_api_fiberevent
    """
    fiber = models.ForeignKey(
        FiberCable,
        related_name="events",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(default=timezone.now)
    previous_status = models.CharField(max_length=15, blank=True)
    new_status = models.CharField(max_length=15)
    detected_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        db_table = "zabbix_api_fiberevent"  # Preserve original table name

    def __str__(self) -> str:
        return (
            f"{self.fiber.name} {self.previous_status}->{self.new_status} "
            f"@ {self.timestamp:%Y-%m-%d %H:%M:%S}"
        )


# Route models now live in inventory.models_routes. Import them dynamically to
# expose the public API while avoiding circular imports during Django startup.
if TYPE_CHECKING:
    from .models_routes import Route as RouteModel
    from .models_routes import RouteEvent as RouteEventModel
    from .models_routes import RouteSegment as RouteSegmentModel
else:  # pragma: no cover - runtime only typing fallbacks
    RouteModel = RouteEventModel = RouteSegmentModel = Any

_routes = import_module("inventory.models_routes")

Route = cast("type[RouteModel]", getattr(_routes, "Route"))
RouteEvent = cast("type[RouteEventModel]", getattr(_routes, "RouteEvent"))
RouteSegment = cast(
    "type[RouteSegmentModel]",
    getattr(_routes, "RouteSegment"),
)

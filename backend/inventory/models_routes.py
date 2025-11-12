"""Route-related database models now hosted in the inventory app."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models

try:  # pragma: no cover - environment dependent import
    from django.contrib.gis.db import models as gis_models
except (ImportError, ImproperlyConfigured):
    from django.db import models as _fallback_models

    class _FallbackLineStringField(_fallback_models.JSONField):
        description = "Fallback LineString storage when GDAL is unavailable"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.pop("srid", None)
            kwargs.setdefault("null", True)
            kwargs.setdefault("blank", True)
            super().__init__(*args, **kwargs)

    class _FallbackGISModule:
        LineStringField = _FallbackLineStringField

    gis_models = _FallbackGISModule()  # type: ignore[assignment]


class Route(models.Model):
    """Optical route built between two inventory ports."""

    STATUS_PLANNED = "planned"
    STATUS_ACTIVE = "active"
    STATUS_DEGRADED = "degraded"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DEGRADED, "Degraded"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    origin_port = models.ForeignKey(
        "inventory.Port",
        on_delete=models.PROTECT,
        related_name="routes_origin",
    )
    destination_port = models.ForeignKey(
        "inventory.Port",
        on_delete=models.PROTECT,
        related_name="routes_destination",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
    )
    length_km = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Total cable length in kilometers.",
    )
    estimated_loss_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected optical loss in decibels.",
    )
    measured_loss_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Latest measured optical loss in decibels.",
    )
    last_built_at = models.DateTimeField(null=True, blank=True)
    last_built_by = models.CharField(max_length=150, blank=True)
    import_source = models.CharField(
        max_length=150,
        blank=True,
        help_text="Origin of the data import (KML file, planner, etc).",
    )
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "inventory_route"

    if TYPE_CHECKING:
        origin_port_id: int
        destination_port_id: int

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """Validate logical constraints before persisting."""

        super().clean()
        if (
            self.origin_port_id
            and self.destination_port_id
            and self.origin_port_id == self.destination_port_id
        ):
            raise ValidationError(
                {
                    "destination_port": (
                        "Destination port must differ from origin port."
                    )
                }
            )

    def update_status(self, status: str, *, save: bool = True) -> None:
        """Update route status ensuring a valid value is stored."""

        valid_status = dict(self.STATUS_CHOICES)
        self.status = (
            status if status in valid_status else self.STATUS_DEGRADED
        )
        if save:
            self.save(update_fields=["status", "updated_at"])


class RouteSegment(models.Model):
    """Segment of an optical route, optionally referencing inventory ports."""

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="segments",
    )
    order = models.PositiveIntegerField(
        help_text="Segment order within the route.",
    )
    from_port = models.ForeignKey(
        "inventory.Port",
        on_delete=models.PROTECT,
        related_name="segments_from",
        null=True,
        blank=True,
    )
    to_port = models.ForeignKey(
        "inventory.Port",
        on_delete=models.PROTECT,
        related_name="segments_to",
        null=True,
        blank=True,
    )
    path_coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text='Array of {"lat": float, "lng": float} points. Deprecated: use path field with PostGIS.',
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
    length_km = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
    )
    estimated_loss_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    measured_loss_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["route", "order"]
        unique_together = ("route", "order")
        db_table = "inventory_routesegment"

    if TYPE_CHECKING:
        from_port_id: int | None
        to_port_id: int | None

    def __str__(self) -> str:
        return f"{self.route.name}#{self.order}"

    def clean(self) -> None:
        """Ensure segment endpoints are consistent."""

        super().clean()
        if (
            self.from_port_id
            and self.to_port_id
            and self.from_port_id == self.to_port_id
        ):
            raise ValidationError(
                {
                    "to_port": (
                        "Segment cannot originate and terminate "
                        "on the same port."
                    )
                }
            )


class RouteEvent(models.Model):
    """Audit log for operations executed on a Route."""

    EVENT_BUILD = "build"
    EVENT_STATUS = "status"
    EVENT_IMPORT = "import"
    EVENT_MEASUREMENT = "measurement"
    EVENT_CHOICES = [
        (EVENT_BUILD, "Build"),
        (EVENT_STATUS, "Status change"),
        (EVENT_IMPORT, "Import"),
        (EVENT_MEASUREMENT, "Measurement"),
    ]

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )
    message = models.TextField(blank=True)
    details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(
        max_length=150,
        blank=True,
        help_text="Originator of the event (user, task, import).",
    )

    class Meta:
        ordering = ["-created_at"]
        db_table = "inventory_routeevent"

    def __str__(self) -> str:
        return f"{self.route.name} - {self.event_type}"


if TYPE_CHECKING:
    from django.db.models.manager import Manager

    RouteSegmentManager = Manager[RouteSegment]
    RouteEventManager = Manager[RouteEvent]

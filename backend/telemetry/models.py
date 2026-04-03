from __future__ import annotations

from django.db import models


class Installation(models.Model):
    """
    Represents a unique ProVemaps installation that sent at least one ping.
    One record per installation — updated on every subsequent ping.
    """

    # Stable anonymous ID generated on first run (UUID stored in data/installation.id)
    installation_id = models.UUIDField(unique=True, db_index=True)

    # Version of ProVemaps at time of last ping
    version = models.CharField(max_length=32)

    # OS platform (Linux, Windows, Darwin…)
    os_platform = models.CharField(max_length=64, blank=True, default="")

    # Number of pings received from this installation
    ping_count = models.PositiveIntegerField(default=1)

    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "telemetry"
        ordering = ["-last_seen"]
        verbose_name = "Instalação"
        verbose_name_plural = "Instalações"

    def __str__(self) -> str:
        return f"{self.installation_id} — v{self.version} ({self.last_seen:%Y-%m-%d})"

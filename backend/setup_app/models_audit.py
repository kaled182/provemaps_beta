"""Audit log model for configuration changes tracking."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class ConfigurationAudit(models.Model):
    """Track configuration changes for compliance and debugging."""

    ACTION_CHOICES = [
        ("create", "Created"),
        ("update", "Updated"),
        ("delete", "Deleted"),
        ("export", "Exported"),
        ("import", "Imported"),
        ("test", "Connection Tested"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="config_audits",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    section = models.CharField(
        max_length=100,
        help_text="Configuration section (e.g., 'Zabbix', 'Database', 'Redis')",
    )
    field_name = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True, help_text="Previous value (sanitized)")
    new_value = models.TextField(blank=True, help_text="New value (sanitized)")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp", "user"]),
            models.Index(fields=["section", "-timestamp"]),
        ]

    def __str__(self) -> str:
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.action} {self.section} at {self.timestamp}"

    @classmethod
    def log_change(
        cls,
        user,
        action: str,
        section: str,
        field_name: str = "",
        old_value: str = "",
        new_value: str = "",
        request=None,
        success: bool = True,
        error_message: str = "",
    ) -> ConfigurationAudit:
        """Create an audit log entry."""
        ip_address = None
        user_agent = ""

        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        # Sanitize sensitive data
        if field_name.lower() in ["password", "api_key", "secret_key"]:
            old_value = "***REDACTED***" if old_value else ""
            new_value = "***REDACTED***" if new_value else ""

        return cls.objects.create(
            user=user,
            action=action,
            section=section,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )

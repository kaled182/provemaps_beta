from django.db import models

from .fields import EncryptedCharField
from .models_audit import ConfigurationAudit  # Import audit model


class FirstTimeSetup(models.Model):
    company_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="setup_app/logos/", null=True, blank=True)
    zabbix_url = models.CharField(max_length=255)
    auth_type = models.CharField(
        max_length=10,
        choices=[
            ("token", "Zabbix API token"),
            ("login", "Zabbix user and password"),
        ],
    )
    zabbix_api_key = EncryptedCharField(max_length=512, blank=True, null=True)
    zabbix_user = EncryptedCharField(max_length=512, blank=True, null=True)
    zabbix_password = EncryptedCharField(max_length=512, blank=True, null=True)
    maps_api_key = EncryptedCharField(max_length=512, blank=True, null=True)
    map_provider = models.CharField(
        max_length=20,
        choices=[
            ("google", "Google Maps"),
            ("mapbox", "Mapbox"),
            ("osm", "OpenStreetMap"),
        ],
        default="google",
    )
    mapbox_token = EncryptedCharField(max_length=512, blank=True, null=True)
    unique_licence = EncryptedCharField(max_length=512, blank=True, null=True)
    db_host = EncryptedCharField(max_length=512, blank=True, null=True)
    db_port = EncryptedCharField(max_length=64, blank=True, null=True)
    db_name = EncryptedCharField(max_length=512, blank=True, null=True)
    db_user = EncryptedCharField(max_length=512, blank=True, null=True)
    db_password = EncryptedCharField(max_length=512, blank=True, null=True)
    redis_url = EncryptedCharField(max_length=512, blank=True, null=True)
    configured = models.BooleanField(default=False)
    configured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.company_name


class MonitoringServer(models.Model):
    SERVER_TYPES = [
        ("zabbix", "Zabbix"),
        ("snmp", "SNMP"),
        ("prometheus", "Prometheus"),
        ("librenms", "LibreNMS"),
    ]

    name = models.CharField(max_length=100)
    server_type = models.CharField(max_length=20, choices=SERVER_TYPES, default="zabbix")
    url = models.CharField(max_length=255)
    auth_token = EncryptedCharField(max_length=512, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    extra_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.server_type})"

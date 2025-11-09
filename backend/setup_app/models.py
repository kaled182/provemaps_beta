from django.db import models

from .fields import EncryptedCharField


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

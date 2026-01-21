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
    ftp_enabled = models.BooleanField(default=False)
    ftp_host = EncryptedCharField(max_length=255, blank=True, null=True)
    ftp_port = models.IntegerField(default=21)
    ftp_user = EncryptedCharField(max_length=255, blank=True, null=True)
    ftp_password = EncryptedCharField(max_length=255, blank=True, null=True)
    ftp_path = EncryptedCharField(max_length=255, blank=True, null=True)
    gdrive_enabled = models.BooleanField(default=False)
    gdrive_credentials_json = EncryptedCharField(
        max_length=4096, max_plain_length=4096, blank=True, null=True
    )
    gdrive_folder_id = EncryptedCharField(max_length=255, blank=True, null=True)
    gdrive_shared_drive_id = EncryptedCharField(max_length=255, blank=True, null=True)
    gdrive_auth_mode = models.CharField(
        max_length=32,
        default="service_account",
        choices=[
            ("service_account", "Service Account"),
            ("oauth", "OAuth (Conta pessoal)"),
        ],
    )
    gdrive_oauth_client_id = EncryptedCharField(max_length=255, blank=True, null=True)
    gdrive_oauth_client_secret = EncryptedCharField(max_length=255, blank=True, null=True)
    gdrive_oauth_refresh_token = EncryptedCharField(max_length=512, blank=True, null=True)
    gdrive_oauth_user_email = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_enabled = models.BooleanField(default=False)
    smtp_host = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_port = EncryptedCharField(max_length=32, blank=True, null=True)
    smtp_security = EncryptedCharField(max_length=16, blank=True, null=True)
    smtp_user = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_password = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_auth_mode = EncryptedCharField(max_length=32, blank=True, null=True)
    smtp_oauth_client_id = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_oauth_client_secret = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_oauth_refresh_token = EncryptedCharField(max_length=512, blank=True, null=True)
    smtp_from_name = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_from_email = EncryptedCharField(max_length=255, blank=True, null=True)
    smtp_test_recipient = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(
        max_length=32,
        default="smsnet",
        choices=[
            ("smsnet", "SMSNET"),
            ("zenvia", "Zenvia"),
            ("totalvoice", "TotalVoice"),
            ("aws_sns", "AWS SNS"),
            ("infobip", "Infobip"),
        ],
    )
    sms_provider_rank = models.IntegerField(default=1)
    sms_username = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_password = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_api_token = EncryptedCharField(max_length=512, blank=True, null=True)
    sms_api_url = EncryptedCharField(max_length=512, blank=True, null=True)
    sms_sender_id = EncryptedCharField(max_length=64, blank=True, null=True)
    sms_test_recipient = EncryptedCharField(max_length=64, blank=True, null=True)
    sms_test_message = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_priority = EncryptedCharField(max_length=16, blank=True, null=True)
    sms_aws_region = EncryptedCharField(max_length=64, blank=True, null=True)
    sms_aws_access_key_id = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_aws_secret_access_key = EncryptedCharField(max_length=255, blank=True, null=True)
    sms_infobip_base_url = EncryptedCharField(max_length=255, blank=True, null=True)
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


class MessagingGateway(models.Model):
    GATEWAY_TYPES = [
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("telegram", "Telegram"),
        ("smtp", "SMTP"),
        ("video", "Videovigilância"),
    ]

    name = models.CharField(max_length=120)
    gateway_type = models.CharField(max_length=16, choices=GATEWAY_TYPES)
    provider = models.CharField(max_length=64, blank=True, null=True)
    priority = models.IntegerField(default=1)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.gateway_type})"


class CompanyProfile(models.Model):
    company_legal_name = models.CharField(max_length=255, blank=True)
    company_trade_name = models.CharField(max_length=255, blank=True)
    company_doc = models.CharField(max_length=32, blank=True)
    company_owner_name = models.CharField(max_length=255, blank=True)
    company_owner_doc = models.CharField(max_length=32, blank=True)
    company_owner_birth = models.CharField(max_length=32, blank=True)
    company_state_reg = models.CharField(max_length=64, blank=True)
    company_city_reg = models.CharField(max_length=64, blank=True)
    company_fistel = models.CharField(max_length=64, blank=True)
    company_created_date = models.CharField(max_length=32, blank=True)
    company_active = models.BooleanField(default=True)
    company_reports_active = models.BooleanField(default=True)

    address_zip = models.CharField(max_length=16, blank=True)
    address_street = models.CharField(max_length=255, blank=True)
    address_number = models.CharField(max_length=32, blank=True)
    address_district = models.CharField(max_length=128, blank=True)
    address_city = models.CharField(max_length=128, blank=True)
    address_state = models.CharField(max_length=8, blank=True)
    address_country = models.CharField(max_length=64, blank=True, default="Brasil")
    address_extra = models.CharField(max_length=255, blank=True)
    address_reference = models.CharField(max_length=255, blank=True)
    address_coords = models.CharField(max_length=64, blank=True)
    address_complex = models.CharField(max_length=128, blank=True)
    address_ibge = models.CharField(max_length=32, blank=True)

    assets_logo = models.FileField(upload_to="setup_app/company/logo/", blank=True, null=True)
    assets_cert_file = models.FileField(upload_to="setup_app/company/cert/", blank=True, null=True)
    assets_cert_password = EncryptedCharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.company_trade_name or self.company_legal_name or "Company Profile"


class VideoMosaic(models.Model):
    """
    Modelo para armazenar configurações de mosaicos de câmeras.
    Permite agrupar múltiplas câmeras em layouts de grade (2x2, 3x2, etc).
    """
    LAYOUT_CHOICES = [
        ("2x2", "2×2 (4 câmeras)"),
        ("3x2", "3×2 (6 câmeras)"),
        ("3x3", "3×3 (9 câmeras)"),
        ("4x3", "4×3 (12 câmeras)"),
        ("4x4", "4×4 (16 câmeras)"),
    ]

    name = models.CharField(max_length=120, help_text="Nome do mosaico")
    layout = models.CharField(
        max_length=8,
        choices=LAYOUT_CHOICES,
        default="2x2",
        help_text="Layout da grade de vídeos"
    )
    cameras = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de IDs dos gateways de vídeo (MessagingGateway)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Mosaico de Vídeo"
        verbose_name_plural = "Mosaicos de Vídeo"

    def __str__(self) -> str:
        return f"{self.name} ({self.layout})"

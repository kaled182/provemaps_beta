from django.db import models
from django.contrib.auth import get_user_model
from typing import Dict, List, Optional

from .fields import EncryptedCharField
from .models_audit import ConfigurationAudit  # Import audit model
from .models_contacts import Contact, ContactGroup, ImportHistory  # Import contact models


User = get_user_model()


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
    # Map configuration - Google Maps
    map_default_zoom = models.IntegerField(default=12)
    map_default_lat = models.DecimalField(max_digits=10, decimal_places=7, default=-15.7801)
    map_default_lng = models.DecimalField(max_digits=10, decimal_places=7, default=-47.9292)
    map_type = models.CharField(max_length=20, default='terrain')  # terrain é mais claro e sem grid
    map_styles = models.TextField(blank=True, null=True)
    enable_street_view = models.BooleanField(default=True)
    enable_traffic = models.BooleanField(default=False)
    # Map configuration - Mapbox
    mapbox_style = models.CharField(max_length=255, default='mapbox://styles/mapbox/streets-v12')
    mapbox_custom_style = models.CharField(max_length=255, blank=True, null=True)
    mapbox_enable_3d = models.BooleanField(default=False)
    # Map configuration - Esri
    esri_api_key = EncryptedCharField(max_length=512, blank=True, null=True)
    esri_basemap = models.CharField(max_length=50, default='streets')
    # Map configuration - Common
    map_language = models.CharField(max_length=10, default='pt-BR')
    map_theme = models.CharField(
        max_length=10,
        default='light',
        choices=[
            ('light', 'Claro'),
            ('dark', 'Escuro'),
            ('auto', 'Automático')
        ]
    )
    enable_map_clustering = models.BooleanField(default=True)
    enable_drawing_tools = models.BooleanField(default=True)
    enable_fullscreen = models.BooleanField(default=True)
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
    site_name = models.CharField(max_length=255, blank=True, null=True, help_text="Nome do site onde o dispositivo está localizado (apenas para gateways de vídeo)")
    config = models.JSONField(default=dict, blank=True)
    departments = models.ManyToManyField(
        'core.Department',
        related_name='video_cameras',
        blank=True,
        help_text="Departamentos com permissão para visualizar esta câmera. Deixe vazio para acesso público (todos departamentos)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.gateway_type})"


class AlertTemplate(models.Model):
    """Modelos de mensagens para alertas automáticos."""

    CATEGORY_GENERIC = 'generic'
    CATEGORY_OPTICAL_LEVEL = 'optical_level'
    CATEGORY_DEVICE_AVAILABILITY = 'device_availability'
    CATEGORY_INTERFACE_SIGNAL = 'interface_signal'

    CATEGORY_CHOICES = [
        (CATEGORY_GENERIC, 'Genérico'),
        (CATEGORY_OPTICAL_LEVEL, 'Nível óptico'),
        (CATEGORY_INTERFACE_SIGNAL, 'Sinal de interface'),
        (CATEGORY_DEVICE_AVAILABILITY, 'Disponibilidade de equipamento'),
    ]

    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_TELEGRAM = 'telegram'
    CHANNEL_EMAIL = 'smtp'
    CHANNEL_CHOICES = [
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_TELEGRAM, 'Telegram'),
        (CHANNEL_EMAIL, 'E-mail (SMTP)'),
    ]

    BASE_PLACEHOLDERS = [
        {
            'key': 'contact_name',
            'label': 'Nome do contato',
            'description': 'Nome completo do destinatário.',
        },
        {
            'key': 'contact_phone',
            'label': 'Telefone do contato',
            'description': 'Telefone no formato internacional.',
        },
    ]

    CATEGORY_PLACEHOLDERS = {
        CATEGORY_GENERIC: [
            {
                'key': 'site_name',
                'label': 'Site',
                'description': 'Nome do site ou localização monitorada.',
            },
            {
                'key': 'device_name',
                'label': 'Equipamento',
                'description': 'Dispositivo principal relacionado ao alerta.',
            },
            {
                'key': 'incident_time',
                'label': 'Horário do incidente',
                'description': 'Timestamp do evento no fuso horário local.',
            },
        ],
        CATEGORY_OPTICAL_LEVEL: [
            {
                'key': 'incident_time',
                'label': 'Horário do incidente',
                'description': 'Timestamp em formato local (ex: 31/01/2026 14:35).',
            },
            {
                'key': 'site_name',
                'label': 'Site',
                'description': 'Nome do site onde o cabo está instalado.',
            },
            {
                'key': 'device_name',
                'label': 'Equipamento',
                'description': 'Nome do equipamento monitorado.',
            },
            {
                'key': 'port_name',
                'label': 'Porta',
                'description': 'Identificação da porta ou interface afetada.',
            },
            {
                'key': 'signal_level',
                'label': 'Nível óptico',
                'description': 'Valor numérico do nível de sinal em dBm.',
            },
            {
                'key': 'signal_threshold',
                'label': 'Limite configurado',
                'description': 'Threshold configurado para o alerta.',
            },
            {
                'key': 'alarm_level',
                'label': 'Nível do alerta',
                'description': 'Classificação (Atenção ou Crítico).',
            },
        ],
        CATEGORY_INTERFACE_SIGNAL: [
            {
                'key': 'device_name',
                'label': 'Equipamento',
                'description': 'Nome do equipamento que abriga a interface.',
            },
            {
                'key': 'port_name',
                'label': 'Interface',
                'description': 'Identificação da porta ou interface monitorada.',
            },
            {
                'key': 'current_status',
                'label': 'Status atual',
                'description': 'Estado atual da interface (UP/DOWN).',
            },
            {
                'key': 'previous_status',
                'label': 'Status anterior',
                'description': 'Estado anterior antes da mudança.',
            },
            {
                'key': 'last_change',
                'label': 'Última alteração',
                'description': 'Timestamp da última mudança de status.',
            },
            {
                'key': 'traffic_in',
                'label': 'Tráfego de entrada',
                'description': 'Taxa de tráfego recebida mais recente (bps).',
            },
            {
                'key': 'traffic_out',
                'label': 'Tráfego de saída',
                'description': 'Taxa de tráfego transmitida mais recente (bps).',
            },
        ],
        CATEGORY_DEVICE_AVAILABILITY: [
            {
                'key': 'device_name',
                'label': 'Equipamento',
                'description': 'Nome do dispositivo afetado.',
            },
            {
                'key': 'site_name',
                'label': 'Site',
                'description': 'Localização onde o dispositivo está instalado.',
            },
            {
                'key': 'device_status',
                'label': 'Status do dispositivo',
                'description': 'Estado atual (Online, Offline, Indisponível).',
            },
            {
                'key': 'offline_since',
                'label': 'Offline desde',
                'description': 'Horário em que a indisponibilidade foi detectada.',
            },
            {
                'key': 'downtime_minutes',
                'label': 'Tempo indisponível (min)',
                'description': 'Duração estimada da indisponibilidade em minutos.',
            },
            {
                'key': 'acknowledged_by',
                'label': 'Reconhecido por',
                'description': 'Usuário que reconheceu o incidente, se aplicável.',
            },
        ],
    }

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default=CATEGORY_GENERIC)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default=CHANNEL_WHATSAPP)
    subject = models.CharField(max_length=255, blank=True, help_text='Usado apenas para envio por e-mail (SMTP).')
    content = models.TextField(help_text='Mensagem enviada ao contato. Use variáveis com {{chaves}}.')
    placeholders = models.JSONField(default=list, blank=True, help_text='Lista de chaves utilizadas neste modelo.')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text='Quando verdadeiro, este modelo será usado como padrão para a categoria/canal.',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_alert_templates',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_alert_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Modelo de aviso'
        verbose_name_plural = 'Modelos de aviso'
        db_table = 'setup_alert_templates'
        indexes = [
            models.Index(fields=['category', 'channel'], name='alert_tpl_cat_chan_idx'),
        ]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def extract_placeholders(cls, content: str) -> List[str]:
        """Retorna a lista de placeholders encontrados no conteúdo."""
        if not content:
            return []
        import re

        pattern = re.compile(r'{{\s*([a-zA-Z0-9_\.]+)\s*}}')
        return sorted(set(match.group(1) for match in pattern.finditer(content)))

    @classmethod
    def placeholder_catalog(cls) -> Dict[str, List[dict]]:
        """Retorna catálogo completo de placeholders por categoria."""
        catalog = {}
        for category, specific in cls.CATEGORY_PLACEHOLDERS.items():
            catalog[category] = list(cls.BASE_PLACEHOLDERS) + list(specific)
        return catalog

    def available_placeholders(self) -> List[dict]:
        """Lista de placeholders disponíveis para a categoria deste modelo."""
        base = list(self.BASE_PLACEHOLDERS)
        specific = list(self.CATEGORY_PLACEHOLDERS.get(self.category, []))
        return base + specific

    def refresh_placeholders(self):
        """Atualiza o campo placeholders com base no conteúdo."""
        self.placeholders = self.extract_placeholders(self.content)

    def save(self, *args, **kwargs):
        self.refresh_placeholders()
        super().save(*args, **kwargs)
        if self.is_default:
            (
                self.__class__.objects
                .filter(category=self.category, channel=self.channel, is_default=True)
                .exclude(pk=self.pk)
                .update(is_default=False)
            )

    @classmethod
    def get_default_template(cls, category: str, channel: str) -> Optional['AlertTemplate']:
        """Retorna o modelo padrão ativo para a categoria e canal informados."""
        queryset = cls.objects.filter(category=category, channel=channel, is_active=True)
        template = queryset.filter(is_default=True).order_by('-updated_at').first()
        if template:
            return template
        return queryset.order_by('-updated_at').first()


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
    site = models.ForeignKey(
        'inventory.Site',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='video_mosaics',
        help_text="Site associado a este mosaico (filtra câmeras por local)"
    )
    departments = models.ManyToManyField(
        'core.Department',
        related_name='video_mosaics',
        blank=True,
        help_text="Departamentos com permissão para visualizar este mosaico. Deixe vazio para acesso público (todos departamentos)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Mosaico de Vídeo"
        verbose_name_plural = "Mosaicos de Vídeo"

    def __str__(self) -> str:
        return f"{self.name} ({self.layout})"

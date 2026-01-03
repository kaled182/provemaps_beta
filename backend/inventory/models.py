"""
Inventory models for network infrastructure management.

These models were migrated from zabbix_api app but preserve the original
database table names using Meta.db_table to avoid data migration issues.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from .fields import LenientJSONField
from .utils_fiber import get_color_for_index

try:  # pragma: no cover - environment specific import
    from django.contrib.gis.db import models as gis_models
except (ImportError, ImproperlyConfigured):
    # CI environments without GDAL/GEOS support should still run the ORM and
    # unit tests. Fall back to a JSON representation that mimics the spatial
    # field API shape closely enough for non-spatial assertions.
    class _FallbackLineStringField(LenientJSONField):
        description = "Fallback LineString storage when GDAL is unavailable"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.pop("srid", None)
            kwargs.setdefault("null", True)
            kwargs.setdefault("blank", True)
            super().__init__(*args, **kwargs)

    class _FallbackPointField(LenientJSONField):
        description = "Fallback Point storage when GDAL is unavailable"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # Drop spatial-only kwargs so JSONField can initialize cleanly.
            for unsupported_key in ("srid", "geography", "spatial_index", "dim"):
                kwargs.pop(unsupported_key, None)
            kwargs.setdefault("null", True)
            kwargs.setdefault("blank", True)
            super().__init__(*args, **kwargs)

    class _FallbackGISModule:  # minimal shim with the attribute we need
        LineStringField = _FallbackLineStringField
        PointField = _FallbackPointField

    gis_models = _FallbackGISModule()  # type: ignore[assignment]


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
    # Phase 7: PostGIS PointField for optimized spatial queries
    # Enables ST_DWithin for accurate radius searches with GIST index
    # geography=True makes PostGIS use geography type (meters)
    # not geometry (degrees)
    location = gis_models.PointField(
        srid=4326, geography=True, null=True, blank=True
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


class DeviceGroup(models.Model):
    """
    Device group imported from Zabbix host groups.
    Used for categorization and filtering (e.g., "Switch Huawei",
    "Router Mikrotik", "VSOLUTION").
    """
    zabbix_groupid = models.CharField(
        max_length=32,
        unique=True,
        help_text="groupid inside Zabbix",
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Group name from Zabbix (e.g. 'Switch Huawei')",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "inventory_device_group"

    def __str__(self) -> str:
        return self.name


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
    primary_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Primary IP address of the device",
    )
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
    groups = models.ManyToManyField(
        DeviceGroup,
        related_name="devices",
        blank=True,
        help_text="Zabbix host groups for this device",
    )

    # --- DEVICE IMPORT SYSTEM FIELDS (Phase 11 - Nov 2025) ---
    
    # Categoria Visual para Mapas (Backbone, GPON, DWDM)
    CATEGORY_CHOICES = [
        ('backbone', 'Backbone / IP'),
        ('gpon', 'GPON / FTTx'),
        ('dwdm', 'DWDM / Óptico'),
        ('access', 'Acesso / Clientes'),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='backbone',
        db_index=True,
        help_text="Define a camada lógica para visualização nos mapas",
    )

    # Configurações de Alerta (Controladas pelo Modal de Importação)
    enable_screen_alert = models.BooleanField(
        default=True,
        verbose_name="Alerta em Tela",
        help_text="Exibir pop-up no dashboard em caso de falha",
    )
    enable_whatsapp_alert = models.BooleanField(
        default=False,
        verbose_name="Alerta WhatsApp",
        help_text="Enviar mensagem automática para o grupo de operações",
    )
    enable_email_alert = models.BooleanField(
        default=False,
        verbose_name="Alerta E-mail",
        help_text="Enviar e-mail para equipe de NOC",
    )

    # Grupo Principal de Monitoramento (Simplificação para Frontend)
    # Complementa o ManyToMany 'groups' com um FK para organização visual
    monitoring_group = models.ForeignKey(
        DeviceGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_devices',
        db_index=True,
        help_text="Grupo principal para organização visual no frontend",
    )

    class Meta:
        unique_together = ("site", "name")
        ordering = ["site__display_name", "name"]
        db_table = "zabbix_api_device"  # Preserve original table name
        indexes = [
            models.Index(
                fields=['category', 'monitoring_group'],
                name='device_cat_grp_idx'
            ),
            models.Index(fields=['zabbix_hostid'], name='device_zabbix_idx'),
        ]

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


class FiberProfile(models.Model):
    """
    Define o gabarito de construção do cabo (template de fábrica).
    
    Exemplo: "48FO (4x12)" significa 4 tubos com 12 fibras cada.
    Evita ter que configurar a construção a cada novo cabo lançado.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Ex: 'Cabo AS-80 48FO (4x12)', '144FO (12x12)'"
    )
    total_fibers = models.IntegerField(
        help_text="Capacidade total de fibras no cabo"
    )
    tube_count = models.IntegerField(
        default=1,
        help_text="Quantidade de tubos loose que o cabo possui"
    )
    fibers_per_tube = models.IntegerField(
        default=12,
        help_text="Quantidade de fibras dentro de cada tubo"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        help_text="Fabricante do cabo (Furukawa, Prysmian, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_fiber_profile"
        ordering = ["total_fibers", "name"]
        verbose_name = "Perfil de Fibra"
        verbose_name_plural = "Perfis de Fibra"

    def __str__(self) -> str:
        return f"{self.name} ({self.total_fibers}FO)"

    def clean(self) -> None:
        """Valida que tube_count * fibers_per_tube = total_fibers"""
        super().clean()
        if self.tube_count * self.fibers_per_tube != self.total_fibers:
            raise ValidationError(
                f"Inconsistência: {self.tube_count} tubos x "
                f"{self.fibers_per_tube} fibras = "
                f"{self.tube_count * self.fibers_per_tube}, "
                f"mas total_fibers={self.total_fibers}"
            )


class SpliceBoxTemplate(models.Model):
    """
    Template físico de Caixa de Emenda (CEO) conforme especificação de fábrica.
    Dados baseados na linha SVT da Fibracem (24–96 fibras, bandejas e portas).
    """
    name = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=50, default="Fibracem")
    model_code = models.CharField(max_length=50, blank=True)

    # Capacidade modular por bandejas
    max_trays = models.IntegerField(help_text="Máximo de bandejas suportadas")
    splices_per_tray = models.IntegerField(
        default=24,
        help_text="Fusões por bandeja (padrão Fibracem SVT = 24)"
    )

    # Portas físicas
    cable_ports_oval = models.IntegerField(
        default=1,
        help_text="Entrada oval (pass-through, 10–25mm)"
    )
    cable_ports_round = models.IntegerField(
        default=4,
        help_text="Entradas cilíndricas (derivação, 8–18mm)"
    )

    # Dimensões (opcional)
    length_mm = models.IntegerField(default=492)
    diameter_mm = models.IntegerField(default=195)

    class Meta:
        db_table = "inventory_splice_box_template"
        ordering = ["manufacturer", "name"]

    def total_capacity(self) -> int:
        return int(self.max_trays) * int(self.splices_per_tray)

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.name} ({self.total_capacity()}FO)"


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
    
    # Parent cable for segments (when cable is split)
    # If this field is set, this cable is a segment and should not
    # appear in the main cable list (only for internal CEO logic)
    parent_cable = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_segments',
        help_text="Cabo pai se este for um segmento criado por split"
    )
    
    # Hierarchical Structure (Phase 11.5 - Physical Fiber Modeling)
    profile = models.ForeignKey(
        FiberProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cables",
        help_text="Perfil técnico que define a estrutura interna do cabo"
    )
    
    # Topology: Logical Connection ("Inventory First, Routing Later" pattern)
    # Cables can be created without sites/ports (floating inventory)
    # and connected later via FiberConnectionModal
    site_a = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cables_start',
        help_text="Site de origem (opcional até conexão lógica)"
    )
    site_b = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cables_end',
        help_text="Site de destino (opcional até conexão lógica)"
    )
    
    origin_port = models.ForeignKey(
        Port,
        related_name="fiber_origin",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Porta de origem (opcional até terminação física)"
    )
    destination_port = models.ForeignKey(
        Port,
        related_name="fiber_destination",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Porta de destino (opcional até terminação física)"
    )
    length_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # Intermediate coordinates when plotting (may include origin/destination)
    path_coordinates = LenientJSONField(
        blank=True,
        null=True,
        help_text=(
            "Coordinate list e.g. [{'lat': -16.6, 'lng': -49.2}, ...]. "
            "Deprecated: use path field."
        ),
    )
    # Spatial field for PostGIS (Phase 10)
    # SRID 4326 = WGS84 (GPS coordinates)
    # Populated by data migration from path_coordinates
    path = gis_models.LineStringField(
        srid=4326,
        blank=True,
        null=True,
        help_text=(
            "Spatial path geometry for PostGIS spatial queries "
            "(bbox filtering)."
        ),
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

    def create_structure(self) -> bool:
        """
        Gera a estrutura física (Tubos e Fibras) baseada no Profile.
        Deve ser chamado após salvar o cabo se um profile for definido.
        
        Returns:
            bool: True se estrutura foi criada,
            False se já existia ou sem profile
        """
        if not self.profile:
            return False

        # Não recriar se já existir estrutura
        if self.tubes.exists():
            return False

        with transaction.atomic():
            # 1. Criar Tubos
            for tube_num in range(1, self.profile.tube_count + 1):
                tube_color_data = get_color_for_index(tube_num)
                tube = BufferTube.objects.create(
                    cable=self,
                    number=tube_num,
                    color=tube_color_data['name'],
                    color_hex=tube_color_data['hex']
                )

                # 2. Criar Fibras dentro do Tubo
                fibers_to_create = []
                for fiber_num in range(1, self.profile.fibers_per_tube + 1):
                    fiber_color_data = get_color_for_index(fiber_num)
                    # Número absoluto da fibra no cabo
                    # Ex: fibra 13 é a 1ª do 2º tubo em um cabo 4x12
                    absolute_num = (
                        (tube_num - 1) * self.profile.fibers_per_tube
                    ) + fiber_num

                    fibers_to_create.append(FiberStrand(
                        tube=tube,
                        number=fiber_num,
                        absolute_number=absolute_num,
                        color=fiber_color_data['name'],
                        color_hex=fiber_color_data['hex'],
                        status='dark'  # Padrão: Apagada
                    ))

                FiberStrand.objects.bulk_create(fibers_to_create)

        return True


class BufferTube(models.Model):
    """
    Tubo Loose (unidade de proteção que agrupa fibras).
    Segue padrão de cores ABNT NBR 14565 / TIA-598.
    """
    cable = models.ForeignKey(
        FiberCable,
        on_delete=models.CASCADE,
        related_name='tubes',
        help_text="Cabo ao qual este tubo pertence"
    )
    number = models.IntegerField(
        help_text="Número sequencial do tubo (1, 2, 3...)"
    )
    color = models.CharField(
        max_length=30,
        help_text="Nome da cor do tubo conforme padrão ABNT"
    )
    color_hex = models.CharField(
        max_length=7,
        default='#FFFFFF',
        help_text="Código hexadecimal da cor"
    )

    class Meta:
        db_table = "inventory_buffer_tube"
        ordering = ["cable", "number"]
        unique_together = [["cable", "number"]]
        verbose_name = "Tubo Loose"
        verbose_name_plural = "Tubos Loose"

    def __str__(self) -> str:
        return f"{self.cable.name} - Tubo {self.number} ({self.color})"


class FiberStrand(models.Model):
    """
    O fio de fibra individual (filamento de vidro).
    Esta é a unidade atômica do sistema de gerenciamento.
    """
    STATUS_DARK = "dark"
    STATUS_LIT = "lit"
    STATUS_RESERVED = "reserved"
    STATUS_BROKEN = "broken"
    STATUS_CHOICES = [
        (STATUS_DARK, "Apagada (Dark Fiber)"),
        (STATUS_LIT, "Iluminada (Ativa)"),
        (STATUS_RESERVED, "Reservada"),
        (STATUS_BROKEN, "Rompida"),
    ]

    tube = models.ForeignKey(
        BufferTube,
        on_delete=models.CASCADE,
        related_name='strands',
        help_text="Tubo ao qual esta fibra pertence"
    )
    number = models.IntegerField(
        help_text="Número da fibra dentro do tubo (1-12 tipicamente)"
    )
    absolute_number = models.IntegerField(
        help_text="Número sequencial no cabo (1-144 para cabo 144FO)"
    )
    color = models.CharField(
        max_length=30,
        help_text="Nome da cor da fibra conforme padrão ABNT"
    )
    color_hex = models.CharField(
        max_length=7,
        help_text="Código hexadecimal da cor"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DARK,
        help_text="Status operacional da fibra"
    )

    # --- CONEXÕES FÍSICAS (segredo da modelagem) ---
    
    # Conexão com Porta de Equipamento (Ex: Porta SFP do Switch via DIO)
    connected_device_port = models.OneToOneField(
        Port,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connected_fiber',
        help_text="Porta de dispositivo conectada (DIO, ODF, Switch)"
    )

    # Metadados de qualidade (medições ópticas)
    attenuation_db = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Atenuação medida em dB (OTDR)"
    )
    last_test_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última medição OTDR"
    )
    notes = models.TextField(
        blank=True,
        help_text="Observações técnicas sobre esta fibra"
    )
    
    # --- Segmentação de Cabo (rastreabilidade) ---
    segment = models.ForeignKey(
        'CableSegment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='strands',
        help_text="Segmento ao qual esta fibra pertence (para rastreabilidade)"
    )

    class Meta:
        db_table = "inventory_fiber_strand"
        ordering = ["absolute_number"]
        unique_together = [["tube", "number"]]
        verbose_name = "Filamento de Fibra"
        verbose_name_plural = "Filamentos de Fibra"

    def __str__(self) -> str:
        return (
            f"{self.tube.cable.name} - "
            f"T{self.tube.number}F{self.number} ({self.color})"
        )

    @property
    def full_address(self) -> dict[str, Any]:
        """Endereço completo da fibra (para documentação)"""
        return {
            "cable": self.tube.cable.name,
            "tube": self.tube.number,
            "tube_color": self.tube.color,
            "fiber": self.number,
            "fiber_color": self.color,
            "notation": f"T{self.tube.number}F{self.number}",
            "absolute": self.absolute_number,
        }


class FiberFusion(models.Model):
    """Fusão física entre duas fibras em uma infraestrutura."""

    infrastructure = models.ForeignKey(
        'FiberInfrastructure',
        on_delete=models.CASCADE,
        related_name='fusions',
        help_text="Infraestrutura (CEO) onde a fusão foi realizada",
    )
    tray = models.IntegerField(
        null=True,
        blank=True,
        help_text="Número da bandeja onde a fusão está registrada",
    )
    slot = models.IntegerField(
        null=True,
        blank=True,
        help_text="Slot físico dentro da bandeja (1–24)",
    )
    fiber_a = models.ForeignKey(
        'FiberStrand',
        on_delete=models.CASCADE,
        related_name='fusions_as_a',
        help_text="Primeira fibra participante da fusão",
    )
    fiber_b = models.ForeignKey(
        'FiberStrand',
        on_delete=models.CASCADE,
        related_name='fusions_as_b',
        help_text="Segunda fibra participante da fusão",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_fiber_fusion'
        verbose_name = 'Fusão de Fibra'
        verbose_name_plural = 'Fusões de Fibra'
        constraints = [
            models.UniqueConstraint(
                fields=['infrastructure', 'tray', 'slot'],
                name='inventory_fiber_fusion_unique_slot',
            )
        ]
        indexes = [
            models.Index(
                fields=['fiber_a'],
                name='idx_fusion_fiber_a',
            ),
            models.Index(
                fields=['fiber_b'],
                name='idx_fusion_fiber_b',
            ),
            models.Index(
                fields=['infrastructure'],
                name='idx_fusion_infrastructure',
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - logging helper
        tray_label = self.tray if self.tray is not None else '-'
        slot_label = self.slot if self.slot is not None else '-'
        return (
            f"Fusion infra={self.infrastructure_id} "
            f"tray={tray_label} slot={slot_label} "
            f"({self.fiber_a_id}<->{self.fiber_b_id})"
        )


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


class FiberInfrastructure(models.Model):
    TYPES = [
        ("slack", "Reserva Técnica"),
        ("splice_box", "Caixa de Emenda (CEO)"),
        ("splitter_box", "Caixa de Atendimento (CTO)"),
        ("transition", "Transição Aéreo/Subt"),
    ]

    cable = models.ForeignKey(
        FiberCable,
        on_delete=models.CASCADE,
        related_name="infrastructure_points",
    )

    type = models.CharField(max_length=20, choices=TYPES)
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ex: CEO-01-BKB",
    )

    # Localização geográfica exata (Point) em WGS84
    location = gis_models.PointField(geography=True, srid=4326)

    # Metragem sequencial calculada (Linear Referencing)
    distance_from_origin = models.FloatField(
        null=True,
        blank=True,
        help_text="Distância em metros a partir do início do cabo",
    )

    # Metadados flexíveis
    metadata = models.JSONField(default=dict, blank=True)

    # Template físico (opcional, para CEOs)
    box_template = models.ForeignKey(
        SpliceBoxTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installed_boxes'
    )
    installed_trays = models.IntegerField(
        default=1,
        help_text="Quantidade de bandejas instaladas fisicamente"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["distance_from_origin", "created_at", "id"]
        db_table = "inventory_fiber_infrastructure"
        verbose_name = "Ponto de Infraestrutura"
        verbose_name_plural = "Pontos de Infraestrutura"

    def __str__(self) -> str:
        has_dist = self.distance_from_origin is not None
        dist_val = f"{self.distance_from_origin:.1f}m"
        dist = dist_val if has_dist else "sem distância"
        return f"{self.get_type_display()} @ {dist}"


class InfrastructureCableAttachment(models.Model):
    """
    Representa como um cabo se conecta fisicamente a uma caixa (CEO/CTO):
    porta oval (pass-through) ou porta redonda (derivação/entrada).
    """
    PORT_CHOICES = [
        ("oval", "Oval (Passagem)"),
        ("round", "Redonda (Derivação)"),
    ]

    infrastructure = models.ForeignKey(
        FiberInfrastructure,
        related_name='attached_cables',
        on_delete=models.CASCADE,
    )
    cable = models.ForeignKey(
        FiberCable,
        related_name='attachments',
        on_delete=models.CASCADE,
    )
    port_type = models.CharField(max_length=10, choices=PORT_CHOICES)
    is_pass_through = models.BooleanField(
        default=False,
        help_text="Se verdadeiro, cabo entra e sai (sangria/pass-through)"
    )

    class Meta:
        db_table = 'inventory_infrastructure_cable_attachment'
        unique_together = [['infrastructure', 'cable', 'port_type']]
        ordering = ['infrastructure_id']

    def __str__(self) -> str:
        return (
            f"{self.cable.name} @ {self.infrastructure.name} "
            f"({self.port_type})"
        )


class CableSegment(models.Model):
    """
    Representa um segmento lógico de um cabo físico.
    
    Uso: Quando um cabo passa por múltiplas CEOs, ele é dividido em segmentos
    para permitir rastreabilidade e fusões corretas.
    
    Exemplo:
        Cabo-Principal (50km total):
          - Seg1: Site A → CEO-01 (20km)
          - Seg2: CEO-01 → CEO-02 (15km)
          - Seg3: CEO-02 → Site B (15km)
    
    Na CEO-01, fusões acontecem entre Seg1 e Seg2 (não "consigo mesmo").
    """
    STATUS_ACTIVE = 'active'
    STATUS_BROKEN = 'broken'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Ativo'),
        (STATUS_BROKEN, 'Rompido'),
        (STATUS_INACTIVE, 'Inativo'),
    ]
    
    cable = models.ForeignKey(
        FiberCable,
        on_delete=models.CASCADE,
        related_name='segments',
        help_text='Cabo físico ao qual este segmento pertence'
    )
    segment_number = models.IntegerField(
        help_text='Número sequencial do segmento (1, 2, 3...)'
    )
    name = models.CharField(
        max_length=200,
        help_text='Ex: Cabo-Principal-Seg1'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text='Status físico do segmento (ativo, rompido, inativo)'
    )
    
    # Infraestruturas de início e fim
    start_infrastructure = models.ForeignKey(
        FiberInfrastructure,
        on_delete=models.SET_NULL,
        related_name='segments_starting_here',
        null=True,
        blank=True,
        help_text='Infraestrutura de origem (CEO, Site, etc.)'
    )
    end_infrastructure = models.ForeignKey(
        FiberInfrastructure,
        on_delete=models.SET_NULL,
        related_name='segments_ending_here',
        null=True,
        blank=True,
        help_text='Infraestrutura de destino'
    )
    
    length_meters = models.FloatField(
        default=0,
        help_text='Comprimento deste segmento em metros'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_cable_segment'
        ordering = ['cable', 'segment_number']
        unique_together = [['cable', 'segment_number']]
        indexes = [
            models.Index(
                fields=['cable', 'segment_number'],
                name='idx_cable_seg_num',
            ),
            models.Index(
                fields=['start_infrastructure'],
                name='idx_seg_start',
            ),
            models.Index(
                fields=['end_infrastructure'],
                name='idx_seg_end',
            ),
        ]
        verbose_name = 'Segmento de Cabo'
        verbose_name_plural = 'Segmentos de Cabo'
    
    def __str__(self) -> str:
        return f"{self.name} ({self.length_meters:.0f}m)"


class ImportRule(models.Model):
    """
    Regex-based rule for automatic device categorization during Zabbix import.
    Applied in priority order (lowest number first) to match device names.
    
    Example:
        pattern = r'^OLT.*'
        category = 'gpon'
        group = DeviceGroup(name='OLT Huawei')
        priority = 10
    """
    pattern = models.CharField(
        max_length=255,
        help_text="Regex pattern to match device name (case-insensitive)",
    )
    category = models.CharField(
        max_length=20,
        choices=Device.CATEGORY_CHOICES,
        help_text="Category to assign when pattern matches",
    )
    group = models.ForeignKey(
        DeviceGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional monitoring group to auto-assign",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive rules are ignored during import",
    )
    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Lower numbers = higher priority (0 = highest)",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable explanation of the rule",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]
        db_table = "inventory_import_rule"
        indexes = [
            models.Index(
                fields=['is_active', 'priority'],
                name='rule_active_prio_idx'
            ),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_active else "✗"
        return f"[{status}] P{self.priority}: {self.pattern} → {self.category}"


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

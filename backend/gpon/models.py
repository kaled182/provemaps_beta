"""Estado das ONU guardado pelo ProVeMaps (EV-0095, ADR 0010).

O Zabbix dá o estado ATUAL de cada ONU mas não transições fiáveis (o «último offline» da OLT
ZTE vem do relógio dela, que está errado). A coleta (``gpon.tasks.collect_onu_states``) grava
aqui o que observa a cada 120 s e ``status_since`` passa a ser a hora em que o ProVeMaps viu a
mudança — é isso que permite «online desde» e a queda coletiva com janela real de 10 min.
"""

from __future__ import annotations

from django.db import models


class OnuState(models.Model):
    VENDOR_CHOICES = (("zte", "ZTE"), ("vsol", "VSOL"))
    TECHNOLOGY_CHOICES = (("gpon", "GPON"), ("epon", "EPON"))
    STATUS_CHOICES = (("online", "Online"), ("offline", "Offline"), ("unknown", "Desconhecido"))
    REASON_CHOICES = (("los", "LOS"), ("dying_gasp", "Dying gasp"), ("other", "Outro"))

    # Sem índice próprio: os dois índices compostos abaixo começam por `device`.
    device = models.ForeignKey(
        "inventory.Device", on_delete=models.CASCADE, related_name="onu_states", db_index=False
    )
    # Identidade estável da ONU na OLT: serial na ZTE; «<pon>:<n>|<mac ou serial>» na VSOL.
    onu_key = models.CharField(max_length=128)
    vendor = models.CharField(max_length=8, choices=VENDOR_CHOICES)
    technology = models.CharField(max_length=8, choices=TECHNOLOGY_CHOICES)
    pon_id = models.CharField(max_length=32)
    onu_index = models.PositiveIntegerField(null=True, blank=True)
    serial = models.CharField(max_length=64, blank=True)
    mac = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="unknown")
    reason = models.CharField(max_length=16, choices=REASON_CHOICES, blank=True)
    reason_label = models.CharField(max_length=64, blank=True)
    raw_status = models.CharField(max_length=32, blank=True)
    raw_reason = models.CharField(max_length=32, blank=True)

    rx_onu_dbm = models.FloatField(null=True, blank=True)
    rx_olt_dbm = models.FloatField(null=True, blank=True)
    distance_m = models.PositiveIntegerField(null=True, blank=True)
    # Chave do item numérico de RX no Zabbix (histórico); vazia = sem histórico.
    rx_item_key = models.CharField(max_length=255, blank=True)

    status_since = models.DateTimeField()
    # True enquanto `status_since` é só a primeira observação (o ecrã diz «desde ≥ …»).
    status_since_is_first_seen = models.BooleanField(default=True)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()

    # Preparação SGP/Radius — hoje sempre vazios.
    cliente_nome = models.CharField(max_length=200, blank=True)
    login_radius = models.CharField(max_length=128, blank=True)
    caixa_cto = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = "Estado de ONU"
        verbose_name_plural = "Estados de ONU"
        constraints = [
            models.UniqueConstraint(fields=["device", "onu_key"], name="gpon_onu_device_key_uniq"),
        ]
        indexes = [
            models.Index(fields=["device", "pon_id"], name="gpon_onu_device_pon_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.onu_key} ({self.pon_id}) {self.status}"

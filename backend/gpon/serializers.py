"""Esquema OpenAPI do Monitoramento GPON (EV-0095). Campos na ordem exata do contrato.

As views devolvem o dict do usecase tal como está (a ordem das chaves é contrato com o
frontend); estes serializers documentam-no em ``/api/schema/swagger/`` e validam os parâmetros.
"""

from __future__ import annotations

from rest_framework import serializers

from inventory.api.device_summaries import (  # noqa: F401 (reexportado para gpon.api)
    DeviceIdsQuerySerializer,
)

from .usecases import HISTORY_HOURS_DEFAULT, HISTORY_HOURS_MAX, HISTORY_HOURS_MIN


class GponOverviewQuerySerializer(serializers.Serializer):
    olt = serializers.IntegerField(required=False, min_value=1)


class OnuHistoryQuerySerializer(serializers.Serializer):
    hours = serializers.IntegerField(
        required=False,
        default=HISTORY_HOURS_DEFAULT,
        min_value=HISTORY_HOURS_MIN,
        max_value=HISTORY_HOURS_MAX,
    )


class ThresholdsSerializer(serializers.Serializer):
    warning = serializers.FloatField()
    critical = serializers.FloatField()


class CapacitySerializer(serializers.Serializer):
    gpon = serializers.IntegerField()
    epon = serializers.IntegerField()


class TotalsSerializer(serializers.Serializer):
    olts = serializers.IntegerField()
    olts_online = serializers.IntegerField()
    olts_offline = serializers.IntegerField()
    pons = serializers.IntegerField()
    onus_provisioned = serializers.IntegerField()
    onus_online = serializers.IntegerField()
    onus_offline = serializers.IntegerField()
    onus_unknown = serializers.IntegerField()
    signal_warning = serializers.IntegerField()
    signal_critical = serializers.IntegerField()
    los = serializers.IntegerField()
    dying_gasp = serializers.IntegerField()
    pons_collective_drop = serializers.IntegerField()


class PonSerializer(serializers.Serializer):
    pon_id = serializers.CharField()
    label = serializers.CharField()
    status = serializers.ChoiceField(choices=["up", "down", "unknown"])
    capacity = serializers.IntegerField()
    onus_provisioned = serializers.IntegerField()
    onus_online = serializers.IntegerField()
    occupancy_pct = serializers.FloatField(allow_null=True)
    rx_avg_dbm = serializers.FloatField(allow_null=True)
    los = serializers.IntegerField()
    dying_gasp = serializers.IntegerField()
    signal_warning = serializers.IntegerField()
    signal_critical = serializers.IntegerField()
    collective_drop = serializers.BooleanField()
    severity = serializers.ChoiceField(choices=["normal", "warning", "critical"])


class OltSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    name = serializers.CharField()
    vendor = serializers.ChoiceField(choices=["zte", "vsol"])
    technology = serializers.ChoiceField(choices=["gpon", "epon"])
    model = serializers.CharField(allow_null=True)
    ip = serializers.CharField(allow_null=True)
    site_name = serializers.CharField(allow_null=True)
    site_id = serializers.IntegerField(allow_null=True)
    status = serializers.ChoiceField(choices=["online", "offline", "unknown"])
    collection_ok = serializers.BooleanField()
    cpu_pct = serializers.FloatField(allow_null=True)
    temperature_c = serializers.FloatField(allow_null=True)
    onus_total = serializers.IntegerField()
    onus_online = serializers.IntegerField()
    pons = PonSerializer(many=True)


class OnuSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    device_id = serializers.IntegerField()
    olt_name = serializers.CharField()
    pon_id = serializers.CharField()
    onu_index = serializers.IntegerField(allow_null=True)
    serial = serializers.CharField(allow_null=True)
    mac = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=["online", "offline", "unknown"])
    reason = serializers.ChoiceField(choices=["los", "dying_gasp", "other"], allow_null=True)
    reason_label = serializers.CharField(allow_null=True)
    rx_onu_dbm = serializers.FloatField(allow_null=True)
    rx_olt_dbm = serializers.FloatField(allow_null=True)
    signal = serializers.ChoiceField(choices=["normal", "warning", "critical"], allow_null=True)
    distance_m = serializers.IntegerField(allow_null=True)
    status_since = serializers.DateTimeField(allow_null=True)
    status_since_is_first_seen = serializers.BooleanField()
    last_seen = serializers.DateTimeField(allow_null=True)
    cliente_nome = serializers.CharField(allow_null=True)
    login_radius = serializers.CharField(allow_null=True)
    caixa_cto = serializers.CharField(allow_null=True)
    severity_rank = serializers.IntegerField(min_value=0, max_value=6)
    has_history = serializers.BooleanField()


class GponOverviewSerializer(serializers.Serializer):
    collected_at = serializers.DateTimeField(allow_null=True)
    zabbix_ok = serializers.BooleanField(allow_null=True)
    zabbix_error = serializers.CharField(allow_null=True)
    thresholds = ThresholdsSerializer()
    capacity = CapacitySerializer()
    totals = TotalsSerializer()
    olts = OltSerializer(many=True)
    onus = OnuSerializer(many=True)


class HistoryPointSerializer(serializers.Serializer):
    x = serializers.DateTimeField()
    y = serializers.FloatField(allow_null=True)


class OnuHistorySerializer(serializers.Serializer):
    onu_id = serializers.IntegerField()
    unit = serializers.CharField()
    label = serializers.CharField()
    points = HistoryPointSerializer(many=True)
    zabbix_ok = serializers.BooleanField()
    zabbix_error = serializers.CharField(allow_null=True)


# ── EV-0108: eventos de ONU por PON ──────────────────────────────────────────
class PonEventsQuerySerializer(serializers.Serializer):
    device = serializers.IntegerField(min_value=1)
    pon = serializers.CharField(max_length=32)
    hours = serializers.IntegerField(min_value=1, max_value=168, default=24)


class OnuEventSerializer(serializers.Serializer):
    at = serializers.DateTimeField()
    onu_id = serializers.IntegerField()
    onu_index = serializers.IntegerField(allow_null=True)
    serial = serializers.CharField(allow_null=True)
    mac = serializers.CharField(allow_null=True)
    cliente_nome = serializers.CharField(allow_null=True)
    kind = serializers.ChoiceField(choices=["online", "offline", "los", "dying_gasp"])
    label = serializers.CharField(allow_null=True)
    previous_kind = serializers.ChoiceField(
        choices=["online", "offline", "los", "dying_gasp"], allow_null=True
    )


class PonEventsSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    pon_id = serializers.CharField()
    hours = serializers.IntegerField()
    since = serializers.DateTimeField(allow_null=True)
    truncated = serializers.BooleanField()
    events = OnuEventSerializer(many=True)


# ── EV-0109: tendência 24 h do RX da PON e tráfego da porta ─────────────────
class PonTrendQuerySerializer(serializers.Serializer):
    device = serializers.IntegerField(min_value=1)
    pon = serializers.CharField(max_length=32)


class PonRxPointSerializer(serializers.Serializer):
    t = serializers.DateTimeField()
    rx_avg_dbm = serializers.FloatField()
    rx_worst_dbm = serializers.FloatField()
    onus = serializers.IntegerField()


class TrafficPointSerializer(serializers.Serializer):
    t = serializers.DateTimeField()
    bps = serializers.FloatField(allow_null=True)


class PonTrafficSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    in_bps = serializers.FloatField(allow_null=True)
    out_bps = serializers.FloatField(allow_null=True)
    at = serializers.DateTimeField(allow_null=True)
    stale = serializers.BooleanField()
    out = TrafficPointSerializer(many=True)


# «in» é palavra reservada em Python: o campo entra com o nome real da resposta.
PonTrafficSerializer._declared_fields["in"] = TrafficPointSerializer(many=True)


class PonTrendSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    pon_id = serializers.CharField()
    hours = serializers.IntegerField()
    rx = PonRxPointSerializer(many=True)
    traffic = PonTrafficSerializer()
    zabbix_ok = serializers.BooleanField()
    zabbix_error = serializers.CharField(allow_null=True)


# ── EV-0111: resumo por OLT (cards do modal de Site) ─────────────────────────
# A consulta (`device_ids=1,2`) usa DeviceIdsQuerySerializer do inventário (importado no topo).
class OltSummarySerializer(serializers.Serializer):
    vendor = serializers.CharField()
    technology = serializers.CharField()
    onus_total = serializers.IntegerField()
    onus_online = serializers.IntegerField()
    signal_warning = serializers.IntegerField()
    signal_critical = serializers.IntegerField()


class OltSummariesSerializer(serializers.Serializer):
    olts = serializers.DictField(child=OltSummarySerializer())

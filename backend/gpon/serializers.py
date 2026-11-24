"""Esquema OpenAPI do Monitoramento GPON (EV-0095). Campos na ordem exata do contrato.

As views devolvem o dict do usecase tal como está (a ordem das chaves é contrato com o
frontend); estes serializers documentam-no em ``/api/schema/swagger/`` e validam os parâmetros.
"""

from __future__ import annotations

from rest_framework import serializers

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

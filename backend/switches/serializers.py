"""Esquema OpenAPI do Monitoramento de Switches (EV-0115). Campos na ordem do payload."""

from __future__ import annotations

from rest_framework import serializers


class SwitchesQuerySerializer(serializers.Serializer):
    refresh = serializers.BooleanField(required=False, default=False)


class ThresholdsSerializer(serializers.Serializer):
    warning = serializers.FloatField()
    critical = serializers.FloatField()
    utilization_pct = serializers.FloatField()


class TopSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    name = serializers.CharField()
    value = serializers.FloatField()


class TotalsSerializer(serializers.Serializer):
    switches = serializers.IntegerField()
    switches_online = serializers.IntegerField()
    switches_offline = serializers.IntegerField()
    switches_unknown = serializers.IntegerField()
    ports_monitored = serializers.IntegerField()
    ports_up = serializers.IntegerField()
    ports_in_use = serializers.IntegerField()
    ports_free = serializers.IntegerField()
    ports_down = serializers.IntegerField()
    signal_warning = serializers.IntegerField()
    signal_critical = serializers.IntegerField()
    high_utilization = serializers.IntegerField()
    hottest = TopSerializer(allow_null=True)
    busiest_cpu = TopSerializer(allow_null=True)


class SwitchSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    name = serializers.CharField()
    vendor = serializers.CharField()
    model = serializers.CharField(allow_null=True)
    ip = serializers.CharField(allow_null=True)
    site_id = serializers.IntegerField(allow_null=True)
    site_name = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=["online", "offline", "unknown"])
    collection_ok = serializers.BooleanField()
    cpu_pct = serializers.FloatField(allow_null=True)
    temperature_c = serializers.FloatField(allow_null=True)
    uptime_s = serializers.FloatField(allow_null=True)
    ports_total = serializers.IntegerField()
    ports_up = serializers.IntegerField()
    ports_in_use = serializers.IntegerField()
    ports_down = serializers.IntegerField()
    signal_warning = serializers.IntegerField()
    signal_critical = serializers.IntegerField()
    high_utilization = serializers.IntegerField()
    worst_rx_dbm = serializers.FloatField(allow_null=True)
    last_clock = serializers.DateTimeField(allow_null=True)


class SwitchPortSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    switch_name = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    kind = serializers.ChoiceField(choices=["optical", "electrical", "mgmt"])
    speed_mbps = serializers.FloatField(allow_null=True)
    speed_label = serializers.CharField(allow_null=True)
    admin = serializers.CharField()
    oper = serializers.CharField()
    in_use = serializers.BooleanField()
    state = serializers.ChoiceField(
        choices=["normal", "warning", "critical", "down", "free", "unknown"]
    )
    reasons = serializers.ListField(child=serializers.CharField())
    rx_dbm = serializers.FloatField(allow_null=True)
    tx_dbm = serializers.FloatField(allow_null=True)
    los = serializers.BooleanField()
    in_bps = serializers.FloatField(allow_null=True)
    out_bps = serializers.FloatField(allow_null=True)
    utilization_pct = serializers.FloatField(allow_null=True)
    in_errors = serializers.FloatField(allow_null=True)
    out_errors = serializers.FloatField(allow_null=True)
    uptime_s = serializers.IntegerField(allow_null=True)
    port_id = serializers.IntegerField(allow_null=True)
    cable_id = serializers.IntegerField(allow_null=True)
    cable_name = serializers.CharField(allow_null=True)
    severity_rank = serializers.IntegerField()


class SwitchesOverviewSerializer(serializers.Serializer):
    collected_at = serializers.DateTimeField()
    zabbix_ok = serializers.BooleanField()
    zabbix_error = serializers.CharField(allow_null=True)
    thresholds = ThresholdsSerializer()
    totals = TotalsSerializer()
    switches = SwitchSerializer(many=True)
    ports = SwitchPortSerializer(many=True)
    duration_ms = serializers.IntegerField()

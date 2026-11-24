"""Resumos de dispositivo para o modal de Site.

- ``GET /api/v1/inventory/devices/ports-summary/?device_ids=1,2`` (EV-0111)
- ``GET /api/v1/inventory/devices/<id>/temperature/`` (EV-0112)
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.usecases.device_summaries import device_temperature, ports_summaries


class DeviceIdsQuerySerializer(serializers.Serializer):
    device_ids = serializers.CharField(max_length=2000)

    def validate_device_ids(self, value: str) -> list[int]:
        try:
            ids = sorted({int(x) for x in value.split(",") if x.strip()})
        except ValueError as exc:
            raise serializers.ValidationError("lista de inteiros separados por vírgula") from exc
        if not ids or len(ids) > 200 or min(ids) < 1:
            raise serializers.ValidationError("entre 1 e 200 ids positivos")
        return ids


class PortsSummaryItemSerializer(serializers.Serializer):
    ports_total = serializers.IntegerField()
    ports_in_use = serializers.IntegerField()
    worst_rx_dbm = serializers.FloatField(allow_null=True)
    worst_rx_level = serializers.CharField(allow_null=True)
    stale_readings = serializers.IntegerField()


class ThresholdsSerializer(serializers.Serializer):
    warning = serializers.FloatField(allow_null=True)
    critical = serializers.FloatField(allow_null=True)


class PortsSummarySerializer(serializers.Serializer):
    devices = serializers.DictField(child=PortsSummaryItemSerializer())
    thresholds = ThresholdsSerializer()


class PortsSummaryView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("device_ids", str, description="ids separados por vírgula (até 200)")
        ],
        responses=PortsSummarySerializer,
        summary="Portas em uso e pior RX óptico por dispositivo (cards do modal de Site)",
    )
    def get(self, request: Request) -> Response:
        query = DeviceIdsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(ports_summaries(query.validated_data["device_ids"]))


class DeviceTemperatureSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    temperature_c = serializers.FloatField(allow_null=True)
    sensor = serializers.CharField(allow_null=True)
    sensors = serializers.IntegerField()
    at = serializers.DateTimeField(allow_null=True)
    reason = serializers.ChoiceField(choices=["no_host", "no_item", "no_reading"], allow_null=True)
    zabbix_ok = serializers.BooleanField()


class DeviceTemperatureView(APIView):
    @extend_schema(
        responses=DeviceTemperatureSerializer,
        summary="Temperatura mais alta entre os sensores do equipamento (Zabbix)",
    )
    def get(self, request: Request, device_id: int) -> Response:
        return Response(device_temperature(device_id))

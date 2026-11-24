"""OTDR: ``GET /api/v1/inventory/cables/<id>/otdr-locate/`` (EV-0127) e os alertas fixados no mapa,
``GET|POST /api/v1/inventory/otdr-alerts/`` e ``POST …/otdr-alerts/<id>/clear/`` (EV-0128)."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.usecases.devices_common import InventoryValidationError
from inventory.usecases.otdr import (
    DIRECTIONS,
    SLACK_PCT_MAX,
    active_alerts,
    adjust_alert,
    clear_alert,
    locate_otdr,
    pin_alert,
)


class OtdrQuerySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=list(DIRECTIONS))
    distance_m = serializers.FloatField(min_value=1)
    slack_pct = serializers.FloatField(min_value=0, max_value=SLACK_PCT_MAX, default=0)
    # EV-0130: ajuste fino (m sobre o traçado; o ponto fica entre as pontas)
    offset_m = serializers.FloatField(default=0, min_value=-500_000, max_value=500_000)
    # EV-0131: medição cruzada — leitura do Site B (distance_m é então a do A; direction ignorado)
    distance_b_m = serializers.FloatField(required=False, min_value=1)


class OtdrSiteSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    distance_m = serializers.FloatField()


class OtdrRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    type_label = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    distance_m = serializers.FloatField(help_text="distância sobre o traçado até ao ponto")


class OtdrReferencesSerializer(serializers.Serializer):
    registered = serializers.IntegerField(help_text="caixas/reservas cadastradas no cabo")
    before = OtdrRefSerializer(allow_null=True)
    after = OtdrRefSerializer(allow_null=True)


class OtdrCrossSerializer(serializers.Serializer):
    reading_a_m = serializers.FloatField()
    reading_b_m = serializers.FloatField()
    fiber_length_m = serializers.FloatField()
    slack_real_pct = serializers.FloatField()
    proportion = serializers.FloatField()


class OtdrResultSerializer(serializers.Serializer):
    cable_id = serializers.IntegerField()
    cable_name = serializers.CharField()
    direction = serializers.CharField()
    otdr_m = serializers.FloatField()
    slack_pct = serializers.FloatField()
    map_distance_m = serializers.FloatField()
    base_map_distance_m = serializers.FloatField()
    offset_m = serializers.FloatField()
    path_length_m = serializers.FloatField()
    inventory_length_km = serializers.FloatField(allow_null=True)
    origin = OtdrSiteSerializer()
    target = OtdrSiteSerializer()
    point = serializers.ListField(child=serializers.FloatField(), help_text="[lng, lat]")
    segment = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    tolerance_m = serializers.FloatField()
    references = OtdrReferencesSerializer()
    mode = serializers.ChoiceField(choices=["single", "cross"])
    cross = OtdrCrossSerializer(allow_null=True)
    warnings = serializers.ListField(child=serializers.CharField())


class OtdrLocateView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "direction", str, description="ab = medido a partir do Site A; ba = do B"
            ),
            OpenApiParameter("distance_m", float, description="leitura do OTDR, em metros"),
            OpenApiParameter("slack_pct", float, description="folga/reserva técnica em % (0 a 20)"),
        ],
        responses=OtdrResultSerializer,
        summary="Ponto provável do rompimento no traçado do cabo a partir da leitura do OTDR",
    )
    def get(self, request: Request, cable_id: int) -> Response:
        query = OtdrQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        v = query.validated_data
        try:
            data = locate_otdr(
                cable_id,
                direction=v["direction"],
                distance_m=v["distance_m"],
                slack_pct=v["slack_pct"],
                offset_m=v["offset_m"],
                distance_b_m=v.get("distance_b_m"),
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data)


class OtdrPinSerializer(serializers.Serializer):
    cable_id = serializers.IntegerField(min_value=1)
    direction = serializers.ChoiceField(choices=list(DIRECTIONS))
    distance_m = serializers.FloatField(min_value=1)
    slack_pct = serializers.FloatField(min_value=0, max_value=SLACK_PCT_MAX, default=0)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    distance_b_m = serializers.FloatField(required=False, min_value=1)  # EV-0131
    offset_m = serializers.FloatField(default=0, min_value=-500_000, max_value=500_000)


class OtdrAlertSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cable_id = serializers.IntegerField()
    note = serializers.CharField(allow_blank=True)
    created_by = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    result = OtdrResultSerializer()
    log = serializers.ListField(child=serializers.DictField(), help_text="registo do atendimento")


class OtdrAdjustSerializer(serializers.Serializer):
    offset_m = serializers.FloatField(min_value=-500_000, max_value=500_000)


class OtdrAlertClearedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cleared_at = serializers.DateTimeField()


class OtdrAlertsView(APIView):
    @extend_schema(
        responses=OtdrAlertSerializer(many=True),
        summary="Pontos de rompimento OTDR fixados no mapa (ativos)",
    )
    def get(self, request: Request) -> Response:
        return Response(active_alerts())

    @extend_schema(
        request=OtdrPinSerializer,
        responses={201: OtdrAlertSerializer},
        summary="Fixa no mapa, para toda a equipa, o ponto OTDR (recalculado no servidor)",
    )
    def post(self, request: Request) -> Response:
        body = OtdrPinSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        v = body.validated_data
        try:
            data = pin_alert(
                v["cable_id"],
                direction=v["direction"],
                distance_m=v["distance_m"],
                slack_pct=v["slack_pct"],
                note=v["note"],
                user=request.user,
                distance_b_m=v.get("distance_b_m"),
                offset_m=v["offset_m"],
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class OtdrAlertClearView(APIView):
    @extend_schema(
        request=None,
        responses=OtdrAlertClearedSerializer,
        summary="Limpa o ponto OTDR do mapa (após o reparo)",
    )
    def post(self, request: Request, alert_id: int) -> Response:
        return Response(clear_alert(alert_id, user=request.user))


class OtdrAlertDetailView(APIView):
    @extend_schema(
        request=OtdrAdjustSerializer,
        responses=OtdrAlertSerializer,
        summary="Ajuste fino de um ponto OTDR fixado (grava para toda a equipa, com registo)",
    )
    def patch(self, request: Request, alert_id: int) -> Response:
        body = OtdrAdjustSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            data = adjust_alert(
                alert_id, offset_m=body.validated_data["offset_m"], user=request.user
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data)

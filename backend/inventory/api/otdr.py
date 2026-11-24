"""``GET /api/v1/inventory/cables/<id>/otdr-locate/`` (EV-0127)."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.usecases.devices_common import InventoryValidationError
from inventory.usecases.otdr import DIRECTIONS, SLACK_PCT_MAX, locate_otdr


class OtdrQuerySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=list(DIRECTIONS))
    distance_m = serializers.FloatField(min_value=1)
    slack_pct = serializers.FloatField(min_value=0, max_value=SLACK_PCT_MAX, default=0)


class OtdrSiteSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    distance_m = serializers.FloatField()


class OtdrResultSerializer(serializers.Serializer):
    cable_id = serializers.IntegerField()
    cable_name = serializers.CharField()
    direction = serializers.CharField()
    otdr_m = serializers.FloatField()
    slack_pct = serializers.FloatField()
    map_distance_m = serializers.FloatField()
    path_length_m = serializers.FloatField()
    inventory_length_km = serializers.FloatField(allow_null=True)
    origin = OtdrSiteSerializer()
    target = OtdrSiteSerializer()
    point = serializers.ListField(child=serializers.FloatField(), help_text="[lng, lat]")
    segment = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    tolerance_m = serializers.FloatField()


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
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data)

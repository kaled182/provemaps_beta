"""``GET /api/v1/monitoring/switches/`` (EV-0115)."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import usecases
from .serializers import SwitchesOverviewSerializer, SwitchesQuerySerializer


class SwitchesOverviewView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "refresh", bool, description="ignora a cache de 60 s (botão Atualizar)"
            )
        ],
        responses=SwitchesOverviewSerializer,
        summary="Switches Huawei: estado, portas (link, RX/TX, tráfego) e KPIs, do Zabbix",
    )
    def get(self, request: Request) -> Response:
        query = SwitchesQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(usecases.switches_overview(refresh=query.validated_data["refresh"]))

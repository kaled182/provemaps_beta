"""API do Monitoramento GPON: ``/api/v1/monitoring/gpon/`` (EV-0095). Views finas.

Autenticação e permissão vêm do ``REST_FRAMEWORK`` (sessão ou token de conta de serviço;
``IsAuthenticated``). O resumo lê só a base e a cache — nenhuma chamada ao Zabbix no pedido.
"""

from __future__ import annotations

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Device

from . import usecases
from .serializers import (
    GponOverviewQuerySerializer,
    GponOverviewSerializer,
    OnuHistoryQuerySerializer,
    OnuHistorySerializer,
)


class GponOverviewView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("olt", int, description="device_id de uma OLT (opcional)")],
        responses=GponOverviewSerializer,
        summary="Estado das OLT, PONs e ONUs (última coleta gravada)",
    )
    def get(self, request: Request) -> Response:
        query = GponOverviewQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            data = usecases.gpon_overview(olt_id=query.validated_data.get("olt"))
        except Device.DoesNotExist as exc:
            raise Http404(str(exc)) from exc
        return Response(data)


class OnuHistoryView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter("hours", int, description="1..168 (padrão 24)")],
        responses=OnuHistorySerializer,
        summary="Histórico do RX de uma ONU (Zabbix)",
    )
    def get(self, request: Request, pk: int) -> Response:
        query = OnuHistoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(usecases.onu_history(pk, query.validated_data["hours"]))

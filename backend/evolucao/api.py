"""API da Central de Evolução: `/api/v1/evolucao/` (ADR 0006 §4.2).

Criar e ver não se gateiam além da autenticação — um botão «Reportar» que dá 403 ensina a não
carregar nele. Triar exige `is_staff` e fica em `ConfigurationAudit`.
"""

from __future__ import annotations

import json

from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from setup_app.models_audit import ConfigurationAudit

from . import usecases as uc
from .models import EvolucaoAnexo
from .serializers import (
    AnexoSerializer,
    EtiquetasSerializer,
    ItemCreateSerializer,
    ItemSerializer,
    ItemTriagemSerializer,
)

SECCAO_AUDITORIA = "Evolução"


def _erro(exc: uc.EvolucaoError) -> Response:
    return Response({"detail": str(exc)}, status=exc.status)


class ItemListCreateView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("estado", str, description="entrada|aceite|a_fazer|feito|recusado"),
            OpenApiParameter("tipo", str, description="problema|ideia"),
        ],
        responses=ItemSerializer(many=True),
        summary="Lista os itens (staff vê tudo; os outros, os seus)",
    )
    def get(self, request: Request) -> Response:
        itens = uc.listar_itens(
            request.user,
            estado=request.query_params.get("estado") or None,
            tipo=request.query_params.get("tipo") or None,
        )
        return Response(ItemSerializer(itens, many=True).data)

    @extend_schema(
        request=ItemCreateSerializer,
        responses={201: ItemSerializer},
        summary="Reporta um problema ou ideia (nasce em `entrada`)",
    )
    def post(self, request: Request) -> Response:
        ser = ItemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        contexto = dict(d.get("contexto") or {})
        contexto.setdefault(
            "request_id",
            getattr(request, "request_id", None) or request.META.get("HTTP_X_REQUEST_ID", ""),
        )
        try:
            item = uc.criar_item(
                autor=request.user,
                tipo=d["tipo"],
                titulo=d["titulo"],
                descricao=d["descricao"],
                impacto=d.get("impacto", ""),
                contexto=contexto,
                anexos=d.get("anexos"),
            )
        except uc.EvolucaoError as exc:
            return _erro(exc)
        return Response(
            ItemSerializer(uc.serialize_item(item)).data, status=status.HTTP_201_CREATED
        )


class ItemDetailView(APIView):
    @extend_schema(responses=ItemSerializer, summary="Um item (autor ou staff)")
    def get(self, request: Request, pk: int) -> Response:
        try:
            item = uc.obter_item(pk)
        except uc.EvolucaoError as exc:
            return _erro(exc)
        if not uc.pode_ver(request.user, item):
            return Response({"detail": "Item não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ItemSerializer(uc.serialize_item(item)).data)

    @extend_schema(
        request=ItemTriagemSerializer,
        responses=ItemSerializer,
        summary="Triagem (só staff): estado, tipo, prioridade, etiquetas, recusa",
    )
    def patch(self, request: Request, pk: int) -> Response:
        if not uc.pode_triar(request.user):
            return Response({"detail": "Só staff tria."}, status=status.HTTP_403_FORBIDDEN)
        ser = ItemTriagemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            item = uc.obter_item(pk)
            mudancas = uc.triar(
                item,
                estado=d.get("estado"),
                tipo=d.get("tipo"),
                prioridade=d["prioridade"] if "prioridade" in d else uc.NAO_MEXER,
                etiquetas=d.get("etiquetas"),
                recusa_motivo=d.get("recusa_motivo"),
            )
        except uc.EvolucaoError as exc:
            return _erro(exc)
        if mudancas:
            ConfigurationAudit.log_change(
                user=request.user,
                action="update",
                section=SECCAO_AUDITORIA,
                field_name=item.codigo,
                new_value=json.dumps(mudancas, ensure_ascii=False, default=str)[:2000],
                request=request._request,
            )
        return Response(ItemSerializer(uc.serialize_item(item)).data)


class EtiquetasView(APIView):
    @extend_schema(responses=EtiquetasSerializer, summary="Etiquetas já em uso")
    def get(self, request: Request) -> Response:
        return Response({"etiquetas": uc.etiquetas_em_uso()})


class AnexoUploadView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
            }
        },
        responses={201: AnexoSerializer},
        summary="Carrega um anexo; o id entra em `anexos` do POST /itens/",
    )
    def post(self, request: Request) -> Response:
        ficheiro = request.FILES.get("file")
        if ficheiro is None:
            return Response({"detail": "Envie o ficheiro no campo `file`."}, status=400)
        anexo = uc.criar_anexo(ficheiro=ficheiro, user=request.user)
        return Response(
            AnexoSerializer(uc.serialize_anexo(anexo)).data, status=status.HTTP_201_CREATED
        )


class AnexoDownloadView(APIView):
    @extend_schema(
        responses={200: {"type": "string", "format": "binary"}}, summary="Descarrega um anexo"
    )
    def get(self, request: Request, pk: int):
        anexo = EvolucaoAnexo.objects.select_related("item", "item__autor").filter(pk=pk).first()
        if anexo is None:
            return Response({"detail": "Anexo não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        visivel = (
            uc.pode_ver(request.user, anexo.item)
            if anexo.item_id
            else (uc.pode_triar(request.user) or anexo.carregado_por_id == request.user.pk)
        )
        if not visivel:
            return Response({"detail": "Anexo não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            anexo.ficheiro.open("rb"),
            content_type=anexo.content_type or "application/octet-stream",
            as_attachment=False,
            filename=anexo.nome_original,
        )

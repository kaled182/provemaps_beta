"""CTOs e postes do Projeto de Rede (EV-0139). Leitura: autenticado; escrita: staff.

- ``GET|POST /api/v1/inventory/ctos/`` · ``PATCH|DELETE /ctos/<id>/``
- ``GET|POST /api/v1/inventory/poles/`` · ``PATCH|DELETE /poles/<id>/``
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.permissions import StaffWritePermission
from inventory.usecases import design_points as uc
from inventory.usecases.devices_common import InventoryValidationError


class _Point(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class CtoCreateSerializer(_Point):
    name = serializers.CharField(max_length=100)
    capacity = serializers.IntegerField(required=False, allow_null=True)
    cable_id = serializers.IntegerField(required=False, allow_null=True)


class CtoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    point = serializers.ListField(child=serializers.FloatField(), help_text="[lng, lat]")
    cable_id = serializers.IntegerField(allow_null=True)
    cable_name = serializers.CharField(allow_null=True)
    km = serializers.FloatField(allow_null=True)
    capacity = serializers.IntegerField(allow_null=True)


class PoleCreateSerializer(_Point):
    name = serializers.CharField(max_length=60)
    owner = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    height_m = serializers.FloatField(required=False, allow_null=True)


class PoleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    point = serializers.ListField(child=serializers.FloatField(), help_text="[lng, lat]")
    owner = serializers.CharField()
    height_m = serializers.FloatField(allow_null=True)


def _run(fn, *args, status=200, **kwargs) -> Response:
    try:
        data = fn(*args, **kwargs)
    except InventoryValidationError as exc:
        return Response({"detail": str(exc)}, status=400)
    return Response(data, status=status) if data is not None else Response(status=204)


class CtosView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(responses=CtoSerializer(many=True), summary="CTOs do Projeto de Rede")
    def get(self, request: Request) -> Response:
        return Response(uc.list_ctos())

    @extend_schema(
        request=CtoCreateSerializer,
        responses={201: CtoSerializer},
        summary="Insere uma CTO (sobre um cabo ou solta)",
    )
    def post(self, request: Request) -> Response:
        body = CtoCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return _run(uc.create_cto, status=201, **body.validated_data)


class CtoDetailView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(request=_Point, responses=CtoSerializer, summary="Move a CTO")
    def patch(self, request: Request, cto_id: int) -> Response:
        body = _Point(data=request.data)
        body.is_valid(raise_exception=True)
        return _run(uc.move_cto, cto_id, **body.validated_data)

    @extend_schema(responses={204: None}, summary="Exclui a CTO (sem fusões)")
    def delete(self, request: Request, cto_id: int) -> Response:
        return _run(uc.delete_cto, cto_id)


class PolesView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(responses=PoleSerializer(many=True), summary="Postes do Projeto de Rede")
    def get(self, request: Request) -> Response:
        return Response(uc.list_poles())

    @extend_schema(
        request=PoleCreateSerializer, responses={201: PoleSerializer}, summary="Insere um poste"
    )
    def post(self, request: Request) -> Response:
        body = PoleCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return _run(uc.create_pole, status=201, **body.validated_data)


class PoleDetailView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(request=_Point, responses=PoleSerializer, summary="Move o poste")
    def patch(self, request: Request, pole_id: int) -> Response:
        body = _Point(data=request.data)
        body.is_valid(raise_exception=True)
        return _run(uc.move_pole, pole_id, **body.validated_data)

    @extend_schema(responses={204: None}, summary="Exclui o poste")
    def delete(self, request: Request, pole_id: int) -> Response:
        return _run(uc.delete_pole, pole_id)

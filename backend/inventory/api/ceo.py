"""CEO no traçado e cabos derivados (EV-0135).

- ``GET|POST /api/v1/inventory/ceos/`` — lista | insere no traçado de um cabo
- ``POST /api/v1/inventory/ceos/<id>/derive/`` — cria um cabo que nasce na CEO
- ``GET /api/v1/inventory/ceos/site-ports/?site=<id>`` — portas do site de destino
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Site
from inventory.permissions import StaffWritePermission
from inventory.usecases.ceo import (
    MODES,
    create_ceo,
    create_slack,
    delete_ceo,
    delete_slack,
    derive_cable,
    list_ceos,
    list_slacks,
    move_ceo,
)
from inventory.usecases.ceo_fusions import (
    ceo_fusions,
    create_fusion,
    create_splitter,
    delete_fusion,
    delete_splitter,
    fuse_tubes,
    trace_light,
    update_splitter,
    update_splitter_port,
)
from inventory.usecases.devices_common import InventoryValidationError
from inventory.usecases.strand_ports import site_ports
from inventory.usecases.trace_tree import trace_tree


class CeoCreateSerializer(serializers.Serializer):
    cable_id = serializers.IntegerField(min_value=1)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    name = serializers.CharField(max_length=100)
    mode = serializers.ChoiceField(choices=list(MODES), default="sangria")
    slack_m = serializers.FloatField(required=False, allow_null=True, min_value=0)
    trays = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=96)


class CeoDerivedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class CeoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    cable_id = serializers.IntegerField(allow_null=True)
    cable_name = serializers.CharField(allow_null=True)
    point = serializers.ListField(child=serializers.FloatField(), help_text="[lng, lat]")
    km = serializers.FloatField()
    mode = serializers.CharField()
    mode_label = serializers.CharField()
    slack_m = serializers.FloatField(allow_null=True)
    trays = serializers.IntegerField(allow_null=True)
    derived = CeoDerivedSerializer(many=True)


class PathPointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class CeoDeriveSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    path = PathPointSerializer(many=True)
    cable_group_id = serializers.IntegerField(required=False, allow_null=True)
    to_site_id = serializers.IntegerField(required=False, allow_null=True)
    to_port_id = serializers.IntegerField(required=False, allow_null=True)
    to_ceo_id = serializers.IntegerField(required=False, allow_null=True)


class CeoDeriveResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    length_km = serializers.FloatField()
    origin_ceo = CeoSerializer()
    needs_profile = serializers.BooleanField()


class CeosView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        responses=CeoSerializer(many=True), summary="CEOs (caixas de emenda) nos traçados"
    )
    def get(self, request: Request) -> Response:
        return Response(list_ceos())

    @extend_schema(
        request=CeoCreateSerializer,
        responses={201: CeoSerializer},
        summary="Insere uma CEO no traçado de um cabo (ponto projetado no traçado)",
    )
    def post(self, request: Request) -> Response:
        body = CeoCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        v = body.validated_data
        try:
            data = create_ceo(
                v["cable_id"],
                lat=v["lat"],
                lng=v["lng"],
                name=v["name"],
                mode=v["mode"],
                slack_m=v.get("slack_m"),
                trays=v.get("trays"),
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class CeoDeriveView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=CeoDeriveSerializer,
        responses={201: CeoDeriveResultSerializer},
        summary="Cria um cabo derivado que nasce na CEO",
    )
    def post(self, request: Request, ceo_id: int) -> Response:
        body = CeoDeriveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        v = body.validated_data
        try:
            data = derive_cable(
                ceo_id,
                name=v["name"],
                path=v["path"],
                cable_group_id=v.get("cable_group_id"),
                to_site_id=v.get("to_site_id"),
                to_port_id=v.get("to_port_id"),
                to_ceo_id=v.get("to_ceo_id"),
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class SitePortsView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        responses=serializers.DictField(),
        summary="Equipamentos e portas de um site (destino de um cabo derivado)",
    )
    def get(self, request: Request) -> Response:
        site_id = request.query_params.get("site")
        if not site_id or not str(site_id).isdigit():
            return Response({"detail": "indique ?site=<id>"}, status=400)
        return Response(site_ports(get_object_or_404(Site, pk=int(site_id))))


class FusionEndSerializer(serializers.Serializer):
    strand_id = serializers.IntegerField(min_value=1)
    side = serializers.ChoiceField(choices=["a", "b", ""], required=False, default="")


class FusionCreateSerializer(serializers.Serializer):
    a = FusionEndSerializer()
    b = FusionEndSerializer()
    tray = serializers.IntegerField(required=False, allow_null=True)
    slot = serializers.IntegerField(required=False, allow_null=True)


class CeoFusionsView(APIView):
    """EV-0136: pontas de fibra da CEO e as fusões (GET); criar fusão (POST)."""

    permission_classes = [StaffWritePermission]

    @extend_schema(responses=serializers.DictField(), summary="Pontas de fibra e fusões da CEO")
    def get(self, request: Request, ceo_id: int) -> Response:
        return Response(ceo_fusions(ceo_id))

    @extend_schema(
        request=FusionCreateSerializer,
        responses={201: serializers.DictField()},
        summary="Cria uma fusão fibra A ↔ fibra B na CEO",
    )
    def post(self, request: Request, ceo_id: int) -> Response:
        body = FusionCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        v = body.validated_data
        try:
            data = create_fusion(ceo_id, a=v["a"], b=v["b"], tray=v.get("tray"), slot=v.get("slot"))
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class CeoFusionDeleteView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(responses={204: None}, summary="Desfaz uma fusão da CEO")
    def delete(self, request: Request, ceo_id: int, fusion_id: int) -> Response:
        delete_fusion(ceo_id, fusion_id)
        return Response(status=204)


class StrandTraceView(APIView):
    """EV-0136: rastreamento da luz a partir de uma ponta da fibra."""

    permission_classes = [StaffWritePermission]

    @extend_schema(
        parameters=[OpenApiParameter("from", str, enum=["a", "b"], description="ponta de partida")],
        responses=serializers.DictField(),
        summary="Rastreia a luz pela fibra, cabos e CEOs até uma porta",
    )
    def get(self, request: Request, strand_id: int) -> Response:
        try:
            return Response(trace_light(strand_id, start=request.query_params.get("from", "a")))
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)


class StrandTraceTreeView(APIView):
    """EV-0143: rastreamento em árvore — fonte, ramos dos splitters, km/dBm e geometria."""

    permission_classes = [StaffWritePermission]

    @extend_schema(
        parameters=[OpenApiParameter("from", str, enum=["a", "b"], description="ponta de partida")],
        responses=serializers.DictField(),
        summary="Rastreia da OLT/switch até cada destino, com os ramos dos splitters",
    )
    def get(self, request: Request, strand_id: int) -> Response:
        try:
            return Response(trace_tree(strand_id, start=request.query_params.get("from", "a")))
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class CeoDetailView(APIView):
    """EV-0138: mover (PATCH {lat, lng}, reprojetado no traçado) ou excluir (vazia) a CEO."""

    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=PointSerializer, responses=CeoSerializer, summary="Move a CEO no traçado"
    )
    def patch(self, request: Request, ceo_id: int) -> Response:
        body = PointSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            return Response(move_ceo(ceo_id, **body.validated_data))
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

    @extend_schema(responses={204: None}, summary="Exclui a CEO (só vazia)")
    def delete(self, request: Request, ceo_id: int) -> Response:
        try:
            delete_ceo(ceo_id)
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


class SlackCreateSerializer(PointSerializer):
    cable_id = serializers.IntegerField(min_value=1)
    meters = serializers.FloatField(min_value=0.1, max_value=5000)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class SlacksView(APIView):
    """EV-0138: reservas técnicas nos traçados."""

    permission_classes = [StaffWritePermission]

    @extend_schema(responses=serializers.DictField(), summary="Reservas técnicas nos traçados")
    def get(self, request: Request) -> Response:
        return Response(list_slacks())

    @extend_schema(
        request=SlackCreateSerializer,
        responses={201: serializers.DictField()},
        summary="Insere reserva técnica no traçado",
    )
    def post(self, request: Request) -> Response:
        body = SlackCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        v = body.validated_data
        try:
            data = create_slack(
                v["cable_id"], lat=v["lat"], lng=v["lng"], meters=v["meters"], name=v["name"]
            )
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class SlackDetailView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=PointSerializer, responses=serializers.DictField(), summary="Move a reserva técnica"
    )
    def patch(self, request: Request, slack_id: int) -> Response:
        body = PointSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            return Response(move_ceo(slack_id, **body.validated_data))
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

    @extend_schema(responses={204: None}, summary="Exclui a reserva técnica")
    def delete(self, request: Request, slack_id: int) -> Response:
        delete_slack(slack_id)
        return Response(status=204)


class TubeEndSerializer(serializers.Serializer):
    cable_id = serializers.IntegerField(min_value=1)
    tube_number = serializers.IntegerField(min_value=1)
    side = serializers.ChoiceField(choices=["a", "b", ""], required=False, default="")


class TubeFusionSerializer(serializers.Serializer):
    a = TubeEndSerializer()
    b = TubeEndSerializer()


class CeoTubeFusionView(APIView):
    """EV-0141: «Fusionar tubo 1:1» — fibra n ↔ fibra n, cor com cor."""

    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=TubeFusionSerializer,
        responses={201: serializers.DictField()},
        summary="Funde um tubo inteiro com outro, fibra a fibra (cor com cor)",
    )
    def post(self, request: Request, ceo_id: int) -> Response:
        body = TubeFusionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            data = fuse_tubes(ceo_id, **body.validated_data)
        except InventoryValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data, status=201)


class SplitterCreateSerializer(serializers.Serializer):
    ratio = serializers.ChoiceField(choices=["1x2", "1x4", "1x8", "1x16", "1x32"])
    name = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")


class SplitterUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60, required=False, allow_blank=True)
    input = FusionEndSerializer(required=False, allow_null=True)


class SplitterPortSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["livre", "reservada", "ocupada", "bloqueada"], required=False
    )
    customer = serializers.CharField(max_length=120, required=False, allow_blank=True)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True)
    output = FusionEndSerializer(required=False, allow_null=True)


def _run(fn, *args, http_status=200, **kwargs) -> Response:
    # `http_status`, não `status`: o PATCH da porta tem um campo `status` (livre/reservada/…)
    try:
        data = fn(*args, **kwargs)
    except InventoryValidationError as exc:
        return Response({"detail": str(exc)}, status=400)
    return Response(data, status=http_status) if data is not None else Response(status=204)


class SplittersView(APIView):
    """EV-0142: splitters na bandeja da CEO/CTO."""

    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=SplitterCreateSerializer,
        responses={201: serializers.DictField()},
        summary="Acrescenta um splitter à caixa (cria as portas)",
    )
    def post(self, request: Request, ceo_id: int) -> Response:
        body = SplitterCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return _run(create_splitter, ceo_id, http_status=201, **body.validated_data)


class SplitterDetailView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=SplitterUpdateSerializer,
        responses=serializers.DictField(),
        summary="Renomeia o splitter ou liga/desliga a fibra de entrada",
    )
    def patch(self, request: Request, ceo_id: int, splitter_id: int) -> Response:
        body = SplitterUpdateSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        return _run(update_splitter, ceo_id, splitter_id, **body.validated_data)

    @extend_schema(responses={204: None}, summary="Remove o splitter")
    def delete(self, request: Request, ceo_id: int, splitter_id: int) -> Response:
        return _run(delete_splitter, ceo_id, splitter_id)


class SplitterPortView(APIView):
    permission_classes = [StaffWritePermission]

    @extend_schema(
        request=SplitterPortSerializer,
        responses=serializers.DictField(),
        summary="Estado da porta (livre/reservada/ocupada/bloqueada), cliente e fibra de saída",
    )
    def patch(self, request: Request, ceo_id: int, splitter_id: int, number: int) -> Response:
        body = SplitterPortSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        return _run(update_splitter_port, ceo_id, splitter_id, number, **body.validated_data)

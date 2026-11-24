"""Caixas de emenda (CEO) no traçado de um cabo e cabos derivados (EV-0135).

Uma CEO é uma ``FiberInfrastructure`` de tipo ``splice_box`` sobre o traçado de um cabo:
ponto projetado no traçado (PostGIS), km desde a origem, reserva técnica, bandejas e o modo:

- ``sangria`` (passagem direta): o cabo atravessa a caixa sem ser cortado; só as fibras
  escolhidas são sangradas e emendadas ao derivado;
- ``corte`` (emenda total): o cabo é cortado na caixa — todas as fibras podem ser emendadas.

O cabo continua a ser um só no inventário nos dois modos (decisão do Paulo); o modo decide
que fusões a CEO aceita (EV-0136). Um cabo derivado nasce na CEO (``origin_infrastructure``)
e termina num site/porta ou noutra CEO.
"""

from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from django.db import connection, transaction
from django.shortcuts import get_object_or_404

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.domain.geometry import calculate_path_length, sanitize_path_points
from inventory.models import CableGroup, FiberCable, FiberInfrastructure, Port, Site
from inventory.spatial import coords_to_linestring
from maps_view.cache_swr import invalidate_dashboard_cache

from .cable_structure import ensure_cable_structure
from .devices_common import InventoryValidationError

MODES = {"sangria": "Sangria (passagem direta)", "corte": "Corte / emenda total"}
CEO_TYPE = "splice_box"


def _project(cable: FiberCable, lat: float, lng: float) -> tuple[Point, float]:
    """Ponto do traçado mais próximo do clique e a distância (m) desde o início do traçado."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ST_X(cp), ST_Y(cp), ST_LineLocatePoint(path, cp) * ST_Length(path::geography)
            FROM (
                SELECT path, ST_ClosestPoint(path, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS cp
                FROM zabbix_api_fibercable WHERE id = %s
            ) q
            """,
            [lng, lat, cable.pk],
        )
        x, y, along = cursor.fetchone()
    return Point(float(x), float(y), srid=4326), float(along)


def ceo_payload(ceo: FiberInfrastructure) -> dict[str, Any]:
    meta = ceo.metadata or {}
    return {
        "id": ceo.pk,
        "name": ceo.name or f"CEO #{ceo.pk}",
        "cable_id": ceo.cable_id,
        "cable_name": ceo.cable.name if ceo.cable_id else None,
        "point": [round(ceo.location.x, 7), round(ceo.location.y, 7)],
        "km": round((ceo.distance_from_origin or 0) / 1000, 3),
        "mode": meta.get("mode") or "sangria",
        "mode_label": MODES.get(meta.get("mode") or "sangria"),
        "slack_m": meta.get("slack_m"),
        "trays": ceo.installed_trays,
        "derived": [
            {"id": c.pk, "name": c.name}
            for c in list(ceo.derived_cables.all()) + list(ceo.arriving_cables.all())
        ],
    }


def list_ceos() -> list[dict[str, Any]]:
    qs = (
        FiberInfrastructure.objects.filter(type=CEO_TYPE)
        .select_related("cable")
        .prefetch_related("derived_cables", "arriving_cables")
        .order_by("name", "id")
    )
    return [ceo_payload(c) for c in qs]


def create_ceo(
    cable_id: int,
    *,
    lat: float,
    lng: float,
    name: str,
    mode: str = "sangria",
    slack_m: float | None = None,
    trays: int | None = None,
) -> dict[str, Any]:
    """Insere a CEO no traçado do cabo, no ponto do traçado mais próximo do clique."""
    if mode not in MODES:
        raise InventoryValidationError("modo deve ser «sangria» ou «corte»")
    name = (name or "").strip()
    if not name:
        raise InventoryValidationError("indique o nome/código da CEO (ex.: CEO-04)")
    if slack_m is not None and slack_m < 0:
        raise InventoryValidationError("a reserva técnica não pode ser negativa")
    if trays is not None and not 0 < trays <= 96:
        raise InventoryValidationError("bandejas entre 1 e 96")
    cable = get_object_or_404(FiberCable, pk=cable_id)
    if cable.path is None or cable.path.num_points < 2:
        raise InventoryValidationError("o cabo não tem traçado no mapa")
    point, along = _project(cable, lat, lng)
    ceo = FiberInfrastructure.objects.create(
        cable=cable,
        type=CEO_TYPE,
        name=name[:100],
        location=point,
        distance_from_origin=along,
        # sem nº indicado fica o valor por omissão do modelo (o campo não aceita nulo)
        **({"installed_trays": trays} if trays is not None else {}),
        metadata={"mode": mode, "slack_m": slack_m},
    )
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    return ceo_payload(ceo)


def derive_cable(
    ceo_id: int,
    *,
    name: str,
    path: list[dict[str, Any]],
    cable_group_id: int | None = None,
    to_site_id: int | None = None,
    to_port_id: int | None = None,
    to_ceo_id: int | None = None,
) -> dict[str, Any]:
    """Cria um cabo que nasce na CEO e segue o traçado desenhado até um site/porta ou outra CEO."""
    ceo = get_object_or_404(
        FiberInfrastructure.objects.select_related("cable"), pk=ceo_id, type=CEO_TYPE
    )
    name = (name or "").strip()
    if not name:
        raise InventoryValidationError("indique o nome do cabo derivado")
    if FiberCable.objects.filter(name=name).exists():
        raise InventoryValidationError(f"já existe um cabo com o nome «{name}»")
    start = {"lat": ceo.location.y, "lng": ceo.location.x}
    drawn = list(path or [])
    if drawn and calculate_path_length([start, drawn[0]]) <= 0.001:
        drawn = drawn[1:]  # o 1.º ponto desenhado já é a CEO
    try:
        points = sanitize_path_points([start, *drawn], allow_empty=False)  # começa sempre na CEO
    except ValueError as exc:
        raise InventoryValidationError(
            "desenhe o traçado do cabo a partir da CEO (pelo menos 1 ponto)"
        ) from exc
    site_b = get_object_or_404(Site, pk=to_site_id) if to_site_id else None
    port_b = None
    if to_port_id:
        port_b = get_object_or_404(Port.objects.select_related("device"), pk=to_port_id)
        if site_b and port_b.device.site_id != site_b.pk:
            raise InventoryValidationError("a porta de destino não é de um equipamento desse site")
        site_b = site_b or port_b.device.site
    to_ceo = None
    if to_ceo_id:
        to_ceo = get_object_or_404(FiberInfrastructure, pk=to_ceo_id, type=CEO_TYPE)
        if to_ceo.pk == ceo.pk:
            raise InventoryValidationError("a CEO de destino tem de ser outra")
    group = get_object_or_404(CableGroup, pk=cable_group_id) if cable_group_id else None
    with transaction.atomic():
        cable = FiberCable.objects.create(
            name=name[:150],
            origin_infrastructure=ceo,
            destination_infrastructure=to_ceo,
            site_b=site_b,
            destination_port=port_b,
            path=coords_to_linestring(points),
            length_km=calculate_path_length(points),
            status=FiberCable.STATUS_UNKNOWN,
            cable_group=group,
        )
        structure = ensure_cable_structure(cable)
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    return {
        "id": cable.pk,
        "name": cable.name,
        "length_km": float(cable.length_km or 0),
        "origin_ceo": ceo_payload(ceo),
        "needs_profile": structure["needs_profile"],
    }

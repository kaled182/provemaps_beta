"""CTOs e postes no Projeto de Rede (EV-0139).

- CTO (caixa de atendimento): ``FiberInfrastructure`` do tipo ``splitter_box``; sobre um cabo
  (ponto projetado no traçado e km, como a CEO) ou solta (sem cabo). Portas: ``installed_trays``
  não serve — a capacidade fica em ``metadata.capacity`` (8/16/…); os splitters vêm no EV-0142.
- Poste: ``Pole`` (código, ponto, concessionária, altura).
"""

from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from django.shortcuts import get_object_or_404

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.models import FiberCable, FiberInfrastructure, Pole
from maps_view.cache_swr import invalidate_dashboard_cache

from .ceo import _project
from .devices_common import InventoryValidationError

CTO_TYPE = "splitter_box"
CTO_CAPACITIES = (2, 4, 8, 16, 24, 32)


def _invalidate() -> None:
    invalidate_fiber_cache()
    invalidate_dashboard_cache()


def _point(lat: float, lng: float) -> Point:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise InventoryValidationError("coordenadas fora do intervalo")
    return Point(float(lng), float(lat), srid=4326)


def cto_payload(cto: FiberInfrastructure) -> dict[str, Any]:
    meta = cto.metadata or {}
    return {
        "id": cto.pk,
        "name": cto.name or f"CTO #{cto.pk}",
        "point": [round(cto.location.x, 7), round(cto.location.y, 7)],
        "cable_id": cto.cable_id,
        "cable_name": cto.cable.name if cto.cable_id else None,
        "km": round((cto.distance_from_origin or 0) / 1000, 3) if cto.cable_id else None,
        "capacity": meta.get("capacity"),
    }


def list_ctos() -> list[dict[str, Any]]:
    qs = FiberInfrastructure.objects.filter(type=CTO_TYPE).select_related("cable")
    return [cto_payload(c) for c in qs.order_by("name", "id")]


def create_cto(
    *, lat: float, lng: float, name: str, capacity: int | None = None, cable_id: int | None = None
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise InventoryValidationError("indique o nome/código da CTO (ex.: CTO-12)")
    if capacity is not None and capacity not in CTO_CAPACITIES:
        raise InventoryValidationError(f"portas: {', '.join(map(str, CTO_CAPACITIES))}")
    cable = None
    point = _point(lat, lng)
    along = 0.0
    if cable_id:
        cable = get_object_or_404(FiberCable, pk=cable_id)
        if cable.path is None or cable.path.num_points < 2:
            raise InventoryValidationError("o cabo não tem traçado no mapa")
        point, along = _project(cable, lat, lng)
    cto = FiberInfrastructure.objects.create(
        cable=cable,
        type=CTO_TYPE,
        name=name[:100],
        location=point,
        distance_from_origin=along,
        metadata={"capacity": capacity},
    )
    _invalidate()
    return cto_payload(cto)


def move_cto(cto_id: int, *, lat: float, lng: float) -> dict[str, Any]:
    cto = get_object_or_404(
        FiberInfrastructure.objects.select_related("cable"), pk=cto_id, type=CTO_TYPE
    )
    if cto.cable is not None and cto.cable.path is not None:
        cto.location, cto.distance_from_origin = _project(cto.cable, lat, lng)
    else:
        cto.location = _point(lat, lng)
    cto.save(update_fields=["location", "distance_from_origin"])
    _invalidate()
    return cto_payload(cto)


def delete_cto(cto_id: int) -> None:
    cto = get_object_or_404(FiberInfrastructure, pk=cto_id, type=CTO_TYPE)
    if cto.fusions.exists():
        raise InventoryValidationError("a CTO tem fusões; desfaça-as antes de a excluir")
    cto.delete()
    _invalidate()


def pole_payload(pole: Pole) -> dict[str, Any]:
    return {
        "id": pole.pk,
        "name": pole.name,
        "point": [round(pole.location.x, 7), round(pole.location.y, 7)],
        "owner": pole.owner,
        "height_m": pole.height_m,
    }


def list_poles() -> list[dict[str, Any]]:
    return [pole_payload(p) for p in Pole.objects.all()]


def create_pole(
    *, lat: float, lng: float, name: str, owner: str = "", height_m: float | None = None
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise InventoryValidationError("indique o código do poste")
    if height_m is not None and not 0 < height_m <= 40:
        raise InventoryValidationError("altura entre 0 e 40 m")
    pole = Pole.objects.create(
        name=name[:60],
        location=_point(lat, lng),
        owner=(owner or "").strip()[:60],
        height_m=height_m,
    )
    return pole_payload(pole)


def move_pole(pole_id: int, *, lat: float, lng: float) -> dict[str, Any]:
    pole = get_object_or_404(Pole, pk=pole_id)
    pole.location = _point(lat, lng)
    pole.save(update_fields=["location"])
    return pole_payload(pole)


def delete_pole(pole_id: int) -> None:
    get_object_or_404(Pole, pk=pole_id).delete()

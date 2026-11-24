"""Localizador de rompimento OTDR (EV-0127): leitura do OTDR → ponto e trecho no traçado do cabo.

Só leitura — não grava nada (fixar o alerta no mapa é o EV-0128).
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404

from inventory.domain import otdr as geo
from inventory.models import FiberCable, Site

from .devices_common import InventoryValidationError

DIRECTIONS = ("ab", "ba")
SLACK_PCT_MAX = 20.0


def _site_of(cable: FiberCable, side: str) -> Site | None:
    site = getattr(cable, f"site_{side}", None)
    if site is not None:
        return site
    port = getattr(cable, "origin_port" if side == "a" else "destination_port", None)
    device = getattr(port, "device", None)
    return getattr(device, "site", None)


def _coord(site: Site | None) -> geo.Coord | None:
    if site is None or site.latitude is None or site.longitude is None:
        return None
    return (float(site.longitude), float(site.latitude))


def _site_payload(site: Site | None, along_m: float) -> dict[str, Any]:
    return {
        "id": getattr(site, "pk", None),
        "name": getattr(site, "display_name", None),
        "distance_m": round(along_m, 1),
    }


def locate_otdr(
    cable_id: int, *, direction: str, distance_m: float, slack_pct: float
) -> dict[str, Any]:
    """Ponto provável do rompimento a ``distance_m`` (leitura do OTDR) medidos a partir do site
    de origem do sentido escolhido, descontada a folga; trecho de ±40 m à volta.

    ``InventoryValidationError`` para sentido/folga inválidos, cabo sem traçado ou leitura que,
    descontada a folga, passa do fim do traçado.
    """
    if direction not in DIRECTIONS:
        raise InventoryValidationError("sentido deve ser «ab» ou «ba»")
    if not 0 <= slack_pct <= SLACK_PCT_MAX:
        raise InventoryValidationError(f"folga entre 0 e {SLACK_PCT_MAX:g} %")
    if distance_m <= 0:
        raise InventoryValidationError("a distância do OTDR tem de ser positiva")
    cable = get_object_or_404(
        FiberCable.objects.select_related(
            "site_a", "site_b", "origin_port__device__site", "destination_port__device__site"
        ),
        pk=cable_id,
    )
    if cable.path is None or cable.path.num_points < 2:
        raise InventoryValidationError("o cabo não tem traçado no mapa")

    site_a, site_b = _site_of(cable, "a"), _site_of(cable, "b")
    coords: list[geo.Coord] = [(float(x), float(y)) for x, y, *_ in cable.path.coords]
    if not geo.path_starts_at_a(coords, _coord(site_a), _coord(site_b)):
        coords.reverse()  # o traçado foi desenhado de B para A
    origin, target = (site_a, site_b) if direction == "ab" else (site_b, site_a)
    if direction == "ba":
        coords.reverse()

    acc = geo.cumulative_m(coords)
    total_m = acc[-1]
    map_m = distance_m / (1 + slack_pct / 100.0)
    if map_m > total_m:
        raise InventoryValidationError(
            f"a leitura, descontada a folga ({map_m / 1000:.2f} km), passa do fim do traçado "
            f"({total_m / 1000:.2f} km) — verificar o sentido, a folga ou o cabo"
        )
    lng, lat = geo.point_at(coords, acc, map_m)
    segment = geo.substring(coords, acc, map_m - geo.TOLERANCE_M, map_m + geo.TOLERANCE_M)
    return {
        "cable_id": cable.pk,
        "cable_name": cable.name,
        "direction": direction,
        "otdr_m": round(distance_m, 1),
        "slack_pct": slack_pct,
        "map_distance_m": round(map_m, 1),
        "path_length_m": round(total_m, 1),
        "inventory_length_km": float(cable.length_km) if cable.length_km is not None else None,
        "origin": _site_payload(origin, map_m),
        "target": _site_payload(target, total_m - map_m),
        "point": [round(lng, 7), round(lat, 7)],
        "segment": [[round(x, 7), round(y, 7)] for x, y in segment],
        "tolerance_m": geo.TOLERANCE_M,
    }

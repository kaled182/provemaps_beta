"""Localizador de rompimento OTDR (EV-0127): leitura do OTDR → ponto e trecho no traçado do cabo.

``locate_otdr`` só lê. Os alertas fixados para a equipa (EV-0128) recalculam o ponto no servidor
e guardam-no em ``OtdrAlert``.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from django.utils import timezone

from inventory.domain import otdr as geo
from inventory.models import FiberCable, OtdrAlert, Site

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


# ── EV-0128: alertas fixados no mapa (partilhados pela equipa) ────────────────
def _user_label(user: Any) -> str | None:
    if user is None:
        return None
    full = (user.get_full_name() or "").strip() if hasattr(user, "get_full_name") else ""
    return full or getattr(user, "username", None)


def alert_payload(alert: OtdrAlert) -> dict[str, Any]:
    return {
        "id": alert.pk,
        "cable_id": alert.cable_id,
        "note": alert.note,
        "created_by": _user_label(alert.created_by),
        "created_at": alert.created_at.isoformat().replace("+00:00", "Z"),
        "result": alert.result,
    }


def active_alerts() -> list[dict[str, Any]]:
    """Alertas ainda não limpos, do mais recente."""
    qs = OtdrAlert.objects.filter(cleared_at__isnull=True).select_related("created_by")
    return [alert_payload(a) for a in qs]


def pin_alert(
    cable_id: int, *, direction: str, distance_m: float, slack_pct: float, user: Any, note: str = ""
) -> dict[str, Any]:
    """Recalcula o ponto (mesmas validações do locate) e fixa-o para toda a equipa."""
    result = locate_otdr(cable_id, direction=direction, distance_m=distance_m, slack_pct=slack_pct)
    alert = OtdrAlert.objects.create(
        cable_id=cable_id,
        direction=direction,
        otdr_m=distance_m,
        slack_pct=slack_pct,
        result=result,
        note=note[:200],
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return alert_payload(alert)


def clear_alert(alert_id: int, *, user: Any) -> dict[str, Any]:
    """Limpa (após o reparo). Limpar um já limpo não faz nada."""
    alert = get_object_or_404(OtdrAlert, pk=alert_id)
    if alert.cleared_at is None:
        alert.cleared_at = timezone.now()
        alert.cleared_by = user if getattr(user, "is_authenticated", False) else None
        alert.save(update_fields=["cleared_at", "cleared_by"])
    return {"id": alert.pk, "cleared_at": alert.cleared_at.isoformat().replace("+00:00", "Z")}

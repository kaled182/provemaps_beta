"""Localizador de rompimento OTDR (EV-0127): leitura do OTDR → ponto e trecho no traçado do cabo.

``locate_otdr`` só lê. Os alertas fixados para a equipa (EV-0128) recalculam o ponto no servidor
e guardam-no em ``OtdrAlert``.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from django.utils import timezone

from inventory.domain import otdr as geo
from inventory.models import FiberCable, FiberInfrastructure, OtdrAlert, Site

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


INFRA_LABELS = dict(FiberInfrastructure.TYPES)


def _references(
    cable: FiberCable, coords: list[geo.Coord], acc: list[float], map_m: float
) -> dict[str, Any]:
    """EV-0130: caixas/reservas cadastradas no cabo imediatamente antes e depois do ponto,
    medidas sobre o traçado (no sentido da medição)."""
    rows = list(
        FiberInfrastructure.objects.filter(cable=cable).only("id", "type", "name", "location")
    )
    placed = sorted(
        ((geo.along_m(coords, acc, (r.location.x, r.location.y)), r) for r in rows),
        key=lambda x: x[0],
    )

    def item(along: float, row: FiberInfrastructure) -> dict[str, Any]:
        return {
            "id": row.pk,
            "type": row.type,
            "type_label": INFRA_LABELS.get(row.type, row.type),
            "name": row.name or None,
            "distance_m": round(abs(along - map_m), 1),
        }

    before = [(a, r) for a, r in placed if a <= map_m]
    after = [(a, r) for a, r in placed if a > map_m]
    return {
        "registered": len(rows),
        "before": item(*before[-1]) if before else None,
        "after": item(*after[0]) if after else None,
    }


def locate_otdr(
    cable_id: int,
    *,
    direction: str,
    distance_m: float,
    slack_pct: float,
    offset_m: float = 0.0,
    distance_b_m: float | None = None,
) -> dict[str, Any]:
    """Ponto provável do rompimento a ``distance_m`` (leitura do OTDR) medidos a partir do site
    de origem do sentido escolhido, descontada a folga; trecho de ±40 m à volta.

    EV-0131 — medição cruzada: com ``distance_b_m`` (leitura feita do Site B), ``distance_m`` é a
    leitura do Site A; a folga deixa de ser estimada e passa a ser a real do cabo,
    ``(A + B) / traçado - 1``, e o ponto fica na proporção ``A / (A + B)`` do traçado.

    ``InventoryValidationError`` para sentido/folga inválidos, cabo sem traçado ou leitura que,
    descontada a folga, passa do fim do traçado.
    """
    cross = distance_b_m is not None
    if cross:
        direction = "ab"
        if distance_b_m <= 0:
            raise InventoryValidationError("a leitura do Site B tem de ser positiva")
    if direction not in DIRECTIONS:
        raise InventoryValidationError("sentido deve ser «ab» ou «ba»")
    if not cross and not 0 <= slack_pct <= SLACK_PCT_MAX:
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
    warnings: list[str] = []
    cross_info: dict[str, Any] | None = None
    if cross:
        fiber_m = distance_m + float(distance_b_m)
        slack_pct = round((fiber_m / total_m - 1) * 100, 2)
        cross_info = {
            "reading_a_m": round(distance_m, 1),
            "reading_b_m": round(float(distance_b_m), 1),
            "fiber_length_m": round(fiber_m, 1),
            "slack_real_pct": slack_pct,
            "proportion": round(distance_m / fiber_m, 4),
        }
        if slack_pct < 0:
            warnings.append(
                "A soma das leituras é menor que o traçado do mapa: o traçado pode estar mais longo"
                " que a fibra real, ou as leituras não são do mesmo evento."
            )
        elif slack_pct > SLACK_PCT_MAX:
            warnings.append(
                f"Folga real de {slack_pct:.1f}% acima de {SLACK_PCT_MAX:g}%: confirmar as leituras"
                " e se o traçado do mapa está completo."
            )
        base_m = distance_m / fiber_m * total_m  # = A / (1 + folga real)
    else:
        base_m = distance_m / (1 + slack_pct / 100.0)
    if base_m > total_m:
        raise InventoryValidationError(
            f"a leitura, descontada a folga ({base_m / 1000:.2f} km), passa do fim do traçado "
            f"({total_m / 1000:.2f} km) — verificar o sentido, a folga ou o cabo"
        )
    # EV-0130: ajuste fino em campo — desloca o ponto sobre o traçado, sem sair das pontas
    map_m = min(max(base_m + offset_m, 0.0), total_m)
    lng, lat = geo.point_at(coords, acc, map_m)
    segment = geo.substring(coords, acc, map_m - geo.TOLERANCE_M, map_m + geo.TOLERANCE_M)
    return {
        "cable_id": cable.pk,
        "cable_name": cable.name,
        "direction": direction,
        "otdr_m": round(distance_m, 1),
        "slack_pct": slack_pct,
        "map_distance_m": round(map_m, 1),
        "base_map_distance_m": round(base_m, 1),
        "offset_m": round(map_m - base_m, 1),
        "path_length_m": round(total_m, 1),
        "inventory_length_km": float(cable.length_km) if cable.length_km is not None else None,
        "origin": _site_payload(origin, map_m),
        "target": _site_payload(target, total_m - map_m),
        "point": [round(lng, 7), round(lat, 7)],
        "segment": [[round(x, 7), round(y, 7)] for x, y in segment],
        "tolerance_m": geo.TOLERANCE_M,
        "references": _references(cable, coords, acc, map_m),
        "mode": "cross" if cross else "single",
        "cross": cross_info,
        "warnings": warnings,
    }


# ── EV-0128: alertas fixados no mapa (partilhados pela equipa) ────────────────
def _user_label(user: Any) -> str | None:
    if user is None:
        return None
    full = (user.get_full_name() or "").strip() if hasattr(user, "get_full_name") else ""
    return full or getattr(user, "username", None)


STATUS_LABELS = dict(OtdrAlert.STATUSES)


def _now_iso() -> str:
    return timezone.now().isoformat().replace("+00:00", "Z")


def alert_payload(alert: OtdrAlert) -> dict[str, Any]:
    return {
        "id": alert.pk,
        "cable_id": alert.cable_id,
        "note": alert.note,
        "created_by": _user_label(alert.created_by),
        "created_at": alert.created_at.isoformat().replace("+00:00", "Z"),
        "result": alert.result,
        "log": alert.log or [],
        "status": alert.status,
        "status_label": STATUS_LABELS.get(alert.status, alert.status),
        "cleared_at": (
            alert.cleared_at.isoformat().replace("+00:00", "Z") if alert.cleared_at else None
        ),
        "cleared_by": _user_label(alert.cleared_by),
    }


def active_alerts() -> list[dict[str, Any]]:
    """Alertas ainda não limpos, do mais recente."""
    qs = OtdrAlert.objects.filter(cleared_at__isnull=True).select_related(
        "created_by", "cleared_by"
    )
    return [alert_payload(a) for a in qs]


def cable_alert_history(cable_id: int) -> list[dict[str, Any]]:
    """EV-0132: todos os rompimentos OTDR do cabo (ativos e concluídos), do mais recente."""
    get_object_or_404(FiberCable.objects.only("id"), pk=cable_id)
    qs = OtdrAlert.objects.filter(cable_id=cable_id).select_related("created_by", "cleared_by")
    return [alert_payload(a) for a in qs]


def set_alert_status(alert_id: int, *, status: str, user: Any) -> dict[str, Any]:
    """EV-0132: muda o estado do atendimento (com registo). «done» conclui e tira o pino."""
    if status not in STATUS_LABELS:
        raise InventoryValidationError(f"estado deve ser um de: {', '.join(STATUS_LABELS)}")
    alert = get_object_or_404(OtdrAlert, pk=alert_id, cleared_at__isnull=True)
    if alert.status != status:
        alert.status = status
        entry = {"at": _now_iso(), "by": _user_label(user), "action": "status", "status": status}
        alert.log = [*(alert.log or []), entry]
        fields = ["status", "log"]
        if status == "done":
            alert.cleared_at = timezone.now()
            alert.cleared_by = user if getattr(user, "is_authenticated", False) else None
            fields += ["cleared_at", "cleared_by"]
        alert.save(update_fields=fields)
    return alert_payload(alert)


def pin_alert(
    cable_id: int,
    *,
    direction: str,
    distance_m: float,
    slack_pct: float,
    user: Any,
    note: str = "",
    distance_b_m: float | None = None,
    offset_m: float = 0.0,
) -> dict[str, Any]:
    """Recalcula o ponto (mesmas validações do locate) e fixa-o para toda a equipa."""
    result = locate_otdr(
        cable_id,
        direction=direction,
        distance_m=distance_m,
        slack_pct=slack_pct,
        distance_b_m=distance_b_m,
        offset_m=offset_m,
    )
    alert = OtdrAlert.objects.create(
        cable_id=cable_id,
        direction=result["direction"],
        otdr_m=distance_m,
        otdr_b_m=distance_b_m,
        offset_m=result["offset_m"],
        slack_pct=result["slack_pct"],
        result=result,
        note=note[:200],
        created_by=user if getattr(user, "is_authenticated", False) else None,
        log=[{"at": _now_iso(), "by": _user_label(user), "action": "pinned"}],
    )
    return alert_payload(alert)


def adjust_alert(alert_id: int, *, offset_m: float, user: Any) -> dict[str, Any]:
    """EV-0130: ajuste fino de um ponto fixado — recalcula no servidor com os parâmetros
    guardados e o novo deslocamento; fica para todos e no registo («+200 m por Ana»)."""
    alert = get_object_or_404(OtdrAlert, pk=alert_id, cleared_at__isnull=True)
    result = locate_otdr(
        alert.cable_id,
        direction=alert.direction,
        distance_m=alert.otdr_m,
        slack_pct=alert.slack_pct,
        offset_m=offset_m,
        distance_b_m=alert.otdr_b_m,
    )
    previous = float(alert.offset_m or 0)
    alert.offset_m = result["offset_m"]
    alert.result = result
    alert.log = [
        *(alert.log or []),
        {
            "at": _now_iso(),
            "by": _user_label(user),
            "action": "adjusted",
            "delta_m": round(alert.offset_m - previous, 1),
            "offset_m": alert.offset_m,
        },
    ]
    alert.save(update_fields=["offset_m", "result", "log"])
    return alert_payload(alert)


def clear_alert(alert_id: int, *, user: Any) -> dict[str, Any]:
    """Limpa (após o reparo). Limpar um já limpo não faz nada."""
    alert = get_object_or_404(OtdrAlert, pk=alert_id)
    if alert.cleared_at is None:
        alert.cleared_at = timezone.now()
        alert.cleared_by = user if getattr(user, "is_authenticated", False) else None
        alert.status = "done"
        alert.log = [
            *(alert.log or []),
            {"at": _now_iso(), "by": _user_label(user), "action": "cleared"},
        ]
        alert.save(update_fields=["cleared_at", "cleared_by", "status", "log"])
    return {"id": alert.pk, "cleared_at": alert.cleared_at.isoformat().replace("+00:00", "Z")}

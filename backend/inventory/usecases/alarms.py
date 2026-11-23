"""Quadro de alarmes de fibra (EV-0059), derivado do histórico `FiberEvent`.

Regra central: `unknown` é **ausência de informação**, não um estado. Não abre nem
fecha incidente — em produção ~80 % dos eventos são oscilação `unknown<->down` por
falha de coleta, e tratá-los como recuperação daria um MTTR falsamente baixo.

Um incidente abre quando o último estado conhecido passa de `up` para `degraded`
ou `down` (ou já está em baixo no início da janela) e fecha quando volta a `up`.
A severidade é a pior vista durante o incidente: `down` → crítico, `degraded` → atenção.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from inventory.models import FiberCable, FiberEvent
from inventory.usecases.fibers import list_cables_optical_summary

KNOWN_UP = "up"
KNOWN_DOWN = {"down": "critical", "degraded": "attention"}
SEVERITY_RANK = {"attention": 1, "critical": 2}
DEFAULT_WINDOW_DAYS = 30


def _incidents_for(
    events: list[tuple[datetime, str]], initial: tuple[datetime, str] | None
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Percorre as transições de um cabo e devolve (incidentes fechados, aberto|None)."""
    closed: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    stream = ([initial] if initial else []) + events
    for when, status in stream:
        if status == KNOWN_UP:
            if current is not None:
                current["closed_at"] = when
                closed.append(current)
                current = None
        elif status in KNOWN_DOWN:
            severity = KNOWN_DOWN[status]
            if current is None:
                current = {"opened_at": when, "severity": severity, "closed_at": None}
            elif SEVERITY_RANK[severity] > SEVERITY_RANK[current["severity"]]:
                current["severity"] = severity
        # qualquer outro valor (unknown, vazio) não muda nada
    return closed, current


def build_alarm_board(
    now: datetime | None = None, window_days: int = DEFAULT_WINDOW_DAYS
) -> dict[str, Any]:
    """Alarmes ativos, resolvidos nas últimas 24 h e MTTR na janela.

    Returns:
        {
          "active": [{cable_id, cable_name, severity, opened_at, duration_seconds,
                      rx, rx_side, center}],   # pior primeiro, depois o mais antigo
          "resolved_24h": int,
          "mttr_seconds": float | None,        # média dos fechados na janela
          "mttr_sample": int,
          "window_days": int,
          "generated_at": iso,
        }
    """
    now = now or timezone.now()
    start = now - timedelta(days=window_days)

    cables = {
        c.id: c for c in FiberCable.objects.filter(parent_cable__isnull=True).only("id", "name")
    }

    # Último estado CONHECIDO antes da janela (um por cabo) — estado inicial.
    initial: dict[int, tuple[datetime, str]] = {}
    before = (
        FiberEvent.objects.filter(timestamp__lt=start, fiber_id__in=cables.keys())
        .exclude(new_status__in=["", "unknown"])
        .order_by("fiber_id", "-timestamp")
        .distinct("fiber_id")
        .values_list("fiber_id", "timestamp", "new_status")
    )
    for fiber_id, ts, status in before:
        initial[fiber_id] = (ts, status)

    # Cabo já em baixo no início da janela: o incidente abriu no primeiro evento em
    # baixo depois do último `up` (não no limite da janela), com a pior severidade
    # desse período. São poucos cabos, uma consulta cada.
    for fiber_id, (_ts, status) in list(initial.items()):
        if status not in KNOWN_DOWN:
            continue
        last_up = (
            FiberEvent.objects.filter(fiber_id=fiber_id, new_status=KNOWN_UP, timestamp__lt=start)
            .order_by("-timestamp")
            .values_list("timestamp", flat=True)
            .first()
        )
        span = FiberEvent.objects.filter(
            fiber_id=fiber_id, new_status__in=list(KNOWN_DOWN), timestamp__lt=start
        )
        if last_up is not None:
            span = span.filter(timestamp__gt=last_up)
        opened = span.order_by("timestamp").values_list("timestamp", flat=True).first()
        worst = "down" if span.filter(new_status="down").exists() else "degraded"
        if opened is not None:
            initial[fiber_id] = (opened, worst)

    events: dict[int, list[tuple[datetime, str]]] = defaultdict(list)
    for fiber_id, ts, status in (
        FiberEvent.objects.filter(timestamp__gte=start, fiber_id__in=cables.keys())
        .order_by("timestamp")
        .values_list("fiber_id", "timestamp", "new_status")
    ):
        events[fiber_id].append((ts, status))

    optical = {c["id"]: c for c in list_cables_optical_summary()["cables"]}

    active: list[dict[str, Any]] = []
    durations: list[float] = []
    resolved_24h = 0
    day_ago = now - timedelta(hours=24)

    for cable_id, cable in cables.items():
        closed, open_incident = _incidents_for(events.get(cable_id, []), initial.get(cable_id))
        for inc in closed:
            if inc["closed_at"] >= start:
                durations.append((inc["closed_at"] - inc["opened_at"]).total_seconds())
            if inc["closed_at"] >= day_ago:
                resolved_24h += 1
        if open_incident is None:
            continue
        snap = optical.get(cable_id, {})
        rx, rx_side = None, None
        for side in ("origin", "destination"):
            end = snap.get(side) or {}
            if end.get("rx") is None or end.get("stale"):
                continue
            if rx is None or end["rx"] < rx:
                rx, rx_side = end["rx"], side
        active.append(
            {
                "cable_id": cable_id,
                "cable_name": cable.name,
                "severity": open_incident["severity"],
                "opened_at": open_incident["opened_at"].isoformat(),
                "duration_seconds": int((now - open_incident["opened_at"]).total_seconds()),
                "rx": rx,
                "rx_side": rx_side,
                "center": snap.get("center"),
            }
        )

    active.sort(key=lambda a: (-SEVERITY_RANK[a["severity"]], a["opened_at"]))
    return {
        "active": active,
        "resolved_24h": resolved_24h,
        "mttr_seconds": (sum(durations) / len(durations)) if durations else None,
        "mttr_sample": len(durations),
        "window_days": window_days,
        "generated_at": now.isoformat(),
    }

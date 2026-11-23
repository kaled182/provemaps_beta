"""Cabo ligado a uma porta, numa só consulta (EV-0071).

Uma porta está ligada a um cabo quando é o ``origin_port`` ou o ``destination_port``
dele. A lista de portas (``/api/v1/ports/``) precisa disso para o modal de
Dispositivo mostrar o cabo e o «Mapa de conectividade»; antes o serializer não o
devolvia e o frontend lia ``cable_id`` que nunca vinha.

Subconsulta correlacionada (não N+1): o mesmo número de consultas para 1 ou 240
portas. Se a porta estiver nas duas pontas de cabos diferentes, vence o de id menor.
"""

from __future__ import annotations

from django.db.models import OuterRef, Q, QuerySet, Subquery

from inventory.models import FiberCable, Port


def _cable_for_port() -> QuerySet[FiberCable]:
    return FiberCable.objects.filter(
        Q(origin_port=OuterRef("pk")) | Q(destination_port=OuterRef("pk"))
    ).order_by("id")


def annotate_connected_cable(queryset: QuerySet[Port]) -> QuerySet[Port]:
    """Acrescenta ``connected_cable_id`` e ``connected_cable_name`` a cada porta."""
    cable = _cable_for_port()
    return queryset.annotate(
        connected_cable_id=Subquery(cable.values("id")[:1]),
        connected_cable_name=Subquery(cable.values("name")[:1]),
    )

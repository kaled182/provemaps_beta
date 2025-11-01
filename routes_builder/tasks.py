"""Celery tasks wrapping routes_builder service operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from celery import shared_task

from routes_builder import services

logger = logging.getLogger(__name__)


# =============================================================================
# CELERY TASKS
# =============================================================================

@shared_task(bind=True, name="routes_builder.build_route")
def build_route(
    self,
    route_id: int,
    force: bool = False,
    options: Optional[Dict[str, Any]] = None,
):
    """Construir ou reconstruir uma rota individual usando o service layer."""

    logger.info("Task build_route iniciada para route_id=%s", route_id)
    payload_options = dict(options or {})

    context = services.RouteBuildContext(
        route_id=route_id,
        force=force,
        options=payload_options,
    )

    try:
        result = services.rebuild_route(context)
        response = {
            "status": "success",
            "route_id": result.route_id,
            "route_status": result.status,
            "segments_created": result.segments_created,
            "events_recorded": result.events_recorded,
            "metadata": result.metadata,
        }
        logger.info(
            "Task build_route concluída para route_id=%s status=%s",
            route_id,
            result.status,
        )
        return response
    except services.RouteServiceError as exc:
        logger.warning(
            "Task build_route falhou para route_id=%s: %s",
            route_id,
            exc,
        )
        return {
            "status": "error",
            "route_id": route_id,
            "message": str(exc),
        }


@shared_task(bind=True, name="routes_builder.build_routes_batch")
def build_routes_batch(
    self,
    route_ids: Iterable[int],
    force: bool = False,
    options: Optional[Dict[str, Any]] = None,
):
    """Processa múltiplas rotas, delegando ao serviço de batch rebuild."""

    route_ids_list = list(route_ids)
    logger.info(
        "Task build_routes_batch iniciada para %d rotas", len(route_ids_list)
    )

    shared_options = dict(options or {})
    contexts = [
        services.RouteBuildContext(
            route_id=route_id,
            force=force,
            options=shared_options,
        )
        for route_id in route_ids_list
    ]

    result = services.rebuild_routes_batch(contexts)

    processed_payload = [
        {
            "route_id": item.route_id,
            "route_status": item.status,
            "segments_created": item.segments_created,
            "events_recorded": item.events_recorded,
            "metadata": item.metadata,
        }
        for item in result.processed
    ]

    summary = {
        "status": "success",
        "processed": processed_payload,
        "failures": list(result.failures),
    }

    logger.info(
        "Task build_routes_batch concluída processed=%d failures=%d",
        len(processed_payload),
        len(result.failures),
    )

    return summary


@shared_task(bind=True, name="routes_builder.invalidate_route_cache")
def invalidate_route_cache(self, route_id: int):
    """Invalidar caches associados à rota informada."""

    logger.info(
        "Task invalidate_route_cache iniciada para route_id=%s", route_id
    )
    services.invalidate_route_cache(route_id)
    return {
        "status": "success",
        "route_id": route_id,
    }


@shared_task(bind=True, name="routes_builder.import_route_from_payload")
def import_route_from_payload(
    self,
    payload: Dict[str, Any],
    created_by: str = "routes_builder.task",
):
    """Importar ou atualizar uma rota a partir de um payload JSON-like."""

    logger.info(
        "Task import_route_from_payload iniciada created_by=%s", created_by
    )

    try:
        result = services.import_route_from_payload(
            payload,
            created_by=created_by,
        )
        return {
            "status": "success",
            "route_id": result.route_id,
            "route_status": result.status,
            "segments_created": result.segments_created,
            "events_recorded": result.events_recorded,
            "metadata": result.metadata,
        }
    except services.RouteServiceError as exc:
        logger.warning(
            "Task import_route_from_payload falhou: %s", exc
        )
        return {
            "status": "error",
            "message": str(exc),
        }


@shared_task(bind=True, name="routes_builder.health_check")
def health_check_routes_builder(self):
    """
    Health check do sistema de rotas.
    Útil para verificar se worker/fila estão funcionando.
    """
    logger.info("Task health_check_routes_builder executada")
    summary = services.health_summary()
    return {
        "status": "success",
        "summary": summary,
    }


"""Tarefa de coleta do estado das ONU (EV-0095) — agendada em ``core/celery.py`` (120 s)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task  # type: ignore[import-not-found]
from django.core.cache import cache
from django.utils import timezone

from . import usecases

logger = logging.getLogger(__name__)

COLLECT_LOCK_KEY = "gpon:collect:lock"
# Maior que o intervalo (120 s) e que uma coleta normal (9 item.get); se o worker morrer a meio,
# o lock expira sozinho.
COLLECT_LOCK_SECONDS = 300


@shared_task(name="gpon.tasks.collect_onu_states")
def collect_onu_states() -> dict[str, Any]:
    now = timezone.now()
    # Uma coleta de cada vez (padrão do EV-0063): execuções sobrepostas gravavam transições
    # duplicadas e ocupavam os workers da fila zabbix.
    if not cache.add(COLLECT_LOCK_KEY, now.isoformat(), COLLECT_LOCK_SECONDS):
        logger.info("gpon.collect_skipped_lock")
        return {"success": True, "skipped": "lock"}
    try:
        result = usecases.collect_onu_states(now=now)
    except Exception as exc:  # a tarefa nunca rebenta; o ecrã lê zabbix_ok
        logger.error("gpon.collect_failed", exc_info=True)
        message = str(exc) or exc.__class__.__name__
        cache.set(
            usecases.LAST_RUN_CACHE_KEY,
            {"collected_at": now.isoformat(), "zabbix_ok": False, "zabbix_error": message},
            usecases.LAST_RUN_CACHE_SECONDS,
        )
        return {"success": False, "zabbix_ok": False, "zabbix_error": message}
    finally:
        cache.delete(COLLECT_LOCK_KEY)
    logger.info(
        "gpon.collect_done",
        extra={
            "olts": result["olts"],
            "onus_seen": result["onus_seen"],
            "transitions": result["transitions"],
            "duration_ms": result["duration_ms"],
            "zabbix_ok": result["zabbix_ok"],
        },
    )
    return {"success": True, **result}

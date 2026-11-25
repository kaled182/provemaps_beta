"""
Celery tasks for inventory app.

Background tasks for inventory synchronization and maintenance.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from celery import shared_task  # type: ignore[import-not-found]
from django.core.cache import cache
from django.core.management import call_command
from django.db import models
from django.utils import timezone

from inventory.domain import optical as optical_domain
from inventory.models import Port

logger = logging.getLogger(__name__)

# EV-0063: uma coleta óptica de cada vez (a coleta mede-se em segundos; o lock
# expira sozinho se o worker morrer a meio).
OPTICAL_LOCK_KEY = "inventory:optical-levels:lock"
OPTICAL_LOCK_SECONDS = 300

fetch_port_optical_snapshot = optical_domain.fetch_port_optical_snapshot

# EV-0085: motivo gravado quando a chave da porta não existe (ou está desativada) no host.
OPTICAL_ITEM_MISSING = "item não existe no host"


@shared_task(
    name="inventory.sync_zabbix_inventory",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def sync_zabbix_inventory_task(
    self: Any, limit: int | None = None, host_filter: str | None = None, update_only: bool = False
) -> dict[str, Any]:
    """
    Background task to sync Zabbix inventory with local database.

    Args:
        limit: Limit number of hosts to sync
        host_filter: Filter hosts by name pattern
        update_only: Only update existing devices

    Returns:
        dict with sync results and statistics

    Raises:
        Exception: If sync fails (will trigger retry)
    """
    logger.info(
        f"Starting Zabbix inventory sync task "
        f"(limit={limit}, filter={host_filter}, update_only={update_only})"
    )

    try:
        # Call management command programmatically
        command_args = []
        command_kwargs = {}

        if limit:
            command_kwargs["limit"] = limit
        if host_filter:
            command_kwargs["host_filter"] = host_filter
        if update_only:
            command_kwargs["update_only"] = True

        # Capture output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            call_command(
                "sync_zabbix_inventory",
                *command_args,
                **command_kwargs,
            )
            output = captured_output.getvalue()
        finally:
            sys.stdout = old_stdout
        logger.info("Zabbix inventory sync completed successfully")

        return {
            "success": True,
            "output": output,
            "limit": limit,
            "host_filter": host_filter,
            "update_only": update_only,
        }

    except Exception as e:
        logger.exception(f"Zabbix inventory sync failed: {e}")
        # Retry the task
        raise self.retry(exc=e) from e


@shared_task(name="inventory.cleanup_orphaned_ports")
def cleanup_orphaned_ports_task() -> dict[str, int]:
    """
    Remove ports that reference devices no longer in Zabbix.

    This is a maintenance task that should run periodically.

    Returns:
        dict with cleanup statistics
    """
    from inventory.models import Device, Port

    logger.info("Starting orphaned ports cleanup")

    # Find devices without zabbix_hostid
    orphaned_devices = Device.objects.filter(zabbix_hostid="")
    orphaned_count = orphaned_devices.count()

    if orphaned_count > 0:
        logger.warning(f"Found {orphaned_count} devices without zabbix_hostid")

    # Count ports to be deleted
    ports_to_delete = Port.objects.filter(device__in=orphaned_devices)
    ports_count = ports_to_delete.count()

    if ports_count > 0:
        logger.info(f"Deleting {ports_count} orphaned port(s)")
        ports_to_delete.delete()

    result = {
        "orphaned_devices": orphaned_count,
        "ports_deleted": ports_count,
    }

    logger.info(f"Orphaned ports cleanup completed: {result}")
    return result


@shared_task(name="inventory.tasks.warm_port_optical_cache")
def warm_port_optical_cache(port_id: int) -> None:
    """Refresh the cached optical snapshot for a single port."""
    port = (
        Port.objects.select_related("device")
        .only(
            "id",
            "device_id",
            "device__zabbix_hostid",
            "rx_power_item_key",
            "tx_power_item_key",
        )
        .filter(id=port_id)
        .first()
    )
    if not port:
        return

    fetch_port_optical_snapshot(
        port,
        discovery_cache={},
        persist_keys=False,
    )


@shared_task(name="inventory.tasks.warm_device_ports")
def warm_device_ports(device_id: int) -> None:
    """Warm optical snapshots for every port belonging to a device."""
    ports = (
        Port.objects.select_related("device")
        .only(
            "id",
            "device_id",
            "device__zabbix_hostid",
            "rx_power_item_key",
            "tx_power_item_key",
        )
        .filter(device_id=device_id)
    )
    for port in ports:
        fetch_port_optical_snapshot(
            port,
            discovery_cache={},
            persist_keys=False,
        )


@shared_task(name="inventory.tasks.warm_all_optical_snapshots")
def warm_all_optical_snapshots() -> None:
    """Queue optical cache refresh for every monitored port."""
    port_ids = list(Port.objects.values_list("id", flat=True))
    for port_id in port_ids:
        cast(Any, warm_port_optical_cache).delay(int(port_id))


@shared_task(name="inventory.tasks.update_all_port_optical_levels")
def update_all_port_optical_levels() -> dict[str, Any]:
    """
    Coleta níveis ópticos (RX/TX) para todas as portas com item keys configuradas
    e persiste nos campos "last_*" do modelo Port.

    Estratégia: usa `fetch_ports_optical_snapshots` (versão batch) que agrupa
    portas por host e faz UMA chamada ao Zabbix por device em vez de uma
    por porta. Permite rodar a task em intervalos curtos (60s) sem pesar
    no Zabbix — essencial para o painel óptico refletir mudanças de estado
    (ex.: cabo voltou ao normal) sem esperar 5+ minutos.

    Objetivo: Eliminar chamadas síncronas ao Zabbix em endpoints REST.
    As APIs passam a ler diretamente do banco (Port.last_rx_power / last_tx_power).
    """
    from inventory.domain.optical import fetch_ports_optical_snapshots
    from inventory.domain.optical_apply import apply_optical_snapshot

    logger.info("[Optical Levels Task] Iniciando atualização de níveis ópticos (batch)")

    # Seleciona apenas portas que possuem ao menos uma key de RX ou TX
    ports_qs = (
        Port.objects.select_related("device")
        .only(
            "id",
            "name",
            "rx_power_item_key",
            "tx_power_item_key",
            "last_rx_power",
            "last_tx_power",
            "optical_problem",
            "device__zabbix_hostid",
        )
        .filter(
            (models.Q(rx_power_item_key__isnull=False) & ~models.Q(rx_power_item_key=""))
            | (models.Q(tx_power_item_key__isnull=False) & ~models.Q(tx_power_item_key=""))
        )
    )

    ports = list(ports_qs)
    total = len(ports)
    updated = 0
    errors: list[str] = []
    now = timezone.now()

    # EV-0063: uma coleta de cada vez — sem isto as execuções de 60 s sobrepunham-se
    # (cada uma levava ~190 s) e ocupavam os workers da fila zabbix.
    if not cache.add(OPTICAL_LOCK_KEY, now.isoformat(), OPTICAL_LOCK_SECONDS):
        logger.info("[Optical Levels Task] Coleta anterior ainda a correr — ignorada")
        return {"success": True, "skipped": "lock", "total": total, "updated": 0, "errors": 0}

    try:
        # Batch: 1 item.get por device. Sem metadados de estado da interface: a tarefa
        # não os usa e custavam ~5 chamadas por porta (EV-0063: 1233 → ~14 chamadas).
        snapshots_map = fetch_ports_optical_snapshots(
            ports, persist_keys=False, include_status_meta=False
        )
    except Exception as exc:
        cache.delete(OPTICAL_LOCK_KEY)
        logger.error("[Optical Levels Task] Batch fetch falhou: %s", exc, exc_info=True)
        return {"success": False, "total": total, "updated": 0, "errors": 1, "error": str(exc)}

    # EV-0085: uma chave que não veio no item.get do host fica no snapshot sem `*_dbm` e sem
    # `*_problem` (o domínio guarda-a como «sem item»). Isso tanto é «item apagado no host»
    # como «Zabbix em baixo» (o item.get em lote engole a exceção e devolve zero itens). Só
    # se regista «item não existe no host» quando esta coleta recebeu pelo menos um item —
    # sem isso uma falha do Zabbix marcava todas as portas como problema de item.
    zabbix_answered = any(
        snap.get(prefix + "_dbm") is not None or snap.get(prefix + "_problem")
        for snap in snapshots_map.values()
        for prefix in ("rx", "tx")
    )

    # Persiste resultados em bulk-style (um save por porta com update_fields)
    for port in ports:
        try:
            snapshot = snapshots_map.get(port.pk) or {}
            # EV-0063/EV-0082: o snapshot só traz `rx_dbm`/`tx_dbm` com leitura válida
            # (item coletado e suportado, valor em -60…+15 dBm, sem sentinela de ONU);
            # o motivo da leitura descartada vem em `rx_problem`/`tx_problem`. Essa
            # ponta não é gravada e `last_optical_check` não avança por ela — o valor
            # anterior fica com a hora antiga e a UI marca-o como leitura antiga.
            bad = [
                f"{label} ({snapshot.get(prefix + '_key')}): {snapshot[prefix + '_problem']}"
                for label, prefix in (("RX", "rx"), ("TX", "tx"))
                if snapshot.get(prefix + "_problem")
            ]
            if bad:
                msg = f"Port {port.id} ({port.name}) chave não devolve dBm: {', '.join(bad)}"
                logger.warning("[Optical Levels Task] %s", msg)
                errors.append(msg)

            # EV-0082/EV-0088: regra partilhada com o refresh manual (um só `last_optical_check`;
            # a ponta sem leitura válida, com ou sem chave, passa a null quando a outra é gravada).
            reading_fields = apply_optical_snapshot(port, snapshot, now)
            update_fields = list(reading_fields)

            # EV-0085: o motivo fica na porta (o ecrã «Saúde da coleta» e o aviso por e-mail
            # leem-no); só entra no save quando muda, para não multiplicar escritas a cada 60 s.
            missing = [
                f"{label} ({snapshot.get(prefix + '_key')}): {OPTICAL_ITEM_MISSING}"
                for label, prefix in (("RX", "rx"), ("TX", "tx"))
                if snapshot.get(prefix + "_key")
                and snapshot.get(prefix + "_dbm") is None
                and not snapshot.get(prefix + "_problem")
            ]
            if not missing or zabbix_answered:
                problem = ", ".join(bad + missing)[:255]
                if problem != (port.optical_problem or ""):
                    port.optical_problem = problem
                    update_fields.append("optical_problem")
            if update_fields:
                port.save(update_fields=update_fields)
            if reading_fields:  # `updated` conta leituras gravadas, não só o motivo
                updated += 1
        except Exception as exc:
            msg = f"Port {port.id} ({port.name}) falhou: {exc}"
            logger.warning("[Optical Levels Task] %s", msg)
            errors.append(msg)

    cache.delete(OPTICAL_LOCK_KEY)
    result = {
        "success": True,
        "total": total,
        "updated": updated,
        "errors": len(errors),
    }
    logger.info(
        "[Optical Levels Task] Concluído: %d/%d portas atualizadas (%d erros)",
        updated,
        total,
        len(errors),
    )
    return result


@shared_task(name="inventory.tasks.refresh_fiber_list_cache")
def refresh_fiber_list_cache() -> dict[str, Any]:
    """
    Refresh the fiber list cache in background.

    This task can be triggered manually or scheduled periodically
    to keep the cache warm.

    Returns:
        dict with refresh statistics
    """
    from inventory.cache.fibers import get_cached_fiber_list
    from inventory.usecases import fibers as fiber_uc

    logger.info("[Fiber Cache Task] Starting background refresh")

    # Force a fresh fetch by calling the function directly
    data, _ = get_cached_fiber_list(fiber_uc.list_fiber_cables)

    result = {
        "success": True,
        "cables_count": len(data),
        "refreshed_at": "background_task",
    }

    logger.info(
        "[Fiber Cache Task] Cache refreshed: %d cables",
        len(data),
    )

    return result


@shared_task(
    name="inventory.tasks.refresh_cables_oper_status",
    bind=True,
    time_limit=300,  # 5 minutes max
)
def refresh_cables_oper_status(self: Any) -> dict[str, Any]:
    """
    Pre-calculate operational status for all fiber cables.

    Phase 9.1: Enhanced to persist status in FiberCable model fields
    instead of relying solely on Redis cache.

    This task runs periodically to:
    1. Fetch all cables from DB
    2. Query Zabbix for each cable's port status
    3. Store results in FiberCable model (DB-backed)
    4. Store in Redis cache (optional acceleration layer)
    5. Broadcast updates via WebSocket

    The API endpoint reads from FiberCable.last_status_* fields
    (database = source of truth, Redis = optional cache).

    Returns:
        dict with processing statistics
    """
    from django.core.cache import cache

    from inventory.models import FiberCable
    from inventory.usecases import fibers as fiber_uc
    from maps_view.realtime.publisher import broadcast_cable_status_update

    logger.info("[Cable Status Task] Starting background refresh")

    start_time = __import__("time").time()
    now = timezone.now()

    # Fetch all cables
    cables = FiberCable.objects.select_related(
        "origin_port__device", "destination_port__device"
    ).all()

    total_count = cables.count()
    success_count = 0
    error_count = 0

    # Collect updates for WebSocket broadcast
    cable_updates = []

    for cable in cables:
        try:
            # Call the existing function that queries Zabbix
            status_data = fiber_uc.update_cable_oper_status(cable.id)

            # PHASE 9.1: Persist in database (source of truth)
            cable.last_status_origin = status_data.get("origin_status", "unknown")
            cable.last_status_dest = status_data.get("destination_status", "unknown")
            cable.last_status_check = now
            cable.save(
                update_fields=[
                    "last_status_origin",
                    "last_status_dest",
                    "last_status_check",
                ]
            )

            # Store in Redis cache (optional acceleration layer)
            cache_key = f"cable:oper_status:{cable.id}"
            cache.set(cache_key, status_data, timeout=120)

            # Add to WebSocket broadcast batch
            cable_updates.append(status_data)

            success_count += 1

        except Exception as exc:
            logger.warning(
                "[Cable Status Task] Failed to process cable %d: %s",
                cable.id,
                exc,
            )
            error_count += 1

    # Broadcast all updates via WebSocket (if channel layer configured)
    if cable_updates:
        try:
            broadcast_cable_status_update(cable_updates)
        except Exception as exc:
            logger.warning(
                "[Cable Status Task] Failed to broadcast updates: %s",
                exc,
            )

    elapsed = __import__("time").time() - start_time

    result = {
        "success": True,
        "total_cables": total_count,
        "processed": success_count,
        "errors": error_count,
        "broadcasted": len(cable_updates),
        "elapsed_seconds": round(elapsed, 2),
    }

    logger.info(
        "[Cable Status Task] Completed: %d/%d cables in %.2fs " "(%d errors, %d broadcasted)",
        success_count,
        total_count,
        elapsed,
        error_count,
        len(cable_updates),
    )

    return result


@shared_task(
    name="inventory.tasks.refresh_fiber_live_status",
    bind=True,
    time_limit=300,  # 5 minutes max
)
def refresh_fiber_live_status(self: Any) -> dict[str, Any]:
    """
    Calculate live status for all fiber cables (Phase 9.1).

    Similar to refresh_cables_oper_status but calls compute_live_status
    which performs more advanced status detection including optical power
    checks and interface status validation.

    Results are persisted to FiberCable.last_live_status and last_live_check.

    Returns:
        dict with processing statistics
    """
    from inventory.models import FiberCable
    from inventory.usecases import fibers as fiber_uc

    logger.info("[Live Status Task] Starting background refresh")

    start_time = __import__("time").time()
    now = timezone.now()

    # Fetch all cables
    cables = FiberCable.objects.select_related(
        "origin_port__device", "destination_port__device"
    ).all()

    total_count = cables.count()
    success_count = 0
    error_count = 0
    changed_count = 0

    for cable in cables:
        try:
            # Compute live status (may update cable.status if changed)
            live_status = fiber_uc.compute_live_status(
                cable,
                persist=True,  # Allow status updates
                event_reason="celery-live-status-refresh",
            )

            # PHASE 9.1: Persist live status result in database
            cable.last_live_status = live_status.combined_status
            cable.last_live_check = now
            cable.save(update_fields=["last_live_status", "last_live_check"])

            if live_status.changed:
                changed_count += 1

            success_count += 1

        except Exception as exc:
            logger.warning(
                "[Live Status Task] Failed to process cable %d: %s",
                cable.id,
                exc,
            )
            error_count += 1

    elapsed = __import__("time").time() - start_time

    result = {
        "success": True,
        "total_cables": total_count,
        "processed": success_count,
        "changed": changed_count,
        "errors": error_count,
        "elapsed_seconds": round(elapsed, 2),
    }

    logger.info(
        "[Live Status Task] Completed: %d/%d cables in %.2fs " "(%d changed, %d errors)",
        success_count,
        total_count,
        elapsed,
        changed_count,
        error_count,
    )

    return result


@shared_task(
    name="inventory.refresh_radius_search_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="maps",
)
def refresh_radius_search_cache(
    self: Any, lat: float, lng: float, radius_km: float, limit: int = 100
) -> dict[str, Any]:
    """
    Async task to refresh radius search cache with fresh data from DB.

    Queued when cache is stale (30-60s old). Fetches fresh results
    and updates cache to serve subsequent requests quickly.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        radius_km: Search radius in kilometers
        limit: Maximum number of results

    Returns:
        dict with refresh status and statistics

    Example:
        from inventory.tasks import refresh_radius_search_cache
        refresh_radius_search_cache.delay(-15.7801, -47.9292, 10, 100)
    """
    from inventory.cache.radius_search import set_cached_radius_search
    from inventory.usecases.spatial import get_sites_within_radius

    logger.info(
        "[Refresh Cache Task] Starting for lat=%.6f, lng=%.6f, " "r=%dkm, limit=%d",
        lat,
        lng,
        radius_km,
        limit,
    )

    start_time = __import__("time").time()

    try:
        # Fetch fresh data from database
        sites = get_sites_within_radius(lat, lng, radius_km, limit)

        # Update cache
        success = set_cached_radius_search(lat, lng, radius_km, limit, sites)

        elapsed = __import__("time").time() - start_time

        result = {
            "success": success,
            "site_count": len(sites),
            "elapsed_seconds": round(elapsed, 3),
            "cache_updated": success,
        }

        logger.info(
            "[Refresh Cache Task] Completed: %d sites in %.3fs " "(cache_updated=%s)",
            len(sites),
            elapsed,
            success,
        )

        return result

    except Exception as exc:
        logger.error("[Refresh Cache Task] Failed: %s", exc.__class__.__name__, exc_info=exc)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(
                "[Refresh Cache Task] Retrying (attempt %d/%d)",
                self.request.retries + 1,
                self.max_retries,
            )
            raise self.retry(exc=exc) from exc

        return {"success": False, "error": str(exc), "error_type": exc.__class__.__name__}

    return result


# === Fim das tasks de optical power ===


# ── Dispatcher de alarmes de fibra (Fase A) ─────────────────────────────────


@shared_task(name="inventory.tasks.dispatch_fiber_alarms_task")
def dispatch_fiber_alarms_task(window_minutes: int = 30) -> dict[str, Any]:
    """Lê FiberEvents recentes, faz match com FiberCableAlarmConfig e envia.

    Agendado no Celery beat a cada 1 min — janela de 30 min cobre o pior
    caso de retry com backoff exponencial (1+2+4+8+16 = 31 min).
    Aplica dedupe + retry policy + snooze via FiberAlarmNotificationLog.
    """
    try:
        from inventory.usecases.fiber_alarm_configs import dispatch_pending_alarms

        summary = dispatch_pending_alarms(window_minutes=window_minutes)
        if summary.get("sent", 0) > 0 or summary.get("failed", 0) > 0:
            logger.info("[dispatch_fiber_alarms] %s", summary)
        return summary
    except Exception as exc:
        logger.exception("dispatch_fiber_alarms_task failed: %s", exc)
        return {"error": str(exc)}


# ── EV-0085: aviso por e-mail da saúde da coleta ────────────────────────────

COLLECTION_HEALTH_NOTIFIED_KEY = "inventory:collection-health:notified"
COLLECTION_HEALTH_NOTIFIED_TIMEOUT = 30 * 24 * 3600
COLLECTION_HEALTH_ROUTE = "/saude-coleta"


def _collection_health_alarms(report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Equipamentos «em alarme»: host Zabbix inexistente OU nenhuma porta com leitura.

    Zabbix em baixo → ``devices_missing_host`` vem vazio: desconhecido não conta como inexistente.
    """
    alarms: dict[int, dict[str, Any]] = {}
    for dev in report["devices_missing_host"]:
        alarms.setdefault(
            dev["device_id"],
            {"name": dev["device_name"], "site": dev["site_name"], "reasons": []},
        )["reasons"].append(f"host Zabbix {dev['zabbix_hostid']} não existe")
    first_problem: dict[int, str] = {}
    for port in report["ports"]:
        if port["problem"]:
            first_problem.setdefault(port["device_id"], port["problem"])
    for dev in report["devices_without_readings"]:
        reason = f"0 de {dev['ports_with_key']} porta(s) com leitura"
        if dev["device_id"] in first_problem:
            reason += f" (ex.: {first_problem[dev['device_id']]})"
        alarms.setdefault(
            dev["device_id"],
            {"name": dev["device_name"], "site": dev["site_name"], "reasons": []},
        )["reasons"].append(reason)
    return alarms


def _collection_health_email(
    alarms: dict[int, dict[str, Any]], new_ids: set[int], stale_hours: int
) -> tuple[str, str]:
    lines = []
    for device_id, info in sorted(alarms.items(), key=lambda kv: (kv[1]["name"], kv[0])):
        mark = " [novo]" if device_id in new_ids else ""
        site = f" — {info['site']}" if info["site"] else ""
        lines.append(f"- {info['name']}{site}{mark}: {'; '.join(info['reasons'])}")
    subject = f"[ProVeMaps] Saúde da coleta: {len(alarms)} equipamento(s) sem leitura"
    body = (
        "Equipamentos com host Zabbix inexistente ou sem nenhuma leitura óptica nas últimas "
        f"{stale_hours} h:\n\n" + "\n".join(lines) + f"\n\nDetalhe em {COLLECTION_HEALTH_ROUTE}.\n"
    )
    return subject, body


@shared_task(name="inventory.tasks.notify_collection_health")
def notify_collection_health() -> dict[str, Any]:
    """Um e-mail só quando um equipamento ENTRA no conjunto em alarme face ao último aviso.

    O conjunto avisado fica em cache; quem sai do alarme sai também do guardado (se voltar,
    avisa-se de novo). Nunca rebenta por SMTP nem por Zabbix: regista e devolve um dict.
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from evolucao.tasks import destinatarios_staff
    from inventory.usecases.collection_health import collection_health

    try:
        report = collection_health()
    except Exception as exc:
        logger.warning("[Collection Health] cálculo falhou: %s", exc, exc_info=True)
        return {"sent": False, "error": str(exc)[:200]}

    alarms = _collection_health_alarms(report)
    current = set(alarms)
    previous = {int(i) for i in (cache.get(COLLECTION_HEALTH_NOTIFIED_KEY) or [])}
    new_ids = current - previous
    result: dict[str, Any] = {
        "sent": False,
        "alarms": len(current),
        "new": len(new_ids),
        "zabbix_ok": report["zabbix_ok"],
    }
    # Os que saíram do alarme saem do guardado — menos com o Zabbix em baixo: aí o «host
    # inexistente» é desconhecido e largá-los fazia o aviso repetir quando o Zabbix voltasse.
    kept = (previous & current) if report["zabbix_ok"] else previous
    if not new_ids:
        cache.set(COLLECTION_HEALTH_NOTIFIED_KEY, sorted(kept), COLLECTION_HEALTH_NOTIFIED_TIMEOUT)
        return result

    recipients = destinatarios_staff()
    if not recipients:
        logger.warning(
            "[Collection Health] %d equipamento(s) em alarme e sem destinatários", len(current)
        )
        result["error"] = "sem destinatários"
        return result

    subject, body = _collection_health_email(alarms, new_ids, report["stale_hours"])
    try:
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", None) or None,
            recipients,
            fail_silently=False,
        )
    except Exception as exc:  # SMTP em baixo não mata a tarefa; tenta-se na hora seguinte
        logger.warning("[Collection Health] envio falhou: %s", exc)
        result["error"] = str(exc)[:200]
        return result

    cache.set(
        COLLECTION_HEALTH_NOTIFIED_KEY, sorted(current | kept), COLLECTION_HEALTH_NOTIFIED_TIMEOUT
    )
    result["sent"] = True
    result["recipients"] = len(recipients)
    logger.info(
        "[Collection Health] aviso enviado: %d em alarme (%d novo(s))", len(current), len(new_ids)
    )
    return result

from __future__ import annotations

import ipaddress
import json
import logging
import platform
import re
import socket
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, cast

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.test import RequestFactory
from django.views.decorators.http import require_GET, require_POST

from integrations.zabbix.decorators import handle_api_errors
from integrations.zabbix.guards import diagnostics_guard

from inventory.usecases import devices as device_uc
from inventory.usecases.devices import (
    InventoryNotFound,
    InventoryUseCaseError,
    InventoryValidationError,
)
from inventory.usecases import fibers as fiber_uc
from inventory.usecases.fibers import FiberNotFound
from inventory.models import FiberCable, FiberEvent

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60

JsonDict = Dict[str, Any]


def _current_status(cable: FiberCable) -> str:
    status_value: Any = getattr(cable, "status")
    if isinstance(status_value, str):
        return status_value
    return str(status_value)


def _load_json_body(request: HttpRequest) -> JsonDict:
    """Parse a JSON request body and guarantee a dictionary response."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object")
    return cast(JsonDict, data)


@require_GET
@login_required
@handle_api_errors
def api_update_cable_oper_status(
    request: HttpRequest,
    cable_id: int,
) -> HttpResponse:
    try:
        payload = fiber_uc.update_cable_oper_status(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_port_optical_status(
    request: HttpRequest,
    port_id: int,
) -> HttpResponse:
    try:
        payload = device_uc.device_port_optical_status(port_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    try:
        payload = device_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports_with_optical(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    cache_key = f"inventory_device_ports_optical_{device_id}"
    payload = cache.get(cache_key)

    if payload is None:
        try:
            payload = device_uc.get_device_ports_with_optical(device_id)
        except InventoryNotFound as exc:
            return JsonResponse({"error": str(exc)}, status=404)
        cache.set(cache_key, payload, CACHE_TTL_SECONDS)
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_add_device_from_zabbix(request: HttpRequest) -> HttpResponse:
    guard_response = diagnostics_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        data = _load_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        payload = device_uc.add_device_from_zabbix(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryUseCaseError as exc:
        logger.exception("Failed to register device via Zabbix: %s", exc)
        return JsonResponse(
            {"error": "Failed to register device"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_zabbix_discover_hosts(request: HttpRequest) -> HttpResponse:
    payload = device_uc.discover_zabbix_hosts()
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_bulk_create_inventory(request: HttpRequest) -> HttpResponse:
    guard_response = diagnostics_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        data = _load_json_body(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    try:
        payload = device_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Bulk create failed: %s", exc)
        return JsonResponse(
            {"error": "Failed to create inventory"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_sites(request: HttpRequest) -> HttpResponse:
    payload = device_uc.list_sites()
    return JsonResponse(payload)


@require_GET
@handle_api_errors
def api_port_traffic_history(
    request: HttpRequest,
    port_id: int,
) -> HttpResponse:
    try:
        payload = device_uc.port_traffic_history(port_id, request.GET)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Failed to fetch traffic history: %s", exc)
        return JsonResponse(
            {"error": "Failed to fetch traffic history"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_test_telnet(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    port_raw = request.GET.get("port", "23")
    timeout_raw = request.GET.get("timeout", "3")
    started = time.time()

    if not host:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse(
                {"error": "Invalid host/IP"},
                status=400,
            )
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return JsonResponse(
            {"error": "Invalid port"},
            status=400,
        )
    try:
        timeout = float(timeout_raw)
        if timeout <= 0 or timeout > 30:
            timeout = 3.0
    except ValueError:
        timeout = 3.0

    result = {"host": host, "port": port, "timeout": timeout}
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            elapsed = time.time() - started
            result.update(
                {
                    "status": "success",
                    "elapsed_ms": int(elapsed * 1000),
                    "peername": conn.getpeername(),
                }
            )
        return JsonResponse(result)
    except Exception as exc:  # pragma: no cover - network failures vary
        elapsed = time.time() - started
        result.update(
            {
                "status": "failed",
                "error": str(exc)[:300],
                "elapsed_ms": int(elapsed * 1000),
            }
        )
        return JsonResponse(result, status=502)


@require_GET
@login_required
@handle_api_errors
def api_test_ping(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    if not host:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse(
                {"error": "Invalid host/IP"},
                status=400,
            )

    try:
        count = int(request.GET.get("count", "1"))
        if count < 1 or count > 4:
            count = 1
    except ValueError:
        count = 1
    try:
        timeout = float(request.GET.get("timeout", "3"))
        if timeout <= 0 or timeout > 15:
            timeout = 3.0
    except ValueError:
        timeout = 3.0

    system = platform.system().lower()
    if system == "windows":
        per_timeout_ms = int(max(1, min(timeout, 5)) * 1000)
        cmd = ["ping", "-n", str(count), "-w", str(per_timeout_ms), host]
    else:
        per_wait = int(max(1, min(timeout, 5)))
        cmd = ["ping", "-c", str(count), "-W", str(per_wait), host]

    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + count + 1,
        )
    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"host": host, "count": count, "status": "timeout"},
            status=504,
        )

    elapsed = time.time() - started
    stdout = proc.stdout or ""
    transmitted = received = packet_loss = None
    avg_ms = None
    try:
        if system == "windows":
            m_stats = re.search(
                (
                    r"Enviados = (\d+), Recebidos = (\d+), "
                    r"Perdidos = (\d+).*?\((\d+)%"
                ),
                stdout,
                re.S,
            ) or re.search(
                (
                    r"Sent = (\d+), Received = (\d+), "
                    r"Lost = (\d+).*?\((\d+)%"
                ),
                stdout,
                re.S,
            )
            if m_stats:
                transmitted, received, _lost, packet_loss = map(
                    int, m_stats.groups()
                )
            m_rtt = re.search(r"Average = (\d+)ms", stdout)
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
        else:
            m_stats = re.search(
                (
                    r"(\d+) packets transmitted, (\d+) "
                    r"(?:packets )?received, (\d+)% packet loss"
                ),
                stdout,
            )
            if m_stats:
                transmitted, received, packet_loss = map(
                    int, m_stats.groups()
                )
            m_rtt = re.search(
                r"rtt min/avg/max/[a-z]+ = [0-9.]+/([0-9.]+)/",
                stdout,
            )
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
    except Exception:  # pragma: no cover - defensive parsing
        pass

    success = proc.returncode == 0 and received and received > 0
    return JsonResponse(
        {
            "host": host,
            "count": count,
            "status": "success" if success else "failed",
            "return_code": proc.returncode,
            "elapsed_ms": int(elapsed * 1000),
            "transmitted": transmitted,
            "received": received,
            "packet_loss_percent": packet_loss,
            "avg_rtt_ms": avg_ms,
            "raw_output": stdout.splitlines()[-6:] if stdout else [],
        }
    )


@require_GET
@login_required
@handle_api_errors
def api_test_ping_telnet(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    factory = RequestFactory()
    ip = request.GET.get("ip") or request.GET.get("host") or ""
    port = request.GET.get("port", "23")
    if not ip:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )

    ping_request = factory.get("/diagnostics/ping", {"ip": ip, "count": "1"})
    ping_request.user = request.user
    ping_response = api_test_ping(ping_request)

    telnet_request = factory.get(
        "/diagnostics/telnet",
        {"ip": ip, "port": port},
    )
    telnet_request.user = request.user
    telnet_response = api_test_telnet(telnet_request)

    return JsonResponse(
        {
            "host": ip,
            "port": port,
            "ping": getattr(ping_response, "json", lambda: None)(),
            "telnet": getattr(telnet_response, "json", lambda: None)(),
            "timestamp": datetime.now().isoformat(),
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_up(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("up")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="up",
        detected_reason="diagnostic-up",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "up",
            "previous_status": previous,
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_down(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("down")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="down",
        detected_reason="diagnostic-down",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "down",
            "previous_status": previous,
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_unknown(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("unknown")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="unknown",
        detected_reason="diagnostic-unknown",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "unknown",
            "previous_status": previous,
        }
    )


__all__ = [
    "api_update_cable_oper_status",
    "api_device_port_optical_status",
    "api_device_ports",
    "api_device_ports_with_optical",
    "api_add_device_from_zabbix",
    "api_zabbix_discover_hosts",
    "api_bulk_create_inventory",
    "api_sites",
    "api_port_traffic_history",
    "api_test_telnet",
    "api_test_ping",
    "api_test_ping_telnet",
    "api_test_set_cable_up",
    "api_test_set_cable_down",
    "api_test_set_cable_unknown",
]

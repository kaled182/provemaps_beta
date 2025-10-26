from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
import time
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.test import RequestFactory
from django.views.decorators.http import require_GET, require_POST

from .decorators import handle_api_errors
from .guards import diagnostics_guard
from inventory.models import FiberCable, FiberEvent


@require_POST
@login_required
@handle_api_errors
def test_set_cable_up(request, cable_id: int):
    guard = diagnostics_guard(request)
    if guard:
        return guard
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)
    previous = cable.status
    cable.update_status("up")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="up",
        detected_reason="diagnostic-up",
    )
    return JsonResponse({"fiber_id": cable.id, "status": "up", "previous_status": previous})


@require_POST
@login_required
@handle_api_errors
def test_set_cable_down(request, cable_id: int):
    guard = diagnostics_guard(request)
    if guard:
        return guard
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)
    previous = cable.status
    cable.update_status("down")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="down",
        detected_reason="diagnostic-down",
    )
    return JsonResponse({"fiber_id": cable.id, "status": "down", "previous_status": previous})


@require_POST
@login_required
@handle_api_errors
def test_set_cable_unknown(request, cable_id: int):
    guard = diagnostics_guard(request)
    if guard:
        return guard
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)
    previous = cable.status
    cable.update_status("unknown")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="unknown",
        detected_reason="diagnostic-unknown",
    )
    return JsonResponse({"fiber_id": cable.id, "status": "unknown", "previous_status": previous})


@require_GET
@login_required
@handle_api_errors
def api_test_telnet(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    port_raw = request.GET.get("port", "23")
    timeout_raw = request.GET.get("timeout", "3")
    started = time.time()

    if not host:
        return JsonResponse({"error": "Parameter ip/host is required"}, status=400)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse({"error": "Invalid host/IP"}, status=400)
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "Invalid port"}, status=400)
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
    except Exception as exc:
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
def api_test_ping(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    if not host:
        return JsonResponse({"error": "Parameter ip/host is required"}, status=400)

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse({"error": "Invalid host/IP"}, status=400)

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
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + count + 1)
    except subprocess.TimeoutExpired:
        return JsonResponse({"host": host, "count": count, "status": "timeout"}, status=504)

    elapsed = time.time() - started
    stdout = proc.stdout or ""
    transmitted = received = packet_loss = None
    avg_ms = None
    try:
        if system == "windows":
            m_stats = re.search(
                r"Enviados = (\d+), Recebidos = (\d+), Perdidos = (\d+).*?\((\d+)%",
                stdout,
                re.S,
            ) or re.search(
                r"Sent = (\d+), Received = (\d+), Lost = (\d+).*?\((\d+)%",
                stdout,
                re.S,
            )
            if m_stats:
                transmitted, received, lost, packet_loss = map(int, m_stats.groups())
            m_rtt = re.search(r"Average = (\d+)ms", stdout)
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
        else:
            m_stats = re.search(
                r"(\d+) packets transmitted, (\d+) (?:packets )?received, (\d+)% packet loss",
                stdout,
            )
            if m_stats:
                transmitted, received, packet_loss = map(int, m_stats.groups())
            m_rtt = re.search(r"rtt min/avg/max/[a-z]+ = [0-9.]+/([0-9.]+)/", stdout)
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
    except Exception:
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
def api_test_ping_telnet(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard

    factory = RequestFactory()
    ip = request.GET.get("ip") or request.GET.get("host") or ""
    port = request.GET.get("port", "23")
    if not ip:
        return JsonResponse({"error": "Parameter ip/host is required"}, status=400)

    ping_request = factory.get("/diagnostics/ping", {"ip": ip, "count": "1"})
    ping_request.user = request.user
    ping_response = api_test_ping(ping_request)

    telnet_request = factory.get("/diagnostics/telnet", {"ip": ip, "port": port})
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

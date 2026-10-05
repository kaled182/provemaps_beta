"""Views dos servidores de monitorização: `/setup_app/api/monitoring-servers/[<id>/]`.

Finas de propósito (EV-0017e): a lógica está em `setup_app.usecases.monitoring`.
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..usecases import monitoring as usecase
from ._auth import staff_required


def _invalid_json():
    return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)


def _error(exc: usecase.MonitoringError):
    return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)


@require_http_methods(["GET", "POST"])
@staff_required
def monitoring_servers(request):
    if request.method == "GET":
        return JsonResponse({"success": True, "servers": usecase.list_servers()})
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _invalid_json()
    try:
        server = usecase.create_server(data)
    except usecase.MonitoringError as exc:
        return _error(exc)
    return JsonResponse({"success": True, "server": server})


@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
@staff_required
def monitoring_server_detail(request, server_id: int):
    try:
        server = usecase.get_server(server_id)
    except usecase.MonitoringError as exc:
        return _error(exc)
    if request.method == "GET":
        return JsonResponse(
            {"success": True, "server": usecase.serialize_monitoring_server(server)}
        )
    if request.method == "DELETE":
        usecase.delete_server(server)
        return JsonResponse({"success": True, "message": "Server removed."})
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _invalid_json()
    return JsonResponse({"success": True, "server": usecase.update_server(server, data)})

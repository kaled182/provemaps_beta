"""Servidores de monitorização (`MonitoringServer`). Saiu de `setup_app/api_views.py` em EV-0017e."""

from __future__ import annotations

from typing import Any

from ..models import MonitoringServer

TOKEN_MASK = "********"


class MonitoringError(ValueError):
    status = 400


class MonitoringServerNotFound(MonitoringError):
    status = 404


def serialize_monitoring_server(server: MonitoringServer) -> dict[str, Any]:
    """O token nunca sai; só `has_auth_token`."""
    return {
        "id": server.id,
        "name": server.name,
        "server_type": server.server_type,
        "url": server.url,
        "is_active": server.is_active,
        "has_auth_token": bool(server.auth_token),
        "auth_token": "",
        "extra_config": server.extra_config or {},
        "created_at": server.created_at.isoformat(),
    }


def list_servers() -> list[dict[str, Any]]:
    servers = MonitoringServer.objects.all().order_by("-is_active", "name")
    return [serialize_monitoring_server(s) for s in servers]


def create_server(data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name", "")).strip()
    url = str(data.get("url", "")).strip()
    if not name or not url:
        raise MonitoringError("Name and URL are required.")
    extra_config = (
        data.get("extra_config", {}) if isinstance(data.get("extra_config"), dict) else {}
    )
    server = MonitoringServer.objects.create(
        name=name,
        url=url,
        server_type=str(data.get("server_type", "zabbix")).strip() or "zabbix",
        auth_token=str(data.get("auth_token", "")).strip() or None,
        is_active=bool(data.get("is_active", True)),
        extra_config=extra_config,
    )
    return serialize_monitoring_server(server)


def get_server(server_id: int) -> MonitoringServer:
    try:
        return MonitoringServer.objects.get(id=server_id)
    except MonitoringServer.DoesNotExist as exc:
        raise MonitoringServerNotFound("Server not found.") from exc


def update_server(server: MonitoringServer, data: dict[str, Any]) -> dict[str, Any]:
    """Parcial; `auth_token` vazio apaga, a máscara mantém, outro valor substitui."""
    if "name" in data:
        server.name = str(data.get("name", "")).strip() or server.name
    if "url" in data:
        server.url = str(data.get("url", "")).strip() or server.url
    if "server_type" in data:
        server.server_type = str(data.get("server_type", "zabbix")).strip() or server.server_type
    if "is_active" in data:
        server.is_active = bool(data.get("is_active"))
    if "extra_config" in data and isinstance(data.get("extra_config"), dict):
        server.extra_config = data.get("extra_config") or {}
    if "auth_token" in data:
        token = data.get("auth_token", "")
        if token == "":
            server.auth_token = None
        elif token != TOKEN_MASK:
            server.auth_token = token
    server.save()
    return serialize_monitoring_server(server)


def delete_server(server: MonitoringServer) -> None:
    server.delete()

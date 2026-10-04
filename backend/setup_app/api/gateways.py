"""Views dos gateways de mensagens e do QR Code do WhatsApp: `/setup_app/api/gateways/*`.

Finas de propósito (EV-0017c): a lógica está em `setup_app.usecases.gateways`.
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..usecases import gateways as usecase
from ._auth import staff_required


def _invalid_json():
    return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)


def _error(exc: usecase.GatewayError):
    return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)


def _body_or_empty(request) -> dict:
    """Corpo JSON tolerante: as rotas de QR tratam JSON inválido como `{}` (comportamento legado)."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


@require_http_methods(["GET", "POST"])
@staff_required
def messaging_gateways(request):
    if request.method == "GET":
        return JsonResponse({"success": True, "gateways": usecase.list_gateways_for(request.user)})
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _invalid_json()
    try:
        gateway = usecase.create_gateway(data)
    except usecase.GatewayError as exc:
        return _error(exc)
    return JsonResponse({"success": True, "gateway": gateway})


@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
@staff_required
def messaging_gateway_detail(request, gateway_id: int):
    try:
        gateway = usecase.get_gateway_for(request.user, gateway_id)
    except usecase.GatewayError as exc:
        return _error(exc)

    if request.method == "GET":
        return JsonResponse({"success": True, "gateway": usecase.serialize_gateway(gateway)})

    if request.method == "DELETE":
        usecase.delete_gateway(gateway)
        return JsonResponse({"success": True, "message": "Gateway removido."})

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _invalid_json()
    return JsonResponse({"success": True, "gateway": usecase.update_gateway(gateway, data)})


def _qr_view(gateway_id: int, action, override_url: str):
    try:
        gateway = usecase.get_qr_gateway(gateway_id)
        result = action(gateway, override_url)
    except usecase.GatewayError as exc:
        return _error(exc)
    return JsonResponse({"success": True, **result})


@require_http_methods(["POST"])
@staff_required
def whatsapp_qr_start(request, gateway_id: int):
    override = (_body_or_empty(request).get("qr_service_url") or "").strip()
    return _qr_view(gateway_id, usecase.qr_start, override)


@require_http_methods(["GET"])
@staff_required
def whatsapp_qr_status(request, gateway_id: int):
    override = request.GET.get("qr_service_url", "").strip()
    return _qr_view(gateway_id, usecase.qr_status, override)


@require_http_methods(["POST"])
@staff_required
def whatsapp_qr_disconnect(request, gateway_id: int):
    override = (_body_or_empty(request).get("qr_service_url") or "").strip()
    return _qr_view(gateway_id, usecase.qr_disconnect, override)


@require_http_methods(["POST"])
@staff_required
def whatsapp_qr_reset(request, gateway_id: int):
    override = (_body_or_empty(request).get("qr_service_url") or "").strip()
    return _qr_view(gateway_id, usecase.qr_reset, override)


@require_http_methods(["POST"])
@staff_required
def whatsapp_qr_test_message(request, gateway_id: int):
    try:
        gateway = usecase.get_qr_gateway(gateway_id)
        result = usecase.qr_test_message(gateway, _body_or_empty(request))
    except usecase.GatewayError as exc:
        return _error(exc)
    return JsonResponse({"success": True, **result})

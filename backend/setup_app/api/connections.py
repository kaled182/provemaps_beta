"""Views dos testes de ligação: `/setup_app/api/test-{zabbix,database,redis,ftp,smtp,sms}/`.

Finas de propósito (EV-0017e): a lógica está em `setup_app.usecases.connections`.
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models_audit import ConfigurationAudit
from ..usecases import connections as usecase
from ._auth import staff_required


def _audit(request, section: str, *, success: bool, error_message: str = "") -> None:
    ConfigurationAudit.log_change(
        user=request.user,
        action="test",
        section=section,
        request=request,
        success=success,
        error_message=error_message,
    )


def _run_test(request, section: str, test):
    """Parse JSON → usecase → resposta; audita sucesso e as falhas que trazem `audit`."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    try:
        result = test(data)
    except usecase.ConnectionTestError as exc:
        if exc.audit is not None:
            _audit(request, section, success=False, error_message=exc.audit)
        return JsonResponse({"success": False, "message": str(exc), **exc.extra}, status=exc.status)
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc!s}"}, status=500)
    _audit(request, section, success=True)
    return JsonResponse({"success": True, **result})


@require_POST
@staff_required
def test_zabbix_connection(request):
    return _run_test(request, "Zabbix", usecase.test_zabbix)


@require_POST
@staff_required
def test_database_connection(request):
    return _run_test(request, "Database", usecase.test_database)


@require_POST
@staff_required
def test_redis_connection(request):
    return _run_test(request, "Redis", usecase.test_redis)


@require_POST
@staff_required
def test_ftp_connection(request):
    return _run_test(request, "FTP", usecase.test_ftp)


@require_POST
@staff_required
def test_smtp_connection(request):
    return _run_test(request, "SMTP", usecase.test_smtp)


@require_POST
@staff_required
def test_sms_connection(request):
    """O SMS não é auditado e os provedores por integrar respondem 200 com `success: False`."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    try:
        return JsonResponse(usecase.test_sms(data))
    except usecase.ConnectionTestError as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc!s}"}, status=500)

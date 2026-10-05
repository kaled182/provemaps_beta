"""Views de configuração: `.env`, `get/update_configuration`, exportar/importar, auditoria.

Finas de propósito (EV-0017b): a lógica está em `setup_app.usecases.config`.
"""

from __future__ import annotations

import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ..models_audit import ConfigurationAudit
from ..usecases import config as usecase
from ._auth import staff_required


def _audit(request, action: str, section: str, **kwargs) -> None:
    ConfigurationAudit.log_change(
        user=request.user, action=action, section=section, request=request, **kwargs
    )


def _invalid_json():
    return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)


# ── .env ─────────────────────────────────────────────────────────────────────


@require_GET
@staff_required
def get_env_file(request):
    """Return the raw .env content for editing."""
    try:
        return JsonResponse({"success": True, "content": usecase.read_env_file()})
    except usecase.EnvTooLarge as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Failed to read env file: {exc}"}, status=500
        )


def _write_env_view(request, *, field: str, action: str, ok_message: str, fail_prefix: str):
    try:
        data = json.loads(request.body or "{}")
        try:
            usecase.write_env_file(data.get(field, ""))
        except usecase.ConfigError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        _audit(request, action, "Env File", success=True)
        return JsonResponse({"success": True, "message": ok_message})
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        _audit(request, action, "Env File", success=False, error_message=str(exc))
        return JsonResponse({"success": False, "message": f"{fail_prefix}: {exc}"}, status=500)


@require_POST
@staff_required
def update_env_file(request):
    """Overwrite the .env file with provided content."""
    return _write_env_view(
        request,
        field="content",
        action="update",
        ok_message="Env file updated.",
        fail_prefix="Failed to update env file",
    )


@require_POST
@staff_required
def import_env_backup(request):
    """Restore .env content from a backup metadata file."""
    return _write_env_view(
        request,
        field="env_file",
        action="import",
        ok_message="Env file importado.",
        fail_prefix="Env import failed",
    )


# ── Configuração ─────────────────────────────────────────────────────────────


@require_GET
@staff_required
def get_configuration(request):
    """Get current configuration values."""
    try:
        return JsonResponse({"success": True, "configuration": usecase.get_configuration()})
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc!s}"}, status=500)


@require_POST
@staff_required
def update_configuration(request):
    """Update system configuration (base de dados; o .env é só modelo)."""
    try:
        data = json.loads(request.body)
        try:
            result = usecase.update_configuration(data)
        except usecase.ConfigError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)

        backup_warning = ""
        if result["backup_error"]:
            backup_warning = (
                "Senha atualizada, mas o backup não foi gerado automaticamente. "
                f"Motivo: {result['backup_error']}"
            )
            _audit(
                request, "backup", "Backups", success=False, error_message=result["backup_error"]
            )

        _audit(request, "update", "System Configuration", success=True)

        message = "Configuration updated successfully"
        if backup_warning:
            message = f"{message}. {backup_warning}"
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "backup_warning": bool(backup_warning),
                "backup_message": backup_warning,
                "backup_created": result["backup_created"],
                "backup_filename": result["backup_filename"],
                "gdrive_upload": result["gdrive_upload"],
                "ftp_upload": result["ftp_upload"],
                "restart_triggered": result["restart_triggered"],
            }
        )
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        _audit(request, "update", "System Configuration", success=False, error_message=str(exc))
        return JsonResponse({"success": False, "message": f"Server error: {exc!s}"}, status=500)


@require_GET
@staff_required
def export_configuration(request):
    """Export current configuration as JSON file (segredos redigidos)."""
    try:
        export_data = usecase.export_configuration(request.user.username)
        _audit(request, "export", "All", success=True)
        response = HttpResponse(json.dumps(export_data, indent=2), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="mapsprove_config.json"'
        return response
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Export failed: {exc!s}"}, status=500)


@require_POST
@staff_required
def import_configuration(request):
    """Import configuration from uploaded JSON file."""
    try:
        if "config_file" not in request.FILES:
            return JsonResponse({"success": False, "message": "No file uploaded"}, status=400)
        content = request.FILES["config_file"].read().decode("utf-8")
        try:
            imported = usecase.import_configuration(content)
        except usecase.ConfigError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        _audit(
            request, "import", "All", new_value=f"Imported {len(imported)} settings", success=True
        )
        return JsonResponse(
            {
                "success": True,
                "message": f"Configuration imported successfully! {len(imported)} settings updated.",
                "imported_keys": imported,
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON file"}, status=400)
    except Exception as exc:
        _audit(request, "import", "All", success=False, error_message=str(exc))
        return JsonResponse({"success": False, "message": f"Import failed: {exc!s}"}, status=500)


@require_GET
@staff_required
def get_audit_history(request):
    """Get configuration change history."""
    try:
        limit = int(request.GET.get("limit", 50))
        section = request.GET.get("section", "")
        return JsonResponse({"success": True, "audits": usecase.get_audit_history(limit, section)})
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc!s}"}, status=500)

"""Views de backups e nuvem: `/setup_app/api/backups/*`, `/api/test-gdrive/`, `/api/gdrive/oauth/*`.

Finas de propósito (EV-0017a): a lógica está em `setup_app.usecases.backups`.
"""

from __future__ import annotations

import json
import logging

from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ..models_audit import ConfigurationAudit
from ..usecases import backups as usecase
from ._auth import staff_required

logger = logging.getLogger(__name__)


def _json_body(request) -> dict:
    return json.loads(request.body or "{}")


def _invalid_json():
    return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)


def _audit(request, action: str, section: str = "Backups", **kwargs) -> None:
    ConfigurationAudit.log_change(
        user=request.user, action=action, section=section, request=request, **kwargs
    )


@require_http_methods(["GET", "POST"])
@staff_required
def backups_manager(request):
    """GET lista; POST com ficheiro guarda um upload, sem ficheiro gera um backup novo."""
    if request.method == "GET":
        return JsonResponse({"success": True, **usecase.list_backups()})

    try:
        if request.FILES.get("file"):
            try:
                filename = usecase.store_uploaded_backup(request.FILES["file"])
            except usecase.InvalidBackupFile as exc:
                return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
            _audit(request, "import", new_value=filename, success=True)
            return JsonResponse(
                {"success": True, "message": "Backup enviado", "filename": filename}, status=201
            )

        try:
            result = usecase.create_backup()
        except usecase.BackupToolMissing as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)

        _audit(request, "create", new_value=result["filename"], success=True)
        return JsonResponse({"success": True, "message": "Backup criado", **result}, status=202)
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Backup failed: {exc}"}, status=500)


@require_POST
@staff_required
def restore_backup(request):
    try:
        filename = _json_body(request).get("filename", "")
        try:
            usecase.restore_backup(filename)
        except usecase.BackupError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        _audit(request, "restore", new_value=filename, success=True)
        return JsonResponse({"success": True, "message": "Restauração iniciada."})
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Restore failed: {exc}"}, status=500)


@require_POST
@staff_required
def delete_backup(request):
    try:
        filename = _json_body(request).get("filename", "")
        try:
            usecase.delete_backup(filename)
        except usecase.BackupNotFound as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        _audit(request, "delete", new_value=filename, success=True)
        return JsonResponse({"success": True, "message": "Backup removido."})
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Delete failed: {exc}"}, status=500)


@require_POST
@staff_required
def upload_backup_to_cloud(request):
    try:
        filename = _json_body(request).get("filename", "")
        try:
            result = usecase.upload_existing_backup(filename)
        except usecase.BackupNotFound as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        _audit(request, "upload", new_value=filename or "", success=True)
        return JsonResponse(
            {
                "success": True,
                "message": "Envio iniciado",
                "gdrive_upload": result["gdrive_upload"],
                "ftp_upload": result["ftp_upload"],
            }
        )
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Upload failed: {exc}"}, status=500)


@require_POST
@staff_required
def update_backup_settings(request):
    try:
        data = _json_body(request)
        payload = usecase.update_backup_settings(data)
        _audit(request, "update", new_value=json.dumps(payload), success=True)
        return JsonResponse(
            {
                "success": True,
                "message": "Configurações de backup atualizadas.",
                "settings": payload,
            }
        )
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Update failed: {exc}"}, status=500)


@require_GET
@staff_required
def download_backup(request, filename):
    try:
        backup_path = usecase.backup_download_path(filename)
    except (usecase.BackupNotFound, ValueError):
        return JsonResponse({"success": False, "message": "File not found."}, status=404)
    return FileResponse(backup_path.open("rb"), as_attachment=True, filename=backup_path.name)


# ── Google Drive ─────────────────────────────────────────────────────────────


@require_POST
@staff_required
def test_gdrive(request):
    """Testa a ligação ao Google Drive (conta de serviço ou OAuth)."""
    try:
        result = usecase.gdrive_test(_json_body(request))
        _audit(
            request,
            "test",
            section="Google Drive",
            success=bool(result.get("success")),
            error_message="" if result.get("success") else result.get("message", ""),
        )
        return JsonResponse(result, status=200 if result.get("success") else 400)
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc}"}, status=500)


@require_POST
@staff_required
def start_gdrive_oauth(request):
    """Inicia o OAuth do Drive pessoal; devolve a URL de autorização."""
    try:
        redirect_uri = request.build_absolute_uri(reverse("setup_app:gdrive_oauth_callback"))
        try:
            result = usecase.gdrive_oauth_start(_json_body(request), redirect_uri)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        except usecase.BackupToolMissing as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)
        request.session["gdrive_oauth_state"] = result["state"]
        return JsonResponse({"success": True, "auth_url": result["auth_url"]})
    except json.JSONDecodeError:
        return _invalid_json()
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc}"}, status=500)


@require_GET
@staff_required
def gdrive_oauth_callback(request):
    """Callback do OAuth: guarda o refresh token. Resposta em texto, é uma janela do Google."""
    error = request.GET.get("error")
    if error:
        return HttpResponse(f"Erro OAuth: {error}", status=400)

    state = request.GET.get("state")
    if not state or state != request.session.get("gdrive_oauth_state"):
        return HttpResponse("Estado OAuth inválido.", status=400)

    code = request.GET.get("code", "")
    if not code:
        return HttpResponse("Código OAuth ausente.", status=400)

    redirect_uri = request.build_absolute_uri(reverse("setup_app:gdrive_oauth_callback"))
    try:
        usecase.gdrive_oauth_complete(code, state, redirect_uri)
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    except usecase.BackupToolMissing as exc:
        return HttpResponse(str(exc), status=exc.status)

    return HttpResponse(
        "Conectado ao Google Drive. Pode fechar esta janela.", content_type="text/plain"
    )

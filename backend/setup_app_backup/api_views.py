"""API endpoints for setup configuration testing and management."""

from __future__ import annotations

import io
import logging
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.core.management import call_command
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.urls import reverse

import requests

from integrations.zabbix.zabbix_client import zabbix_request
from integrations.zabbix.guards import reload_diagnostics_flag_cache
from .models import FirstTimeSetup, MonitoringServer, MessagingGateway, CompanyProfile
from .models_audit import ConfigurationAudit
from .services import runtime_settings, video_gateway as video_gateway_service
from .services.cloud_backups import test_gdrive_connection, upload_backup_to_gdrive
from .services.config_loader import clear_runtime_config_cache
from .services.service_reloader import trigger_restart
from .utils import env_manager


logger = logging.getLogger(__name__)


def _staff_check(user):
    """Check if user is staff."""
    return user.is_active and user.is_staff


def _user_can_access_video_gateway(user, gateway: MessagingGateway) -> bool:
    """Validate RBAC for accessing a video gateway."""
    if user.is_superuser:
        return True
    # Gateways without departamentos are considered public
    if not gateway.departments.exists():
        return True
    profile = getattr(user, "profile", None)
    if not profile:
        return False
    user_department_ids = list(profile.departments.values_list("id", flat=True))
    if not user_department_ids:
        return False
    return gateway.departments.filter(id__in=user_department_ids).exists()


BACKUP_DIR = Path(settings.BASE_DIR) / "database" / "backups"
_ALLOWED_BACKUP_EXTENSIONS = {".zip"}
_MIN_BACKUP_PASSWORD_LEN = 8


def _get_db_settings() -> Dict[str, str]:
    keys = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    values = env_manager.read_values(keys)
    missing = [key for key in keys if key != "DB_PASSWORD" and not values.get(key)]
    if missing:
        raise ValueError(f"Missing database settings: {', '.join(missing)}")
    return values


def _safe_backup_path(filename: str) -> Path:
    if not filename:
        raise ValueError("Filename required")
    safe_name = Path(filename).name
    if safe_name != filename:
        raise ValueError("Invalid filename")
    return BACKUP_DIR / safe_name


def _ensure_backup_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _get_backup_password() -> bytes:
    values = env_manager.read_values(["BACKUP_ZIP_PASSWORD"])
    password = values.get("BACKUP_ZIP_PASSWORD", "").strip()
    if len(password) < _MIN_BACKUP_PASSWORD_LEN:
        raise ValueError(
            "A senha do backup precisa ter pelo menos 8 caracteres para criptografar."
        )
    return password.encode("utf-8")


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        return False
    return bool(value)


def _get_or_create_company_profile() -> CompanyProfile:
    profile = CompanyProfile.objects.first()
    if not profile:
        profile = CompanyProfile.objects.create()
    return profile


def _file_info(field, request):
    if not field or not getattr(field, "name", ""):
        return {"name": "", "url": ""}
    try:
        url = field.url
    except Exception:
        url = ""
    if url and request is not None:
        url = request.build_absolute_uri(url)
    return {"name": field.name, "url": url}


def _serialize_company_profile(profile: CompanyProfile, request=None) -> Dict[str, Any]:
    return {
        "company_legal_name": profile.company_legal_name,
        "company_trade_name": profile.company_trade_name,
        "company_doc": profile.company_doc,
        "company_owner_name": profile.company_owner_name,
        "company_owner_doc": profile.company_owner_doc,
        "company_owner_birth": profile.company_owner_birth,
        "company_state_reg": profile.company_state_reg,
        "company_city_reg": profile.company_city_reg,
        "company_fistel": profile.company_fistel,
        "company_created_date": profile.company_created_date,
        "company_active": profile.company_active,
        "company_reports_active": profile.company_reports_active,
        "address_zip": profile.address_zip,
        "address_street": profile.address_street,
        "address_number": profile.address_number,
        "address_district": profile.address_district,
        "address_city": profile.address_city,
        "address_state": profile.address_state,
        "address_country": profile.address_country,
        "address_extra": profile.address_extra,
        "address_reference": profile.address_reference,
        "address_coords": profile.address_coords,
        "address_complex": profile.address_complex,
        "address_ibge": profile.address_ibge,
        "assets_logo": _file_info(profile.assets_logo, request),
        "assets_cert_file": _file_info(profile.assets_cert_file, request),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


def _get_gdrive_settings() -> Dict[str, str]:
    values = env_manager.read_values(
        [
            "GDRIVE_ENABLED",
            "GDRIVE_AUTH_MODE",
            "GDRIVE_CREDENTIALS_JSON",
            "GDRIVE_FOLDER_ID",
            "GDRIVE_SHARED_DRIVE_ID",
            "GDRIVE_OAUTH_CLIENT_ID",
            "GDRIVE_OAUTH_CLIENT_SECRET",
            "GDRIVE_OAUTH_REFRESH_TOKEN",
            "GDRIVE_OAUTH_USER_EMAIL",
        ]
    )
    return {
        "enabled": _to_bool(values.get("GDRIVE_ENABLED", "")),
        "auth_mode": values.get("GDRIVE_AUTH_MODE", "service_account"),
        "credentials": values.get("GDRIVE_CREDENTIALS_JSON", ""),
        "folder_id": values.get("GDRIVE_FOLDER_ID", ""),
        "shared_drive_id": values.get("GDRIVE_SHARED_DRIVE_ID", ""),
        "oauth_client_id": values.get("GDRIVE_OAUTH_CLIENT_ID", ""),
        "oauth_client_secret": values.get("GDRIVE_OAUTH_CLIENT_SECRET", ""),
        "oauth_refresh_token": values.get("GDRIVE_OAUTH_REFRESH_TOKEN", ""),
        "oauth_user_email": values.get("GDRIVE_OAUTH_USER_EMAIL", ""),
    }


def _get_ftp_settings() -> Dict[str, str]:
    values = env_manager.read_values(
        ["FTP_ENABLED", "FTP_HOST", "FTP_PORT", "FTP_USER", "FTP_PASSWORD", "FTP_PATH"]
    )
    return {
        "enabled": _to_bool(values.get("FTP_ENABLED", "")),
        "host": values.get("FTP_HOST", ""),
        "port": values.get("FTP_PORT", ""),
        "user": values.get("FTP_USER", ""),
        "password": values.get("FTP_PASSWORD", ""),
        "path": values.get("FTP_PATH", ""),
    }


def _ensure_ftp_dir(ftp, remote_path: str) -> None:
    if not remote_path:
        return
    normalized = remote_path.strip()
    if not normalized:
        return
    if normalized.startswith("/"):
        ftp.cwd("/")
        normalized = normalized[1:]
    for part in [p for p in normalized.split("/") if p]:
        try:
            ftp.cwd(part)
        except Exception:
            try:
                ftp.mkd(part)
            except Exception:
                pass
            ftp.cwd(part)


def _upload_backup_via_ftp(filename: str, settings_payload: Dict[str, str] | None = None) -> Dict[str, object]:
    if not filename:
        return {"success": False, "message": "Backup filename not available."}
    settings_payload = settings_payload or _get_ftp_settings()
    if not settings_payload.get("enabled"):
        return {"success": False, "message": "FTP desabilitado."}

    backup_path = _safe_backup_path(filename)
    if not backup_path.exists():
        return {"success": False, "message": "Arquivo de backup não encontrado."}

    host = settings_payload.get("host", "")
    if not host:
        return {"success": False, "message": "FTP host não configurado."}

    port_raw = settings_payload.get("port", "")
    try:
        port = int(port_raw) if port_raw else 21
    except ValueError:
        port = 21

    try:
        import ftplib

        ftp = ftplib.FTP()
        ftp.connect(host=host, port=port, timeout=10)
        if settings_payload.get("user") or settings_payload.get("password"):
            ftp.login(user=settings_payload.get("user", ""), passwd=settings_payload.get("password", ""))
        else:
            ftp.login()
        _ensure_ftp_dir(ftp, settings_payload.get("path", ""))
        with backup_path.open("rb") as handler:
            ftp.storbinary(f"STOR {backup_path.name}", handler)
        ftp.quit()
        return {"success": True, "message": "Backup enviado via FTP."}
    except Exception as exc:
        return {"success": False, "message": f"Falha ao enviar via FTP: {exc}"}


def _upload_backup_if_enabled(
    filename: str,
    *,
    enabled: bool | None = None,
    auth_mode: str | None = None,
    credentials_json: str | None = None,
    folder_id: str | None = None,
    shared_drive_id: str | None = None,
    oauth_client_id: str | None = None,
    oauth_client_secret: str | None = None,
    oauth_refresh_token: str | None = None,
) -> Dict[str, object]:
    if not filename:
        return {"success": False, "message": "Backup filename not available."}

    if enabled is not None:
        settings_payload = {
            "enabled": bool(enabled),
            "auth_mode": auth_mode or "service_account",
            "credentials": credentials_json or "",
            "folder_id": folder_id or "",
            "shared_drive_id": shared_drive_id or "",
            "oauth_client_id": oauth_client_id or "",
            "oauth_client_secret": oauth_client_secret or "",
            "oauth_refresh_token": oauth_refresh_token or "",
        }
    else:
        settings_payload = _get_gdrive_settings()
    if not settings_payload["enabled"]:
        return {"success": False, "message": "Google Drive desabilitado."}

    backup_path = _safe_backup_path(filename)
    if not backup_path.exists():
        return {"success": False, "message": "Arquivo de backup não encontrado."}

    return upload_backup_to_gdrive(
        backup_path,
        auth_mode=settings_payload.get("auth_mode", "service_account"),
        credentials_json=settings_payload.get("credentials", "") or "",
        folder_id=settings_payload.get("folder_id", "") or None,
        shared_drive_id=settings_payload.get("shared_drive_id", "") or None,
        oauth_client_id=settings_payload.get("oauth_client_id", "") or "",
        oauth_client_secret=settings_payload.get("oauth_client_secret", "") or "",
        oauth_refresh_token=settings_payload.get("oauth_refresh_token", "") or "",
    )


def _detect_backup_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".config.json"):
        return "config"
    if lower.startswith("manual_backup_") or "manual" in lower:
        return "manual"
    if "auto" in lower or "scheduled" in lower or "snapshot" in lower:
        return "auto"
    if "import" in lower or "upload" in lower:
        return "upload"
    return "unknown"


def _apply_backup_retention() -> None:
    retention_days = env_manager.read_values(["BACKUP_RETENTION_DAYS"]).get("BACKUP_RETENTION_DAYS", "")
    retention_count = env_manager.read_values(["BACKUP_RETENTION_COUNT"]).get("BACKUP_RETENTION_COUNT", "")

    try:
        days = int(retention_days) if retention_days else None
    except ValueError:
        days = None

    try:
        count = int(retention_count) if retention_count else None
    except ValueError:
        count = None

    if not days and not count:
        return

    _ensure_backup_dir()
    files = []
    for path in BACKUP_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in _ALLOWED_BACKUP_EXTENSIONS:
            continue
        try:
            path.stat()
        except FileNotFoundError:
            continue
        files.append(path)

    if days:
        cutoff = datetime.now().timestamp() - (days * 86400)
        for path in files:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)

    if count:
        sortable = []
        for path in files:
            try:
                sortable.append((path.stat().st_mtime, path))
            except FileNotFoundError:
                continue
        sorted_files = sorted(sortable, key=lambda item: item[0], reverse=True)
        for _, path in sorted_files[count:]:
            path.unlink(missing_ok=True)


@require_POST
@login_required
@user_passes_test(_staff_check)
def test_zabbix_connection(request):
    """Test Zabbix API connection with provided credentials."""
    try:
        data = json.loads(request.body)
        zabbix_url = data.get("zabbix_api_url", "").strip()
        auth_type = data.get("auth_type", "login")
        api_key = data.get("zabbix_api_key", "").strip()
        username = data.get("zabbix_api_user", "").strip()
        password = data.get("zabbix_api_password", "").strip()

        if not zabbix_url:
            return JsonResponse(
                {"success": False, "message": "Zabbix URL is required"}, status=400
            )

        # Test connection using direct requests (to test custom credentials)
        try:
            import requests

            def _post(payload, headers=None):
                return requests.post(
                    zabbix_url,
                    json=payload,
                    headers=headers or {"Content-Type": "application/json"},
                    timeout=10,
                )

            # 1) Connectivity check (no auth required)
            payload = {
                "jsonrpc": "2.0",
                "method": "apiinfo.version",
                "params": {},
                "id": 1,
            }

            response = _post(payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error_payload = result.get("error", {})
                error_details = (
                    error_payload.get("data")
                    or error_payload.get("message")
                    or "API error"
                )
                ConfigurationAudit.log_change(
                    user=request.user,
                    action="test",
                    section="Zabbix",
                    request=request,
                    success=False,
                    error_message=error_details,
                )
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Serviço respondeu com erro: {error_details}",
                        "status": "api_error",
                    },
                    status=400,
                )

            version = result.get("result", "Unknown")

            # 2) Optional auth validation (token or login)
            if auth_type == "token" and api_key:
                # Zabbix 7.x+ requer Authorization Bearer header para API Keys
                # O formato "auth" no payload não é mais suportado com tokens
                auth_payload = {
                    "jsonrpc": "2.0",
                    "method": "user.get",
                    "params": {"output": ["userid"]},
                    "id": 2,
                }
                auth_response = _post(
                    auth_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                auth_result = auth_response.json()

                if "error" in auth_result:
                    error_message = auth_result.get("error", {}).get("message", "Unknown error")
                    ConfigurationAudit.log_change(
                        user=request.user,
                        action="test",
                        section="Zabbix",
                        request=request,
                        success=False,
                        error_message=f"Invalid API token: {error_message}",
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Conexão OK, mas o token do Zabbix é inválido.",
                            "status": "auth_failed",
                            "version": version,
                            "error_detail": error_message,
                        },
                        status=400,
                    )

            if auth_type == "login":
                if not username or not password:
                    ConfigurationAudit.log_change(
                        user=request.user,
                        action="test",
                        section="Zabbix",
                        request=request,
                        success=False,
                        error_message="Missing username/password",
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Conexão OK, mas usuário/senha não foram informados.",
                            "status": "auth_missing",
                            "version": version,
                        },
                        status=400,
                    )

                login_payload = {
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {"username": username, "password": password},
                    "id": 2,
                }
                login_response = _post(login_payload)
                login_result = login_response.json()
                if "error" in login_result or not login_result.get("result"):
                    ConfigurationAudit.log_change(
                        user=request.user,
                        action="test",
                        section="Zabbix",
                        request=request,
                        success=False,
                        error_message="Login failed",
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Conexão OK, mas a autenticação falhou.",
                            "status": "auth_failed",
                            "version": version,
                        },
                        status=400,
                    )

            # Log successful test
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Zabbix",
                request=request,
                success=True,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Serviço online. Zabbix v{version}.",
                    "version": version,
                    "status": "online",
                }
            )

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Zabbix",
                request=request,
                success=False,
                error_message=error_msg,
            )
            return JsonResponse(
                {"success": False, "message": f"Serviço offline: {error_msg}", "status": "offline"},
                status=400,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def test_database_connection(request):
    """Test database connection with provided credentials."""
    try:
        data = json.loads(request.body)
        db_host = data.get("db_host", "").strip()
        db_port = data.get("db_port", "").strip()
        db_name = data.get("db_name", "").strip()
        db_user = data.get("db_user", "").strip()
        db_password = data.get("db_password", "").strip()

        if not all([db_host, db_port, db_name, db_user]):
            return JsonResponse(
                {
                    "success": False,
                    "message": "All database fields are required except password",
                },
                status=400,
            )

        # Test connection
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_password,
                database=db_name,
                connect_timeout=5,
            )

            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version_full = cursor.fetchone()[0]
            # Extract PostgreSQL version (e.g., "PostgreSQL 16.1")
            if ',' in version_full:
                version = version_full.split(',')[0]
            else:
                version = version_full
            cursor.close()
            conn.close()

            # Log successful test
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Database",
                request=request,
                success=True,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Connection successful! {version}",
                    "version": version,
                }
            )

        except Exception as e:
            error_msg = str(e)
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Database",
                request=request,
                success=False,
                error_message=error_msg,
            )
            return JsonResponse(
                {"success": False, "message": f"Connection failed: {error_msg}"},
                status=400,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def test_redis_connection(request):
    """Test Redis connection with provided URL."""
    try:
        data = json.loads(request.body)
        redis_url = data.get("redis_url", "").strip()

        if not redis_url:
            return JsonResponse(
                {"success": False, "message": "Redis URL is required"},
                status=400,
            )

        # Test connection
        try:
            import redis
            from urllib.parse import urlparse

            # Parse Redis URL
            parsed = urlparse(redis_url)
            
            # Create Redis client
            r = redis.Redis(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 6379,
                db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                password=parsed.password,
                socket_connect_timeout=5,
            )

            # Test connection with PING
            r.ping()
            
            # Get Redis info
            info = r.info()
            redis_version = info.get('redis_version', 'Unknown')
            
            r.close()

            # Log successful test
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Redis",
                request=request,
                success=True,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Connection successful! Redis version: {redis_version}",
                    "version": redis_version,
                }
            )

        except Exception as e:
            error_msg = str(e)
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="Redis",
                request=request,
                success=False,
                error_message=error_msg,
            )
            return JsonResponse(
                {"success": False, "message": f"Connection failed: {error_msg}"},
                status=400,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def test_ftp_connection(request):
    """Test FTP connection with provided credentials."""
    try:
        data = json.loads(request.body or "{}")
        host = data.get("ftp_host", "").strip()
        port_raw = data.get("ftp_port", "").strip()
        username = data.get("ftp_user", "").strip()
        password = data.get("ftp_password", "").strip()
        remote_path = data.get("ftp_path", "").strip()

        if not host:
            values = env_manager.read_values(
                ["FTP_HOST", "FTP_PORT", "FTP_USER", "FTP_PASSWORD", "FTP_PATH"]
            )
            host = values.get("FTP_HOST", "")
            port_raw = port_raw or values.get("FTP_PORT", "")
            username = username or values.get("FTP_USER", "")
            password = password or values.get("FTP_PASSWORD", "")
            remote_path = remote_path or values.get("FTP_PATH", "")

        if not host:
            return JsonResponse(
                {"success": False, "message": "FTP host is required."},
                status=400,
            )

        try:
            port = int(port_raw) if port_raw else 21
        except ValueError:
            port = 21

        try:
            import ftplib

            ftp = ftplib.FTP()
            ftp.connect(host=host, port=port, timeout=8)
            if username or password:
                ftp.login(user=username, passwd=password)
            else:
                ftp.login()
            if remote_path:
                ftp.cwd(remote_path)
            pwd = ftp.pwd()
            ftp.quit()

            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="FTP",
                request=request,
                success=True,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Connection successful! PWD: {pwd}",
                }
            )
        except Exception as exc:
            error_msg = str(exc)
            ConfigurationAudit.log_change(
                user=request.user,
                action="test",
                section="FTP",
                request=request,
                success=False,
                error_message=error_msg,
            )
            return JsonResponse(
                {"success": False, "message": f"Connection failed: {error_msg}"},
                status=400,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )

@require_POST
@login_required
@user_passes_test(_staff_check)
def test_smtp_connection(request):
    """Test SMTP settings by sending a test email."""
    try:
        data = json.loads(request.body or "{}")
        host = data.get("smtp_host", "").strip()
        port_raw = data.get("smtp_port", "").strip()
        security = data.get("smtp_security", "").strip().lower()
        username = data.get("smtp_user", "").strip()
        password = data.get("smtp_password", "")
        auth_mode = data.get("smtp_auth_mode", "").strip().lower()
        oauth_client_id = data.get("smtp_oauth_client_id", "").strip()
        oauth_client_secret = data.get("smtp_oauth_client_secret", "").strip()
        oauth_refresh_token = data.get("smtp_oauth_refresh_token", "").strip()
        from_name = data.get("smtp_from_name", "").strip()
        from_email = data.get("smtp_from_email", "").strip()
        recipient = data.get("smtp_test_recipient", "").strip()

        values = env_manager.read_values(
            [
                "SMTP_HOST",
                "SMTP_PORT",
                "SMTP_SECURITY",
                "SMTP_USER",
                "SMTP_PASSWORD",
                "SMTP_AUTH_MODE",
                "SMTP_OAUTH_CLIENT_ID",
                "SMTP_OAUTH_CLIENT_SECRET",
                "SMTP_OAUTH_REFRESH_TOKEN",
                "SMTP_FROM_NAME",
                "SMTP_FROM_EMAIL",
                "SMTP_TEST_RECIPIENT",
            ]
        )
        host = host or values.get("SMTP_HOST", "")
        port_raw = port_raw or values.get("SMTP_PORT", "")
        security = security or values.get("SMTP_SECURITY", "")
        username = username or values.get("SMTP_USER", "")
        password = password or values.get("SMTP_PASSWORD", "")
        auth_mode = auth_mode or values.get("SMTP_AUTH_MODE", "")
        oauth_client_id = oauth_client_id or values.get("SMTP_OAUTH_CLIENT_ID", "")
        oauth_client_secret = oauth_client_secret or values.get("SMTP_OAUTH_CLIENT_SECRET", "")
        oauth_refresh_token = oauth_refresh_token or values.get("SMTP_OAUTH_REFRESH_TOKEN", "")
        from_name = from_name or values.get("SMTP_FROM_NAME", "")
        from_email = from_email or values.get("SMTP_FROM_EMAIL", "")
        recipient = recipient or values.get("SMTP_TEST_RECIPIENT", "")

        if not from_email and username:
            from_email = username
        if not auth_mode:
            auth_mode = "password"

        missing = []
        if not host:
            missing.append("host")
        if not from_email:
            missing.append("remetente")
        if not recipient:
            missing.append("destinatário")
        if missing:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Campos obrigatórios ausentes: {', '.join(missing)}.",
                },
                status=400,
            )

        try:
            port = int(port_raw) if port_raw else (465 if security == "ssl" else 587)
        except ValueError:
            port = 587

        import base64
        import smtplib
        import ssl
        from email.message import EmailMessage

        msg = EmailMessage()
        sender = f"{from_name} <{from_email}>" if from_name else from_email
        msg["Subject"] = "Teste SMTP - ProveMaps"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content("Este é um email de teste do ProveMaps.")

        if security == "ssl":
            server = smtplib.SMTP_SSL(
                host=host,
                port=port,
                context=ssl.create_default_context(),
                timeout=10,
            )
            server.ehlo()
        else:
            server = smtplib.SMTP(host=host, port=port, timeout=10)
            server.ehlo()
            if security == "tls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()

        if auth_mode == "oauth":
            if not username:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Informe o usuário (email) para autenticação OAuth.",
                    },
                    status=400,
                )
            if not (oauth_client_id and oauth_client_secret and oauth_refresh_token):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Informe Client ID, Client Secret e Refresh Token do OAuth.",
                    },
                    status=400,
                )
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                None,
                refresh_token=oauth_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                scopes=["https://mail.google.com/"],
            )
            creds.refresh(Request())
            access_token = creds.token
            auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
            auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
            server.docmd("AUTH", "XOAUTH2 " + auth_b64)
        elif username and password:
            server.login(username, password)
        server.send_message(msg)
        server.quit()

        ConfigurationAudit.log_change(
            user=request.user,
            action="test",
            section="SMTP",
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Email enviado com sucesso."})
    except Exception as exc:
        error_msg = str(exc)
        if "5.7.8" in error_msg or "BadCredentials" in error_msg:
            error_msg = (
                "Gmail rejeitou as credenciais. Verifique usuário/senha, ou use "
                "App Password/OAuth. Se for Workspace, considere smtp-relay.gmail.com."
            )
        ConfigurationAudit.log_change(
            user=request.user,
            action="test",
            section="SMTP",
            request=request,
            success=False,
            error_message=str(exc),
        )
        return JsonResponse(
            {"success": False, "message": f"Falha ao enviar email: {error_msg}"},
            status=400,
        )

@require_POST
@login_required
@user_passes_test(_staff_check)
def test_gdrive(request):
    """Test Google Drive connection using Service Account."""
    try:
        data = json.loads(request.body or "{}")
        auth_mode = data.get("gdrive_auth_mode", "").strip()
        credentials_json = data.get("gdrive_credentials_json", "").strip()
        folder_id = data.get("gdrive_folder_id", "").strip()
        shared_drive_id = data.get("gdrive_shared_drive_id", "").strip()
        oauth_client_id = data.get("gdrive_oauth_client_id", "").strip()
        oauth_client_secret = data.get("gdrive_oauth_client_secret", "").strip()

        values = {}
        if not auth_mode or (auth_mode == "service_account" and not credentials_json) or auth_mode == "oauth":
            values = env_manager.read_values(
                [
                    "GDRIVE_AUTH_MODE",
                    "GDRIVE_CREDENTIALS_JSON",
                    "GDRIVE_FOLDER_ID",
                    "GDRIVE_SHARED_DRIVE_ID",
                    "GDRIVE_OAUTH_CLIENT_ID",
                    "GDRIVE_OAUTH_CLIENT_SECRET",
                    "GDRIVE_OAUTH_REFRESH_TOKEN",
                ]
            )
            auth_mode = auth_mode or values.get("GDRIVE_AUTH_MODE", "")
            credentials_json = credentials_json or values.get("GDRIVE_CREDENTIALS_JSON", "")
            folder_id = folder_id or values.get("GDRIVE_FOLDER_ID", "")
            shared_drive_id = shared_drive_id or values.get("GDRIVE_SHARED_DRIVE_ID", "")
            oauth_client_id = oauth_client_id or values.get("GDRIVE_OAUTH_CLIENT_ID", "")
            oauth_client_secret = oauth_client_secret or values.get("GDRIVE_OAUTH_CLIENT_SECRET", "")
            oauth_refresh_token = values.get("GDRIVE_OAUTH_REFRESH_TOKEN", "")
        else:
            oauth_refresh_token = ""

        result = test_gdrive_connection(
            auth_mode=auth_mode or "service_account",
            credentials_json=credentials_json,
            folder_id=folder_id or None,
            shared_drive_id=shared_drive_id or None,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            oauth_refresh_token=oauth_refresh_token,
        )

        ConfigurationAudit.log_change(
            user=request.user,
            action="test",
            section="Google Drive",
            request=request,
            success=bool(result.get("success")),
            error_message="" if result.get("success") else result.get("message", ""),
        )

        status = 200 if result.get("success") else 400
        return JsonResponse(result, status=status)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Server error: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def start_gdrive_oauth(request):
    """Start OAuth flow for personal Google Drive."""
    try:
        data = json.loads(request.body or "{}")
        client_id = data.get("gdrive_oauth_client_id", "").strip()
        client_secret = data.get("gdrive_oauth_client_secret", "").strip()

        if not client_id or not client_secret:
            values = env_manager.read_values(
                ["GDRIVE_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_SECRET"]
            )
            client_id = client_id or values.get("GDRIVE_OAUTH_CLIENT_ID", "")
            client_secret = client_secret or values.get("GDRIVE_OAUTH_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            return JsonResponse(
                {"success": False, "message": "Informe Client ID e Client Secret."},
                status=400,
            )

        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError:
            return JsonResponse(
                {"success": False, "message": "Google OAuth SDK não instalado."},
                status=500,
            )

        env_manager.write_values(
            {
                "GDRIVE_AUTH_MODE": "oauth",
                "GDRIVE_OAUTH_CLIENT_ID": client_id,
                "GDRIVE_OAUTH_CLIENT_SECRET": client_secret,
            }
        )
        FirstTimeSetup.objects.update_or_create(
            configured=True,
            defaults={
                "gdrive_auth_mode": "oauth",
                "gdrive_oauth_client_id": client_id,
                "gdrive_oauth_client_secret": client_secret,
            },
        )

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        redirect_uri = request.build_absolute_uri(reverse("setup_app:gdrive_oauth_callback"))
        flow = Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/drive"],
            redirect_uri=redirect_uri,
        )
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        request.session["gdrive_oauth_state"] = state

        return JsonResponse({"success": True, "auth_url": auth_url})
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Server error: {exc}"},
            status=500,
        )


@require_GET
@login_required
@user_passes_test(_staff_check)
def gdrive_oauth_callback(request):
    """OAuth callback to store refresh token for personal Drive uploads."""
    error = request.GET.get("error")
    if error:
        return HttpResponse(f"Erro OAuth: {error}", status=400)

    state = request.GET.get("state")
    if not state or state != request.session.get("gdrive_oauth_state"):
        return HttpResponse("Estado OAuth inválido.", status=400)

    code = request.GET.get("code", "")
    if not code:
        return HttpResponse("Código OAuth ausente.", status=400)

    values = env_manager.read_values(
        ["GDRIVE_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_SECRET"]
    )
    client_id = values.get("GDRIVE_OAUTH_CLIENT_ID", "")
    client_secret = values.get("GDRIVE_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return HttpResponse("Client ID/Secret não configurados.", status=400)

    try:
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
    except ImportError:
        return HttpResponse("Google OAuth SDK não instalado.", status=500)

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    redirect_uri = request.build_absolute_uri(reverse("setup_app:gdrive_oauth_callback"))
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/drive"],
        state=state,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    refresh_token = creds.refresh_token
    if not refresh_token:
        return HttpResponse("Refresh token não foi retornado.", status=400)

    user_email = ""
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        about = service.about().get(fields="user").execute()
        user_email = (about or {}).get("user", {}).get("emailAddress", "")
    except Exception:
        user_email = ""

    env_manager.write_values(
        {
            "GDRIVE_AUTH_MODE": "oauth",
            "GDRIVE_OAUTH_REFRESH_TOKEN": refresh_token,
            "GDRIVE_OAUTH_USER_EMAIL": user_email,
        }
    )

    FirstTimeSetup.objects.update_or_create(
        configured=True,
        defaults={
            "gdrive_auth_mode": "oauth",
            "gdrive_oauth_refresh_token": refresh_token,
            "gdrive_oauth_user_email": user_email,
        },
    )

    clear_runtime_config_cache()
    runtime_settings.reload_config()

    return HttpResponse(
        "Conectado ao Google Drive. Pode fechar esta janela.",
        content_type="text/plain",
    )

@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def export_configuration(request):
    """Export current configuration as JSON file."""
    try:
        editable_keys = [
            "SECRET_KEY",
            "DEBUG",
            "ZABBIX_API_URL",
            "ZABBIX_API_USER",
            "ZABBIX_API_PASSWORD",
            "ZABBIX_API_KEY",
            "GOOGLE_MAPS_API_KEY",
            "MAP_PROVIDER",
            "MAPBOX_TOKEN",
            # Map configuration - Google Maps
            "MAP_DEFAULT_ZOOM",
            "MAP_DEFAULT_LAT",
            "MAP_DEFAULT_LNG",
            "MAP_TYPE",
            "MAP_STYLES",
            "ENABLE_STREET_VIEW",
            "ENABLE_TRAFFIC",
            # Map configuration - Mapbox
            "MAPBOX_STYLE",
            "MAPBOX_CUSTOM_STYLE",
            "MAPBOX_ENABLE_3D",
            # Map configuration - Esri
            "ESRI_API_KEY",
            "ESRI_BASEMAP",
            # Map configuration - Common
            "MAP_LANGUAGE",
            "MAP_THEME",
            "ENABLE_MAP_CLUSTERING",
            "ENABLE_DRAWING_TOOLS",
            "ENABLE_FULLSCREEN",
            "ALLOWED_HOSTS",
            "ENABLE_DIAGNOSTIC_ENDPOINTS",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_URL",
            "SERVICE_RESTART_COMMANDS",
            "BACKUP_ZIP_PASSWORD",
            "FTP_ENABLED",
            "FTP_HOST",
            "FTP_PORT",
            "FTP_USER",
            "FTP_PASSWORD",
            "FTP_PATH",
            "GDRIVE_ENABLED",
            "GDRIVE_AUTH_MODE",
            "GDRIVE_CREDENTIALS_JSON",
            "GDRIVE_FOLDER_ID",
            "GDRIVE_SHARED_DRIVE_ID",
            "GDRIVE_OAUTH_CLIENT_ID",
            "GDRIVE_OAUTH_CLIENT_SECRET",
            "GDRIVE_OAUTH_REFRESH_TOKEN",
            "GDRIVE_OAUTH_USER_EMAIL",
            "SMTP_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_SECURITY",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_AUTH_MODE",
            "SMTP_OAUTH_CLIENT_ID",
            "SMTP_OAUTH_CLIENT_SECRET",
            "SMTP_OAUTH_REFRESH_TOKEN",
            "SMTP_FROM_NAME",
            "SMTP_FROM_EMAIL",
            "SMTP_TEST_RECIPIENT",
            "SMS_ENABLED",
            "SMS_PROVIDER",
            "SMS_PROVIDER_RANK",
            "SMS_USERNAME",
            "SMS_PASSWORD",
            "SMS_API_TOKEN",
            "SMS_API_URL",
            "SMS_SENDER_ID",
            "SMS_TEST_RECIPIENT",
            "SMS_TEST_MESSAGE",
            "SMS_PRIORITY",
            "SMS_AWS_REGION",
            "SMS_AWS_ACCESS_KEY_ID",
            "SMS_AWS_SECRET_ACCESS_KEY",
            "SMS_INFOBIP_BASE_URL",
        ]

        config_data = env_manager.read_values(editable_keys)

        # Sanitize sensitive data for export
        sensitive_keys = [
            "SECRET_KEY",
            "ZABBIX_API_PASSWORD",
            "ZABBIX_API_KEY",
            "DB_PASSWORD",
            "BACKUP_ZIP_PASSWORD",
            "FTP_PASSWORD",
            "GDRIVE_CREDENTIALS_JSON",
            "GDRIVE_OAUTH_CLIENT_SECRET",
            "GDRIVE_OAUTH_REFRESH_TOKEN",
            "SMTP_PASSWORD",
            "SMTP_OAUTH_CLIENT_SECRET",
            "SMTP_OAUTH_REFRESH_TOKEN",
            "SMS_PASSWORD",
            "SMS_API_TOKEN",
            "SMS_AWS_SECRET_ACCESS_KEY",
        ]
        for key in sensitive_keys:
            if key in config_data and config_data[key]:
                config_data[key] = "***EXPORTED_BUT_REDACTED***"

        export_data = {
            "version": "1.0",
            "exported_by": request.user.username,
            "exported_at": __import__("datetime").datetime.now().isoformat(),
            "configuration": config_data,
        }

        # Log export
        ConfigurationAudit.log_change(
            user=request.user,
            action="export",
            section="All",
            request=request,
            success=True,
        )

        response = HttpResponse(
            json.dumps(export_data, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="mapsprove_config.json"'
        return response

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Export failed: {str(e)}"}, status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def import_configuration(request):
    """Import configuration from uploaded JSON file."""
    try:
        if "config_file" not in request.FILES:
            return JsonResponse(
                {"success": False, "message": "No file uploaded"}, status=400
            )

        config_file = request.FILES["config_file"]
        content = config_file.read().decode("utf-8")
        import_data = json.loads(content)

        if "configuration" not in import_data:
            return JsonResponse(
                {"success": False, "message": "Invalid configuration file format"},
                status=400,
            )

        config = import_data["configuration"]

        # Filter out redacted values
        filtered_config = {
            k: v
            for k, v in config.items()
            if v and v != "***EXPORTED_BUT_REDACTED***"
        }

        # Write to env file
        env_manager.write_values(filtered_config)

        # Log import
        ConfigurationAudit.log_change(
            user=request.user,
            action="import",
            section="All",
            new_value=f"Imported {len(filtered_config)} settings",
            request=request,
            success=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Configuration imported successfully! {len(filtered_config)} settings updated.",
                "imported_keys": list(filtered_config.keys()),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON file"}, status=400
        )
    except Exception as e:
        ConfigurationAudit.log_change(
            user=request.user,
            action="import",
            section="All",
            request=request,
            success=False,
            error_message=str(e),
        )
        return JsonResponse(
            {"success": False, "message": f"Import failed: {str(e)}"}, status=500
        )


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def get_audit_history(request):
    """Get configuration change history."""
    try:
        limit = int(request.GET.get("limit", 50))
        section = request.GET.get("section", "")

        queryset = ConfigurationAudit.objects.all()

        if section:
            queryset = queryset.filter(section=section)

        audits = queryset[:limit]

        audit_data = [
            {
                "id": audit.id,
                "user": audit.user.username if audit.user else "Anonymous",
                "action": audit.get_action_display(),
                "section": audit.section,
                "field_name": audit.field_name,
                "old_value": audit.old_value,
                "new_value": audit.new_value,
                "success": audit.success,
                "error_message": audit.error_message,
                "timestamp": audit.timestamp.isoformat(),
                "ip_address": audit.ip_address,
            }
            for audit in audits
        ]

        return JsonResponse({"success": True, "audits": audit_data})

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def test_sms_connection(request):
    """Test SMS settings by sending a test message."""
    try:
        data = json.loads(request.body or "{}")
        provider = data.get("sms_provider", "").strip().lower() or "smsnet"
        username = data.get("sms_username", "").strip()
        password = data.get("sms_password", "")
        api_token = data.get("sms_api_token", "").strip()
        api_url = data.get("sms_api_url", "").strip()
        sender_id = data.get("sms_sender_id", "").strip()
        test_recipient = data.get("sms_test_recipient", "").strip()
        test_message = data.get("sms_test_message", "").strip() or "Teste SMS ProveMaps."
        priority = data.get("sms_priority", "").strip()
        infobip_base_url = data.get("sms_infobip_base_url", "").strip()
        aws_region = data.get("sms_aws_region", "").strip()
        aws_access_key = data.get("sms_aws_access_key_id", "").strip()
        aws_secret = data.get("sms_aws_secret_access_key", "").strip()

        values = env_manager.read_values(
            [
                "SMS_PROVIDER",
                "SMS_USERNAME",
                "SMS_PASSWORD",
                "SMS_API_TOKEN",
                "SMS_API_URL",
                "SMS_SENDER_ID",
                "SMS_TEST_RECIPIENT",
                "SMS_TEST_MESSAGE",
                "SMS_PRIORITY",
                "SMS_INFOBIP_BASE_URL",
                "SMS_AWS_REGION",
                "SMS_AWS_ACCESS_KEY_ID",
                "SMS_AWS_SECRET_ACCESS_KEY",
            ]
        )
        provider = provider or values.get("SMS_PROVIDER", "smsnet")
        username = username or values.get("SMS_USERNAME", "")
        password = password or values.get("SMS_PASSWORD", "")
        api_token = api_token or values.get("SMS_API_TOKEN", "")
        api_url = api_url or values.get("SMS_API_URL", "")
        sender_id = sender_id or values.get("SMS_SENDER_ID", "")
        test_recipient = test_recipient or values.get("SMS_TEST_RECIPIENT", "")
        test_message = test_message or values.get("SMS_TEST_MESSAGE", "")
        priority = priority or values.get("SMS_PRIORITY", "")
        infobip_base_url = infobip_base_url or values.get("SMS_INFOBIP_BASE_URL", "")
        aws_region = aws_region or values.get("SMS_AWS_REGION", "")
        aws_access_key = aws_access_key or values.get("SMS_AWS_ACCESS_KEY_ID", "")
        aws_secret = aws_secret or values.get("SMS_AWS_SECRET_ACCESS_KEY", "")

        def _normalize_br_phone(raw: str) -> str:
            digits = re.sub(r"\\D", "", raw or "")
            if digits.startswith("55") and len(digits) in (12, 13):
                return digits
            if len(digits) in (10, 11):
                return f"55{digits}"
            return ""

        import re

        normalized_phone = _normalize_br_phone(test_recipient)
        if not normalized_phone:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Telefone inválido. Use DDD + número (10 ou 11 dígitos), com ou sem 55.",
                },
                status=400,
            )
        test_recipient = normalized_phone

        if provider == "smsnet":
            if not username or not password:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Usuário e senha são obrigatórios para SMSNET.",
                    },
                    status=400,
                )
            if not api_url:
                api_url = "https://sistema.smsnet.com.br/sms/global"

            import requests

            params = {
                "username": username,
                "password": password,
                "to": test_recipient,
                "msg": test_message,
            }
            if priority:
                params["priority"] = priority

            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code != 200:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Falha no envio SMSNET: HTTP {response.status_code}.",
                    },
                    status=400,
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "SMS enviado com sucesso (SMSNET).",
                }
            )

        if provider == "zenvia":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Integração Zenvia disponível para configuração. Envio será habilitado na próxima etapa.",
                }
            )

        if provider == "totalvoice":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Integração TotalVoice disponível para configuração. Envio será habilitado na próxima etapa.",
                }
            )

        if provider == "aws_sns":
            missing = [name for name, value in {
                "região": aws_region,
                "access key": aws_access_key,
                "secret key": aws_secret,
            }.items() if not value]
            if missing:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Campos obrigatórios ausentes: {', '.join(missing)}.",
                    },
                    status=400,
                )
            return JsonResponse(
                {
                    "success": False,
                    "message": "Integração AWS SNS disponível para configuração. Envio será habilitado na próxima etapa.",
                }
            )

        if provider == "infobip":
            missing = [name for name, value in {
                "base URL": infobip_base_url,
                "API token": api_token,
            }.items() if not value]
            if missing:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Campos obrigatórios ausentes: {', '.join(missing)}.",
                    },
                    status=400,
                )
            return JsonResponse(
                {
                    "success": False,
                    "message": "Integração Infobip disponível para configuração. Envio será habilitado na próxima etapa.",
                }
            )

        return JsonResponse(
            {"success": False, "message": "Provedor SMS não reconhecido."},
            status=400,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def get_configuration(request):
    """Get current configuration values."""
    try:
        editable_keys = [
            "SECRET_KEY",
            "DEBUG",
            "ZABBIX_API_URL",
            "ZABBIX_API_USER",
            "ZABBIX_API_PASSWORD",
            "ZABBIX_API_KEY",
            "GOOGLE_MAPS_API_KEY",
            "MAP_PROVIDER",
            "MAPBOX_TOKEN",
            # Map configuration - Google Maps
            "MAP_DEFAULT_ZOOM",
            "MAP_DEFAULT_LAT",
            "MAP_DEFAULT_LNG",
            "MAP_TYPE",
            "MAP_STYLES",
            "ENABLE_STREET_VIEW",
            "ENABLE_TRAFFIC",
            # Map configuration - Mapbox
            "MAPBOX_STYLE",
            "MAPBOX_CUSTOM_STYLE",
            "MAPBOX_ENABLE_3D",
            # Map configuration - Esri
            "ESRI_API_KEY",
            "ESRI_BASEMAP",
            # Map configuration - Common
            "MAP_LANGUAGE",
            "MAP_THEME",
            "ENABLE_MAP_CLUSTERING",
            "ENABLE_DRAWING_TOOLS",
            "ENABLE_FULLSCREEN",
            "ALLOWED_HOSTS",
            "ENABLE_DIAGNOSTIC_ENDPOINTS",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_URL",
            "SERVICE_RESTART_COMMANDS",
            "BACKUP_ZIP_PASSWORD",
            "FTP_ENABLED",
            "FTP_HOST",
            "FTP_PORT",
            "FTP_USER",
            "FTP_PASSWORD",
            "FTP_PATH",
            "GDRIVE_ENABLED",
            "GDRIVE_AUTH_MODE",
            "GDRIVE_CREDENTIALS_JSON",
            "GDRIVE_FOLDER_ID",
            "GDRIVE_SHARED_DRIVE_ID",
            "GDRIVE_OAUTH_CLIENT_ID",
            "GDRIVE_OAUTH_CLIENT_SECRET",
            "GDRIVE_OAUTH_USER_EMAIL",
            "SMTP_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_SECURITY",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_AUTH_MODE",
            "SMTP_OAUTH_CLIENT_ID",
            "SMTP_OAUTH_CLIENT_SECRET",
            "SMTP_OAUTH_REFRESH_TOKEN",
            "SMTP_FROM_NAME",
            "SMTP_FROM_EMAIL",
            "SMTP_TEST_RECIPIENT",
            "SMS_ENABLED",
            "SMS_PROVIDER",
            "SMS_PROVIDER_RANK",
            "SMS_USERNAME",
            "SMS_PASSWORD",
            "SMS_API_TOKEN",
            "SMS_API_URL",
            "SMS_SENDER_ID",
            "SMS_TEST_RECIPIENT",
            "SMS_TEST_MESSAGE",
            "SMS_PRIORITY",
            "SMS_AWS_REGION",
            "SMS_AWS_ACCESS_KEY_ID",
            "SMS_AWS_SECRET_ACCESS_KEY",
            "SMS_INFOBIP_BASE_URL",
            # Network thresholds
            "OPTICAL_RX_WARNING_THRESHOLD",
            "OPTICAL_RX_CRITICAL_THRESHOLD",
            # Backup automation
            "BACKUP_AUTO_ENABLED",
            "BACKUP_FREQUENCY",
            "BACKUP_RETENTION_DAYS",
            "BACKUP_CLOUD_UPLOAD",
            "BACKUP_CLOUD_PROVIDER",
            "BACKUP_CLOUD_PATH",
        ]
        current_values = env_manager.read_values(editable_keys)
        runtime_config = runtime_settings.get_runtime_config()
        allowed_hosts_fallback = ",".join(runtime_config.allowed_hosts)

        fallback_values = {
            "SECRET_KEY": getattr(settings, "SECRET_KEY", ""),
            "DEBUG": getattr(settings, "DEBUG", False),
            "ZABBIX_API_URL": runtime_config.zabbix_api_url,
            "ZABBIX_API_USER": runtime_config.zabbix_api_user,
            "ZABBIX_API_PASSWORD": runtime_config.zabbix_api_password,
            "ZABBIX_API_KEY": runtime_config.zabbix_api_key,
            "GOOGLE_MAPS_API_KEY": runtime_config.google_maps_api_key,
            "MAP_PROVIDER": runtime_config.map_provider or "google",
            "MAPBOX_TOKEN": runtime_config.mapbox_token,
            # Map configuration defaults - Google Maps
            "MAP_DEFAULT_ZOOM": "12",
            "MAP_DEFAULT_LAT": "-15.7801",
            "MAP_DEFAULT_LNG": "-47.9292",
            "MAP_TYPE": "terrain",
            "MAP_STYLES": "",
            "ENABLE_STREET_VIEW": True,
            "ENABLE_TRAFFIC": False,
            # Map configuration defaults - Mapbox
            "MAPBOX_STYLE": "mapbox://styles/mapbox/streets-v12",
            "MAPBOX_CUSTOM_STYLE": "",
            "MAPBOX_ENABLE_3D": False,
            # Map configuration defaults - Esri
            "ESRI_API_KEY": "",
            "ESRI_BASEMAP": "streets",
            # Map configuration defaults - Common
            "MAP_LANGUAGE": "pt-BR",
            "MAP_THEME": "light",
            "ENABLE_MAP_CLUSTERING": True,
            "ENABLE_DRAWING_TOOLS": True,
            "ENABLE_FULLSCREEN": True,
            "ALLOWED_HOSTS": allowed_hosts_fallback,
            "ENABLE_DIAGNOSTIC_ENDPOINTS": runtime_config.diagnostics_enabled,
            "DB_HOST": runtime_config.db_host,
            "DB_PORT": runtime_config.db_port,
            "DB_NAME": runtime_config.db_name,
            "DB_USER": runtime_config.db_user,
            "DB_PASSWORD": runtime_config.db_password,
            "REDIS_URL": runtime_config.redis_url,
            "SERVICE_RESTART_COMMANDS": getattr(settings, "SERVICE_RESTART_COMMANDS", ""),
            "BACKUP_ZIP_PASSWORD": current_values.get("BACKUP_ZIP_PASSWORD", ""),
            "FTP_ENABLED": runtime_config.ftp_enabled,
            "FTP_HOST": runtime_config.ftp_host,
            "FTP_PORT": runtime_config.ftp_port,
            "FTP_USER": runtime_config.ftp_user,
            "FTP_PASSWORD": runtime_config.ftp_password,
            "FTP_PATH": runtime_config.ftp_path,
            "GDRIVE_ENABLED": runtime_config.gdrive_enabled,
            "GDRIVE_AUTH_MODE": runtime_config.gdrive_auth_mode,
            "GDRIVE_CREDENTIALS_JSON": runtime_config.gdrive_credentials_json,
            "GDRIVE_FOLDER_ID": runtime_config.gdrive_folder_id,
            "GDRIVE_SHARED_DRIVE_ID": runtime_config.gdrive_shared_drive_id,
            "GDRIVE_OAUTH_CLIENT_ID": runtime_config.gdrive_oauth_client_id,
            "GDRIVE_OAUTH_CLIENT_SECRET": runtime_config.gdrive_oauth_client_secret,
            "GDRIVE_OAUTH_USER_EMAIL": runtime_config.gdrive_oauth_user_email,
            "SMTP_ENABLED": runtime_config.smtp_enabled,
            "SMTP_HOST": runtime_config.smtp_host,
            "SMTP_PORT": runtime_config.smtp_port,
            "SMTP_SECURITY": runtime_config.smtp_security,
            "SMTP_USER": runtime_config.smtp_user,
            "SMTP_PASSWORD": runtime_config.smtp_password,
            "SMTP_AUTH_MODE": runtime_config.smtp_auth_mode,
            "SMTP_OAUTH_CLIENT_ID": runtime_config.smtp_oauth_client_id,
            "SMTP_OAUTH_CLIENT_SECRET": runtime_config.smtp_oauth_client_secret,
            "SMTP_OAUTH_REFRESH_TOKEN": runtime_config.smtp_oauth_refresh_token,
            "SMTP_FROM_NAME": runtime_config.smtp_from_name,
            "SMTP_FROM_EMAIL": runtime_config.smtp_from_email,
            "SMTP_TEST_RECIPIENT": runtime_config.smtp_test_recipient,
            "SMS_ENABLED": runtime_config.sms_enabled,
            "SMS_PROVIDER": runtime_config.sms_provider,
            "SMS_PROVIDER_RANK": runtime_config.sms_provider_rank,
            "SMS_USERNAME": runtime_config.sms_username,
            "SMS_PASSWORD": runtime_config.sms_password,
            "SMS_API_TOKEN": runtime_config.sms_api_token,
            "SMS_API_URL": runtime_config.sms_api_url,
            "SMS_SENDER_ID": runtime_config.sms_sender_id,
            "SMS_TEST_RECIPIENT": runtime_config.sms_test_recipient,
            "SMS_TEST_MESSAGE": runtime_config.sms_test_message,
            "SMS_PRIORITY": runtime_config.sms_priority,
            "SMS_AWS_REGION": runtime_config.sms_aws_region,
            "SMS_AWS_ACCESS_KEY_ID": runtime_config.sms_aws_access_key_id,
            "SMS_AWS_SECRET_ACCESS_KEY": runtime_config.sms_aws_secret_access_key,
            "SMS_INFOBIP_BASE_URL": runtime_config.sms_infobip_base_url,
            # Defaults for network thresholds if not configured
            "OPTICAL_RX_WARNING_THRESHOLD": "-24",
            "OPTICAL_RX_CRITICAL_THRESHOLD": "-27",
            # Backup automation defaults
            "BACKUP_AUTO_ENABLED": False,
            "BACKUP_FREQUENCY": "weekly",
            "BACKUP_RETENTION_DAYS": "30",
            "BACKUP_CLOUD_UPLOAD": False,
            "BACKUP_CLOUD_PROVIDER": "google_drive",
            "BACKUP_CLOUD_PATH": "/backups/provemaps",
        }

        # Convert boolean strings to actual booleans for JSON, fallback to runtime/config defaults
        config_data = {}
        for key in editable_keys:
            value = current_values.get(key, "")
            if value == "":
                value = fallback_values.get(key, "")
            if key in ["DEBUG", "ENABLE_DIAGNOSTIC_ENDPOINTS", "FTP_ENABLED", "GDRIVE_ENABLED", "SMTP_ENABLED", "SMS_ENABLED", "BACKUP_AUTO_ENABLED", "BACKUP_CLOUD_UPLOAD", "ENABLE_STREET_VIEW", "ENABLE_TRAFFIC", "MAPBOX_ENABLE_3D", "ENABLE_MAP_CLUSTERING", "ENABLE_DRAWING_TOOLS", "ENABLE_FULLSCREEN"]:
                if isinstance(value, bool):
                    config_data[key] = value
                else:
                    config_data[key] = str(value).lower() == "true" if value else False
            else:
                config_data[key] = value or ""

        oauth_token = env_manager.read_values(["GDRIVE_OAUTH_REFRESH_TOKEN"]).get(
            "GDRIVE_OAUTH_REFRESH_TOKEN", ""
        )
        config_data["GDRIVE_OAUTH_CONNECTED"] = bool(oauth_token)
        
        return JsonResponse({
            "success": True,
            "configuration": config_data
        })

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, 
            status=500
        )


@require_GET
@login_required
@user_passes_test(_staff_check)
def get_company_profile(request):
    """Get company registration data."""
    try:
        profile = _get_or_create_company_profile()
        return JsonResponse(
            {"success": True, "profile": _serialize_company_profile(profile, request=request)}
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Server error: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def update_company_profile(request):
    """Update company registration data."""
    try:
        profile = _get_or_create_company_profile()
        content_type = request.content_type or ""
        if content_type.startswith("multipart/form-data"):
            data = request.POST
        else:
            data = json.loads(request.body or "{}")

        field_map = [
            "company_legal_name",
            "company_trade_name",
            "company_doc",
            "company_owner_name",
            "company_owner_doc",
            "company_owner_birth",
            "company_state_reg",
            "company_city_reg",
            "company_fistel",
            "company_created_date",
            "address_zip",
            "address_street",
            "address_number",
            "address_district",
            "address_city",
            "address_state",
            "address_country",
            "address_extra",
            "address_reference",
            "address_coords",
            "address_complex",
            "address_ibge",
        ]

        for field in field_map:
            if field in data:
                setattr(profile, field, (data.get(field) or "").strip())

        if "company_active" in data:
            profile.company_active = _to_bool(data.get("company_active"))
        if "company_reports_active" in data:
            profile.company_reports_active = _to_bool(data.get("company_reports_active"))

        files = request.FILES
        if "assets_logo" in files:
            profile.assets_logo = files["assets_logo"]
        if "assets_cert_file" in files:
            profile.assets_cert_file = files["assets_cert_file"]
        if "assets_cert_password" in data and data.get("assets_cert_password"):
            profile.assets_cert_password = data.get("assets_cert_password") or ""

        profile.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Cadastro atualizado.",
                "profile": _serialize_company_profile(profile, request=request),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "JSON inválido."},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Server error: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def update_configuration(request):
    """Update system configuration (save to .env and database)."""
    try:
        data = json.loads(request.body)

        # Read existing values from .env to allow partial updates
        all_possible_keys = [
            "SECRET_KEY", "ZABBIX_API_URL", "ZABBIX_API_USER", "ZABBIX_API_PASSWORD",
            "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "GOOGLE_MAPS_API_KEY", "MAP_PROVIDER", "MAPBOX_TOKEN", "ALLOWED_HOSTS",
        ]
        existing_values = env_manager.read_values(all_possible_keys)
        
        # Validate required fields - use existing values if not provided in request
        required_fields = [
            "SECRET_KEY", "ZABBIX_API_URL", "DB_HOST", 
            "DB_PORT", "DB_NAME", "DB_USER"
        ]
        
        missing_fields = []
        for field in required_fields:
            # Check if field is provided in request OR exists in .env
            value_from_request = data.get(field, "").strip()
            value_from_env = existing_values.get(field, "").strip()
            if not value_from_request and not value_from_env:
                missing_fields.append(field)
        
        if missing_fields:
            return JsonResponse({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=400)

        existing_backup_password = env_manager.read_values(["BACKUP_ZIP_PASSWORD"]).get(
            "BACKUP_ZIP_PASSWORD", ""
        )
        backup_zip_password = data.get("BACKUP_ZIP_PASSWORD", "").strip()
        if backup_zip_password and len(backup_zip_password) < _MIN_BACKUP_PASSWORD_LEN:
            return JsonResponse(
                {
                    "success": False,
                    "message": "A senha do backup precisa ter pelo menos 8 caracteres.",
                },
                status=400,
            )
        if backup_zip_password == "":
            backup_zip_password = existing_backup_password

        # Step 1: Write to .env file
        existing_oauth = env_manager.read_values(
            [
                "GDRIVE_OAUTH_REFRESH_TOKEN",
                "GDRIVE_OAUTH_USER_EMAIL",
                "GDRIVE_OAUTH_CLIENT_ID",
                "GDRIVE_OAUTH_CLIENT_SECRET",
            ]
        )
        ftp_port_raw = data.get("FTP_PORT", "").strip()
        try:
            ftp_port_value = int(ftp_port_raw) if ftp_port_raw else 21
        except ValueError:
            ftp_port_value = 21

        existing_smtp = env_manager.read_values(
            [
                "SMTP_PASSWORD",
            ]
        )
        existing_sms = env_manager.read_values(
            [
                "SMS_PASSWORD",
                "SMS_API_TOKEN",
                "SMS_AWS_SECRET_ACCESS_KEY",
            ]
        )
        existing_smtp_oauth = env_manager.read_values(
            [
                "SMTP_AUTH_MODE",
                "SMTP_OAUTH_CLIENT_ID",
                "SMTP_OAUTH_CLIENT_SECRET",
                "SMTP_OAUTH_REFRESH_TOKEN",
            ]
        )
        smtp_password = data.get("SMTP_PASSWORD", "")
        if smtp_password == "":
            smtp_password = existing_smtp.get("SMTP_PASSWORD", "")
        sms_provider_rank = data.get("SMS_PROVIDER_RANK", "").strip()
        try:
            sms_provider_rank_value = int(sms_provider_rank) if sms_provider_rank else 1
        except ValueError:
            sms_provider_rank_value = 1
        if sms_provider_rank_value < 1:
            sms_provider_rank_value = 1
        if sms_provider_rank_value > 5:
            sms_provider_rank_value = 5
        sms_password = data.get("SMS_PASSWORD", "")
        if sms_password == "":
            sms_password = existing_sms.get("SMS_PASSWORD", "")
        sms_api_token = data.get("SMS_API_TOKEN", "")
        if sms_api_token == "":
            sms_api_token = existing_sms.get("SMS_API_TOKEN", "")
        sms_aws_secret_access_key = data.get("SMS_AWS_SECRET_ACCESS_KEY", "")
        if sms_aws_secret_access_key == "":
            sms_aws_secret_access_key = existing_sms.get("SMS_AWS_SECRET_ACCESS_KEY", "")

        # Parse thresholds (optional numbers)
        def _parse_float_str(value, default):
            try:
                v = float(str(value).strip())
                return str(v)
            except Exception:
                return str(default)

        payload = {
            "SECRET_KEY": data.get("SECRET_KEY") or existing_values.get("SECRET_KEY", ""),
            "DEBUG": "True" if _to_bool(data.get("DEBUG", False)) else "False",
            "ZABBIX_API_URL": data.get("ZABBIX_API_URL") or existing_values.get("ZABBIX_API_URL", ""),
            "ZABBIX_API_USER": data.get("ZABBIX_API_USER") or existing_values.get("ZABBIX_API_USER", ""),
            "ZABBIX_API_PASSWORD": data.get("ZABBIX_API_PASSWORD") or existing_values.get("ZABBIX_API_PASSWORD", ""),
            "ZABBIX_API_KEY": data.get("ZABBIX_API_KEY", "").strip(),
            "GOOGLE_MAPS_API_KEY": data.get("GOOGLE_MAPS_API_KEY", "").strip(),
            "MAP_PROVIDER": data.get("MAP_PROVIDER", "google").strip() or "google",
            "MAPBOX_TOKEN": data.get("MAPBOX_TOKEN", "").strip(),
            # Map configuration - Google Maps
            "MAP_DEFAULT_ZOOM": data.get("MAP_DEFAULT_ZOOM", "12").strip() or "12",
            "MAP_DEFAULT_LAT": data.get("MAP_DEFAULT_LAT", "-15.7801").strip() or "-15.7801",
            "MAP_DEFAULT_LNG": data.get("MAP_DEFAULT_LNG", "-47.9292").strip() or "-47.9292",
            "MAP_TYPE": data.get("MAP_TYPE", "terrain").strip() or "terrain",
            "MAP_STYLES": data.get("MAP_STYLES", "").strip(),
            "ENABLE_STREET_VIEW": "True" if _to_bool(data.get("ENABLE_STREET_VIEW", True)) else "False",
            "ENABLE_TRAFFIC": "True" if _to_bool(data.get("ENABLE_TRAFFIC", False)) else "False",
            # Map configuration - Mapbox
            "MAPBOX_STYLE": data.get("MAPBOX_STYLE", "mapbox://styles/mapbox/streets-v12").strip() or "mapbox://styles/mapbox/streets-v12",
            "MAPBOX_CUSTOM_STYLE": data.get("MAPBOX_CUSTOM_STYLE", "").strip(),
            "MAPBOX_ENABLE_3D": "True" if _to_bool(data.get("MAPBOX_ENABLE_3D", False)) else "False",
            # Map configuration - Esri
            "ESRI_API_KEY": data.get("ESRI_API_KEY", "").strip(),
            "ESRI_BASEMAP": data.get("ESRI_BASEMAP", "streets").strip() or "streets",
            # Map configuration - Common
            "MAP_LANGUAGE": data.get("MAP_LANGUAGE", "pt-BR").strip() or "pt-BR",
            "MAP_THEME": data.get("MAP_THEME", "light").strip() or "light",
            "ENABLE_MAP_CLUSTERING": "True" if _to_bool(data.get("ENABLE_MAP_CLUSTERING", True)) else "False",
            "ENABLE_DRAWING_TOOLS": "True" if _to_bool(data.get("ENABLE_DRAWING_TOOLS", True)) else "False",
            "ENABLE_FULLSCREEN": "True" if _to_bool(data.get("ENABLE_FULLSCREEN", True)) else "False",
            "ALLOWED_HOSTS": data.get("ALLOWED_HOSTS") or existing_values.get("ALLOWED_HOSTS", ""),
            "ENABLE_DIAGNOSTIC_ENDPOINTS": (
                "True" if _to_bool(data.get("ENABLE_DIAGNOSTIC_ENDPOINTS", False)) 
                else "False"
            ),
            "DB_HOST": data.get("DB_HOST") or existing_values.get("DB_HOST", ""),
            "DB_PORT": data.get("DB_PORT") or existing_values.get("DB_PORT", ""),
            "DB_NAME": data.get("DB_NAME") or existing_values.get("DB_NAME", ""),
            "DB_USER": data.get("DB_USER") or existing_values.get("DB_USER", ""),
            "DB_PASSWORD": data.get("DB_PASSWORD") or existing_values.get("DB_PASSWORD", ""),
            "REDIS_URL": data.get("REDIS_URL", "").strip(),
            "SERVICE_RESTART_COMMANDS": data.get(
                "SERVICE_RESTART_COMMANDS", ""
            ).strip(),
            "BACKUP_ZIP_PASSWORD": backup_zip_password,
            "FTP_ENABLED": "True" if _to_bool(data.get("FTP_ENABLED", False)) else "False",
            "FTP_HOST": data.get("FTP_HOST", "").strip(),
            "FTP_PORT": str(ftp_port_value),
            "FTP_USER": data.get("FTP_USER", "").strip(),
            "FTP_PASSWORD": data.get("FTP_PASSWORD", "").strip(),
            "FTP_PATH": data.get("FTP_PATH", "").strip() or "/backups/",
            "GDRIVE_ENABLED": "True" if _to_bool(data.get("GDRIVE_ENABLED", False)) else "False",
            "GDRIVE_AUTH_MODE": data.get("GDRIVE_AUTH_MODE", "").strip() or "service_account",
            "GDRIVE_CREDENTIALS_JSON": data.get("GDRIVE_CREDENTIALS_JSON", "").strip(),
            "GDRIVE_FOLDER_ID": data.get("GDRIVE_FOLDER_ID", "").strip(),
            "GDRIVE_SHARED_DRIVE_ID": data.get("GDRIVE_SHARED_DRIVE_ID", "").strip(),
            "GDRIVE_OAUTH_CLIENT_ID": data.get("GDRIVE_OAUTH_CLIENT_ID", "").strip()
            or existing_oauth.get("GDRIVE_OAUTH_CLIENT_ID", ""),
            "GDRIVE_OAUTH_CLIENT_SECRET": data.get("GDRIVE_OAUTH_CLIENT_SECRET", "").strip()
            or existing_oauth.get("GDRIVE_OAUTH_CLIENT_SECRET", ""),
            "GDRIVE_OAUTH_REFRESH_TOKEN": existing_oauth.get("GDRIVE_OAUTH_REFRESH_TOKEN", ""),
            "GDRIVE_OAUTH_USER_EMAIL": existing_oauth.get("GDRIVE_OAUTH_USER_EMAIL", ""),
            "SMTP_ENABLED": "True" if _to_bool(data.get("SMTP_ENABLED", False)) else "False",
            "SMTP_HOST": data.get("SMTP_HOST", "").strip(),
            "SMTP_PORT": data.get("SMTP_PORT", "").strip(),
            "SMTP_SECURITY": data.get("SMTP_SECURITY", "").strip(),
            "SMTP_USER": data.get("SMTP_USER", "").strip(),
            "SMTP_PASSWORD": smtp_password,
            "SMTP_AUTH_MODE": data.get("SMTP_AUTH_MODE", "").strip()
            or existing_smtp_oauth.get("SMTP_AUTH_MODE", "password"),
            "SMTP_OAUTH_CLIENT_ID": data.get("SMTP_OAUTH_CLIENT_ID", "").strip()
            or existing_smtp_oauth.get("SMTP_OAUTH_CLIENT_ID", ""),
            "SMTP_OAUTH_CLIENT_SECRET": data.get("SMTP_OAUTH_CLIENT_SECRET", "").strip()
            or existing_smtp_oauth.get("SMTP_OAUTH_CLIENT_SECRET", ""),
            "SMTP_OAUTH_REFRESH_TOKEN": data.get("SMTP_OAUTH_REFRESH_TOKEN", "").strip()
            or existing_smtp_oauth.get("SMTP_OAUTH_REFRESH_TOKEN", ""),
            "SMTP_FROM_NAME": data.get("SMTP_FROM_NAME", "").strip(),
            "SMTP_FROM_EMAIL": data.get("SMTP_FROM_EMAIL", "").strip(),
            "SMTP_TEST_RECIPIENT": data.get("SMTP_TEST_RECIPIENT", "").strip(),
            "SMS_ENABLED": "True" if _to_bool(data.get("SMS_ENABLED", False)) else "False",
            "SMS_PROVIDER": data.get("SMS_PROVIDER", "").strip() or "smsnet",
            "SMS_PROVIDER_RANK": str(sms_provider_rank_value),
            "SMS_USERNAME": data.get("SMS_USERNAME", "").strip(),
            "SMS_PASSWORD": sms_password,
            "SMS_API_TOKEN": sms_api_token,
            "SMS_API_URL": data.get("SMS_API_URL", "").strip(),
            "SMS_SENDER_ID": data.get("SMS_SENDER_ID", "").strip(),
            "SMS_TEST_RECIPIENT": data.get("SMS_TEST_RECIPIENT", "").strip(),
            "SMS_TEST_MESSAGE": data.get("SMS_TEST_MESSAGE", "").strip(),
            "SMS_PRIORITY": data.get("SMS_PRIORITY", "").strip(),
            "SMS_AWS_REGION": data.get("SMS_AWS_REGION", "").strip(),
            "SMS_AWS_ACCESS_KEY_ID": data.get("SMS_AWS_ACCESS_KEY_ID", "").strip(),
            "SMS_AWS_SECRET_ACCESS_KEY": sms_aws_secret_access_key,
            "SMS_INFOBIP_BASE_URL": data.get("SMS_INFOBIP_BASE_URL", "").strip(),
            # Network thresholds
            "OPTICAL_RX_WARNING_THRESHOLD": _parse_float_str(
                data.get("OPTICAL_RX_WARNING_THRESHOLD", "-24"), -24
            ),
            "OPTICAL_RX_CRITICAL_THRESHOLD": _parse_float_str(
                data.get("OPTICAL_RX_CRITICAL_THRESHOLD", "-27"), -27
            ),
        }

        smtp_enabled = _to_bool(payload["SMTP_ENABLED"])
        smtp_security = (payload["SMTP_SECURITY"] or "").lower()
        if smtp_enabled:
            from_email = payload["SMTP_FROM_EMAIL"] or payload["SMTP_USER"]
            email_payload = {
                "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "EMAIL_HOST": payload["SMTP_HOST"],
                "EMAIL_PORT": payload["SMTP_PORT"] or "587",
                "EMAIL_HOST_USER": payload["SMTP_USER"],
                "EMAIL_HOST_PASSWORD": payload["SMTP_PASSWORD"],
                "EMAIL_USE_TLS": "True" if smtp_security == "tls" else "False",
                "EMAIL_USE_SSL": "True" if smtp_security == "ssl" else "False",
                "DEFAULT_FROM_EMAIL": from_email,
                "SERVER_EMAIL": from_email,
            }
            payload.update(email_payload)
        else:
            payload.update(
                {
                    "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
                    "EMAIL_HOST": "",
                    "EMAIL_PORT": "",
                    "EMAIL_HOST_USER": "",
                    "EMAIL_HOST_PASSWORD": "",
                    "EMAIL_USE_TLS": "False",
                    "EMAIL_USE_SSL": "False",
                }
            )
        
        env_manager.write_values(payload)
        os.environ["OPTICAL_RX_WARNING_THRESHOLD"] = payload["OPTICAL_RX_WARNING_THRESHOLD"]
        os.environ["OPTICAL_RX_CRITICAL_THRESHOLD"] = payload["OPTICAL_RX_CRITICAL_THRESHOLD"]
        settings.EMAIL_BACKEND = payload.get("EMAIL_BACKEND", settings.EMAIL_BACKEND)
        settings.EMAIL_HOST = payload.get("EMAIL_HOST", settings.EMAIL_HOST)
        settings.EMAIL_PORT = int(payload["EMAIL_PORT"]) if payload.get("EMAIL_PORT") else settings.EMAIL_PORT
        settings.EMAIL_HOST_USER = payload.get("EMAIL_HOST_USER", settings.EMAIL_HOST_USER)
        settings.EMAIL_HOST_PASSWORD = payload.get("EMAIL_HOST_PASSWORD", settings.EMAIL_HOST_PASSWORD)
        settings.EMAIL_USE_TLS = payload.get("EMAIL_USE_TLS", "False").lower() == "true"
        settings.EMAIL_USE_SSL = payload.get("EMAIL_USE_SSL", "False").lower() == "true"
        settings.DEFAULT_FROM_EMAIL = payload.get("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)
        settings.SERVER_EMAIL = payload.get("SERVER_EMAIL", settings.SERVER_EMAIL)
        os.environ["SERVICE_RESTART_COMMANDS"] = payload["SERVICE_RESTART_COMMANDS"]
        try:
            settings.OPTICAL_RX_WARNING_THRESHOLD = float(payload["OPTICAL_RX_WARNING_THRESHOLD"])
        except (TypeError, ValueError):
            settings.OPTICAL_RX_WARNING_THRESHOLD = -24.0
        try:
            settings.OPTICAL_RX_CRITICAL_THRESHOLD = float(payload["OPTICAL_RX_CRITICAL_THRESHOLD"])
        except (TypeError, ValueError):
            settings.OPTICAL_RX_CRITICAL_THRESHOLD = -27.0

        # Step 2: Persist to database
        auth_type = "token" if payload["ZABBIX_API_KEY"] else "login"
        
        FirstTimeSetup.objects.update_or_create(
            configured=True,
            defaults={
                "company_name": "MapsproveFiber",
                "zabbix_url": payload["ZABBIX_API_URL"],
                "auth_type": auth_type,
                "zabbix_api_key": (
                    payload["ZABBIX_API_KEY"] if auth_type == "token" else None
                ),
                "zabbix_user": (
                    payload["ZABBIX_API_USER"] if auth_type == "login" else None
                ),
                "zabbix_password": (
                    payload["ZABBIX_API_PASSWORD"] if auth_type == "login" 
                    else None
                ),
                "maps_api_key": payload["GOOGLE_MAPS_API_KEY"],
                "map_provider": payload["MAP_PROVIDER"],
                "mapbox_token": payload["MAPBOX_TOKEN"],
                # Map configuration - Google Maps
                "map_default_zoom": int(payload.get("MAP_DEFAULT_ZOOM", 12)),
                "map_default_lat": float(payload.get("MAP_DEFAULT_LAT", -15.7801)),
                "map_default_lng": float(payload.get("MAP_DEFAULT_LNG", -47.9292)),
                "map_type": payload.get("MAP_TYPE", "terrain"),
                "map_styles": payload.get("MAP_STYLES", ""),
                "enable_street_view": _to_bool(payload.get("ENABLE_STREET_VIEW", True)),
                "enable_traffic": _to_bool(payload.get("ENABLE_TRAFFIC", False)),
                # Map configuration - Mapbox
                "mapbox_style": payload.get("MAPBOX_STYLE", "mapbox://styles/mapbox/streets-v12"),
                "mapbox_custom_style": payload.get("MAPBOX_CUSTOM_STYLE", ""),
                "mapbox_enable_3d": _to_bool(payload.get("MAPBOX_ENABLE_3D", False)),
                # Map configuration - Esri
                "esri_api_key": payload.get("ESRI_API_KEY", ""),
                "esri_basemap": payload.get("ESRI_BASEMAP", "streets"),
                # Map configuration - Common
                "map_language": payload.get("MAP_LANGUAGE", "pt-BR"),
                "map_theme": payload.get("MAP_THEME", "light"),
                "enable_map_clustering": _to_bool(payload.get("ENABLE_MAP_CLUSTERING", True)),
                "enable_drawing_tools": _to_bool(payload.get("ENABLE_DRAWING_TOOLS", True)),
                "enable_fullscreen": _to_bool(payload.get("ENABLE_FULLSCREEN", True)),
                "db_host": payload["DB_HOST"],
                "db_port": payload["DB_PORT"],
                "db_name": payload["DB_NAME"],
                "db_user": payload["DB_USER"],
                "db_password": payload["DB_PASSWORD"],
                "redis_url": payload["REDIS_URL"],
                "ftp_enabled": _to_bool(payload["FTP_ENABLED"]),
                "ftp_host": payload["FTP_HOST"],
                "ftp_port": ftp_port_value,
                "ftp_user": payload["FTP_USER"],
                "ftp_password": payload["FTP_PASSWORD"],
                "ftp_path": payload["FTP_PATH"],
                "gdrive_enabled": _to_bool(payload["GDRIVE_ENABLED"]),
                "gdrive_auth_mode": payload["GDRIVE_AUTH_MODE"],
                "gdrive_credentials_json": payload["GDRIVE_CREDENTIALS_JSON"],
                "gdrive_folder_id": payload["GDRIVE_FOLDER_ID"],
                "gdrive_shared_drive_id": payload["GDRIVE_SHARED_DRIVE_ID"],
                "gdrive_oauth_client_id": payload["GDRIVE_OAUTH_CLIENT_ID"],
                "gdrive_oauth_client_secret": payload["GDRIVE_OAUTH_CLIENT_SECRET"],
                "gdrive_oauth_refresh_token": payload["GDRIVE_OAUTH_REFRESH_TOKEN"],
                "gdrive_oauth_user_email": payload["GDRIVE_OAUTH_USER_EMAIL"],
                "smtp_enabled": _to_bool(payload["SMTP_ENABLED"]),
                "smtp_host": payload["SMTP_HOST"],
                "smtp_port": payload["SMTP_PORT"],
                "smtp_security": payload["SMTP_SECURITY"],
                "smtp_user": payload["SMTP_USER"],
                "smtp_password": payload["SMTP_PASSWORD"],
                "smtp_auth_mode": payload["SMTP_AUTH_MODE"],
                "smtp_oauth_client_id": payload["SMTP_OAUTH_CLIENT_ID"],
                "smtp_oauth_client_secret": payload["SMTP_OAUTH_CLIENT_SECRET"],
                "smtp_oauth_refresh_token": payload["SMTP_OAUTH_REFRESH_TOKEN"],
                "smtp_from_name": payload["SMTP_FROM_NAME"],
                "smtp_from_email": payload["SMTP_FROM_EMAIL"],
                "smtp_test_recipient": payload["SMTP_TEST_RECIPIENT"],
                "sms_enabled": _to_bool(payload["SMS_ENABLED"]),
                "sms_provider": payload["SMS_PROVIDER"],
                "sms_provider_rank": sms_provider_rank_value,
                "sms_username": payload["SMS_USERNAME"],
                "sms_password": payload["SMS_PASSWORD"],
                "sms_api_token": payload["SMS_API_TOKEN"],
                "sms_api_url": payload["SMS_API_URL"],
                "sms_sender_id": payload["SMS_SENDER_ID"],
                "sms_test_recipient": payload["SMS_TEST_RECIPIENT"],
                "sms_test_message": payload["SMS_TEST_MESSAGE"],
                "sms_priority": payload["SMS_PRIORITY"],
                "sms_aws_region": payload["SMS_AWS_REGION"],
                "sms_aws_access_key_id": payload["SMS_AWS_ACCESS_KEY_ID"],
                "sms_aws_secret_access_key": payload["SMS_AWS_SECRET_ACCESS_KEY"],
                "sms_infobip_base_url": payload["SMS_INFOBIP_BASE_URL"],
            }
        )

        # Step 3: Clear caches
        clear_runtime_config_cache()
        runtime_settings.reload_config()
        
        from integrations.zabbix.zabbix_service import clear_token_cache
        clear_token_cache()
        reload_diagnostics_flag_cache()

        # Step 4: Trigger service restart if configured
        restart_triggered = False
        if payload["SERVICE_RESTART_COMMANDS"]:
            restart_triggered = trigger_restart()

        backup_warning = ""
        gdrive_upload = None
        ftp_upload = None
        backup_created = False
        backup_filename = ""
        # Step 5: Trigger a new backup if the password changed
        if backup_zip_password != existing_backup_password:
            try:
                backup_filename = call_command("make_backup") or ""
                backup_created = True
                gdrive_upload = _upload_backup_if_enabled(
                    backup_filename,
                    enabled=_to_bool(payload["GDRIVE_ENABLED"]),
                    auth_mode=payload["GDRIVE_AUTH_MODE"],
                    credentials_json=payload["GDRIVE_CREDENTIALS_JSON"],
                    folder_id=payload["GDRIVE_FOLDER_ID"],
                    shared_drive_id=payload["GDRIVE_SHARED_DRIVE_ID"],
                    oauth_client_id=payload["GDRIVE_OAUTH_CLIENT_ID"],
                    oauth_client_secret=payload["GDRIVE_OAUTH_CLIENT_SECRET"],
                    oauth_refresh_token=payload["GDRIVE_OAUTH_REFRESH_TOKEN"],
                )
                ftp_upload = _upload_backup_via_ftp(
                    backup_filename,
                    {
                        "enabled": _to_bool(payload["FTP_ENABLED"]),
                        "host": payload["FTP_HOST"],
                        "port": payload["FTP_PORT"],
                        "user": payload["FTP_USER"],
                        "password": payload["FTP_PASSWORD"],
                        "path": payload["FTP_PATH"],
                    },
                )
            except Exception as exc:
                backup_warning = (
                    "Senha atualizada, mas o backup não foi gerado automaticamente. "
                    f"Motivo: {exc}"
                )
                ConfigurationAudit.log_change(
                    user=request.user,
                    action="backup",
                    section="Backups",
                    request=request,
                    success=False,
                    error_message=str(exc),
                )

        # Log success
        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="System Configuration",
            request=request,
            success=True,
        )

        message = "Configuration updated successfully"
        if backup_warning:
            message = f"{message}. {backup_warning}"

        return JsonResponse({
            "success": True,
            "message": message,
            "backup_warning": bool(backup_warning),
            "backup_message": backup_warning,
            "backup_created": backup_created,
            "backup_filename": backup_filename,
            "gdrive_upload": gdrive_upload or {},
            "ftp_upload": ftp_upload or {},
            "restart_triggered": restart_triggered,
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, 
            status=400
        )
    except Exception as e:
        # Log failure
        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="System Configuration",
            request=request,
            success=False,
            error_message=str(e),
        )
        
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, 
            status=500
        )


def _serialize_monitoring_server(server: MonitoringServer) -> Dict[str, Any]:
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


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(_staff_check)
def monitoring_servers(request):
    if request.method == "GET":
        servers = MonitoringServer.objects.all().order_by("-is_active", "name")
        return JsonResponse({
            "success": True,
            "servers": [_serialize_monitoring_server(server) for server in servers],
        })

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )

    name = data.get("name", "").strip()
    url = data.get("url", "").strip()
    server_type = data.get("server_type", "zabbix").strip() or "zabbix"
    auth_token = data.get("auth_token", "").strip()
    extra_config = data.get("extra_config", {}) if isinstance(data.get("extra_config"), dict) else {}
    is_active = bool(data.get("is_active", True))

    if not name or not url:
        return JsonResponse(
            {"success": False, "message": "Name and URL are required."},
            status=400,
        )

    server = MonitoringServer.objects.create(
        name=name,
        url=url,
        server_type=server_type,
        auth_token=auth_token or None,
        is_active=is_active,
        extra_config=extra_config,
    )

    return JsonResponse({
        "success": True,
        "server": _serialize_monitoring_server(server),
    })


@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
@login_required
@user_passes_test(_staff_check)
def monitoring_server_detail(request, server_id: int):
    try:
        server = MonitoringServer.objects.get(id=server_id)
    except MonitoringServer.DoesNotExist:
        return JsonResponse({"success": False, "message": "Server not found."}, status=404)

    if request.method == "GET":
        return JsonResponse({"success": True, "server": _serialize_monitoring_server(server)})

    if request.method == "DELETE":
        server.delete()
        return JsonResponse({"success": True, "message": "Server removed."})

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )

    if "name" in data:
        server.name = data.get("name", "").strip() or server.name
    if "url" in data:
        server.url = data.get("url", "").strip() or server.url
    if "server_type" in data:
        server.server_type = data.get("server_type", "zabbix").strip() or server.server_type
    if "is_active" in data:
        server.is_active = bool(data.get("is_active"))
    if "extra_config" in data and isinstance(data.get("extra_config"), dict):
        server.extra_config = data.get("extra_config") or {}

    if "auth_token" in data:
        token = data.get("auth_token", "")
        if token == "":
            server.auth_token = None
        elif token != "********":
            server.auth_token = token

    server.save()

    return JsonResponse({"success": True, "server": _serialize_monitoring_server(server)})


def _serialize_gateway(gateway: MessagingGateway) -> Dict[str, Any]:
    serialized = {
        "id": gateway.id,
        "name": gateway.name,
        "gateway_type": gateway.gateway_type,
        "provider": gateway.provider or "",
        "priority": gateway.priority,
        "enabled": gateway.enabled,
        "is_active": gateway.enabled,  # Alias for frontend compatibility
        "site_name": gateway.site_name or "",
        "config": gateway.config or {},
        "created_at": gateway.created_at.isoformat(),
        "updated_at": gateway.updated_at.isoformat(),
    }
    
    # Para gateways de vídeo, adicionar playback_url automaticamente
    if gateway.gateway_type == "video":
        try:
            playback_url = video_gateway_service.build_playback_url(gateway)
            if playback_url:
                serialized["playback_url"] = playback_url
        except Exception:
            pass  # Se falhar, apenas não adiciona o campo
    
    return serialized


def _ensure_default_gateways() -> None:
    runtime_config = runtime_settings.get_runtime_config()

    has_sms = MessagingGateway.objects.filter(gateway_type="sms").exists()
    if not has_sms:
        sms_filled = any(
            [
                runtime_config.sms_provider,
                runtime_config.sms_username,
                runtime_config.sms_api_url,
                runtime_config.sms_sender_id,
                runtime_config.sms_enabled,
            ]
        )
        if sms_filled:
            MessagingGateway.objects.create(
                name=(runtime_config.sms_provider or "SMSNET").upper(),
                gateway_type="sms",
                provider=runtime_config.sms_provider or "smsnet",
                priority=int(runtime_config.sms_provider_rank or 1),
                enabled=bool(runtime_config.sms_enabled),
                config={
                    "username": runtime_config.sms_username or "",
                    "password": runtime_config.sms_password or "",
                    "api_token": runtime_config.sms_api_token or "",
                    "api_url": runtime_config.sms_api_url or "",
                    "sender_id": runtime_config.sms_sender_id or "",
                    "test_recipient": runtime_config.sms_test_recipient or "",
                    "test_message": runtime_config.sms_test_message or "",
                    "aws_region": runtime_config.sms_aws_region or "",
                    "aws_access_key_id": runtime_config.sms_aws_access_key_id or "",
                    "aws_secret_access_key": runtime_config.sms_aws_secret_access_key or "",
                    "infobip_base_url": runtime_config.sms_infobip_base_url or "",
                },
            )

    has_smtp = MessagingGateway.objects.filter(gateway_type="smtp").exists()
    if not has_smtp:
        smtp_filled = any(
            [
                runtime_config.smtp_host,
                runtime_config.smtp_user,
                runtime_config.smtp_from_email,
                runtime_config.smtp_enabled,
            ]
        )
        if smtp_filled:
            MessagingGateway.objects.create(
                name="SMTP Principal",
                gateway_type="smtp",
                provider="smtp",
                priority=1,
                enabled=bool(runtime_config.smtp_enabled),
                config={
                    "host": runtime_config.smtp_host or "",
                    "port": runtime_config.smtp_port or "",
                    "security": runtime_config.smtp_security or "",
                    "user": runtime_config.smtp_user or "",
                    "password": runtime_config.smtp_password or "",
                    "auth_mode": runtime_config.smtp_auth_mode or "password",
                    "from_name": runtime_config.smtp_from_name or "",
                    "from_email": runtime_config.smtp_from_email or "",
                    "test_recipient": runtime_config.smtp_test_recipient or "",
                    "oauth_client_id": runtime_config.smtp_oauth_client_id or "",
                    "oauth_client_secret": runtime_config.smtp_oauth_client_secret or "",
                    "oauth_refresh_token": runtime_config.smtp_oauth_refresh_token or "",
                },
            )


def _sync_gateway_env(gateway_type: str) -> None:
    if gateway_type not in {"sms", "smtp"}:
        return
    active = (
        MessagingGateway.objects.filter(gateway_type=gateway_type, enabled=True)
        .order_by("priority", "id")
        .first()
    )
    if not active:
        if MessagingGateway.objects.filter(gateway_type=gateway_type).exists():
            if gateway_type == "sms":
                env_manager.write_values({"SMS_ENABLED": "False"})
            else:
                env_manager.write_values({"SMTP_ENABLED": "False"})
            clear_runtime_config_cache()
            runtime_settings.reload_config()
        return

    if gateway_type == "sms":
        config = active.config or {}
        payload = {
            "SMS_ENABLED": "True" if active.enabled else "False",
            "SMS_PROVIDER": active.provider or "smsnet",
            "SMS_PROVIDER_RANK": str(active.priority or 1),
            "SMS_USERNAME": config.get("username", ""),
            "SMS_PASSWORD": config.get("password", ""),
            "SMS_API_TOKEN": config.get("api_token", ""),
            "SMS_API_URL": config.get("api_url", ""),
            "SMS_SENDER_ID": config.get("sender_id", ""),
            "SMS_TEST_RECIPIENT": config.get("test_recipient", ""),
            "SMS_TEST_MESSAGE": config.get("test_message", ""),
            "SMS_PRIORITY": config.get("priority", ""),
            "SMS_AWS_REGION": config.get("aws_region", ""),
            "SMS_AWS_ACCESS_KEY_ID": config.get("aws_access_key_id", ""),
            "SMS_AWS_SECRET_ACCESS_KEY": config.get("aws_secret_access_key", ""),
            "SMS_INFOBIP_BASE_URL": config.get("infobip_base_url", ""),
        }
        env_manager.write_values(payload)
        clear_runtime_config_cache()
        runtime_settings.reload_config()
        return

    config = active.config or {}
    security = (config.get("security") or "tls").lower()
    from_email = config.get("from_email") or config.get("user") or ""
    payload = {
        "SMTP_ENABLED": "True" if active.enabled else "False",
        "SMTP_HOST": config.get("host", ""),
        "SMTP_PORT": str(config.get("port", "")),
        "SMTP_SECURITY": security,
        "SMTP_USER": config.get("user", ""),
        "SMTP_PASSWORD": config.get("password", ""),
        "SMTP_AUTH_MODE": config.get("auth_mode", "password"),
        "SMTP_OAUTH_CLIENT_ID": config.get("oauth_client_id", ""),
        "SMTP_OAUTH_CLIENT_SECRET": config.get("oauth_client_secret", ""),
        "SMTP_OAUTH_REFRESH_TOKEN": config.get("oauth_refresh_token", ""),
        "SMTP_FROM_NAME": config.get("from_name", ""),
        "SMTP_FROM_EMAIL": config.get("from_email", ""),
        "SMTP_TEST_RECIPIENT": config.get("test_recipient", ""),
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": config.get("host", ""),
        "EMAIL_PORT": str(config.get("port", "")),
        "EMAIL_HOST_USER": config.get("user", ""),
        "EMAIL_HOST_PASSWORD": config.get("password", ""),
        "EMAIL_USE_TLS": "True" if security == "tls" else "False",
        "EMAIL_USE_SSL": "True" if security == "ssl" else "False",
        "DEFAULT_FROM_EMAIL": from_email,
        "SERVER_EMAIL": from_email,
    }
    env_manager.write_values(payload)
    clear_runtime_config_cache()
    runtime_settings.reload_config()


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(_staff_check)
def messaging_gateways(request):
    if request.method == "GET":
        _ensure_default_gateways()
        
        # Filtrar por departamentos do usuário (apenas para câmeras de vídeo)
        if request.user.is_superuser:
            # Superuser vê todos os gateways
            gateways = MessagingGateway.objects.all().order_by("gateway_type", "priority", "name")
        else:
            # Usuários normais veem:
            # - Todos os gateways que NÃO são de vídeo (sms, whatsapp, telegram, smtp)
            # - Câmeras de vídeo dos seus departamentos OU públicas (sem departamento)
            user_depts = request.user.profile.departments.all()
            
            gateways = MessagingGateway.objects.filter(
                Q(gateway_type__in=['sms', 'whatsapp', 'telegram', 'smtp']) |  # Não-vídeo: sempre visível
                Q(gateway_type='video', departments__in=user_depts) |  # Vídeo: departamentos do usuário
                Q(gateway_type='video', departments__isnull=True)  # Vídeo: público
            ).distinct().order_by("gateway_type", "priority", "name")
        
        return JsonResponse(
            {"success": True, "gateways": [_serialize_gateway(gw) for gw in gateways]}
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )

    gateway_type = data.get("gateway_type", "").strip()
    if gateway_type not in {"sms", "whatsapp", "telegram", "smtp", "video"}:
        return JsonResponse(
            {"success": False, "message": "Tipo de gateway inválido."}, status=400
        )

    name = data.get("name", "").strip()
    if not name:
        return JsonResponse(
            {"success": False, "message": "Nome do gateway é obrigatório."}, status=400
        )

    try:
        priority = int(data.get("priority", 1))
    except (TypeError, ValueError):
        priority = 1
    if priority < 1:
        priority = 1

    config = data.get("config", {}) if isinstance(data.get("config"), dict) else {}
    gateway = MessagingGateway.objects.create(
        name=name,
        gateway_type=gateway_type,
        provider=data.get("provider", "").strip() or None,
        priority=priority,
        enabled=bool(data.get("enabled", True)),
        site_name=data.get("site_name", "").strip() or None,
        config=config,
    )

    _sync_gateway_env(gateway.gateway_type)

    return JsonResponse({"success": True, "gateway": _serialize_gateway(gateway)})


def _get_whatsapp_qr_service_url(gateway: MessagingGateway) -> str:
    config = gateway.config or {}
    service_url = config.get("qr_service_url", "").strip()
    if service_url:
        return service_url
    values = env_manager.read_values(["WHATSAPP_QR_SERVICE_URL"])
    return values.get("WHATSAPP_QR_SERVICE_URL", "").strip()


def _update_gateway_qr_state(
    gateway: MessagingGateway, status: str, qr_image_url: str | None
) -> None:
    merged = dict(gateway.config or {})
    if status:
        merged["qr_status"] = status
    if qr_image_url is not None:
        merged["qr_image_url"] = qr_image_url
    gateway.config = merged
    gateway.save(update_fields=["config", "updated_at"])


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def whatsapp_qr_start(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway WhatsApp não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    if config.get("auth_mode") != "qr":
        return JsonResponse(
            {"success": False, "message": "Gateway não está em modo QR Code."},
            status=400,
        )

    service_url = _get_whatsapp_qr_service_url(gateway)
    if not service_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Serviço de QR Code não configurado.",
            },
            status=400,
        )

    try:
        import requests

        extra_url = ""
        try:
            payload = json.loads(request.body or "{}")
            extra_url = payload.get("qr_service_url", "").strip()
        except json.JSONDecodeError:
            extra_url = ""
        if extra_url:
            service_url = extra_url

        response = requests.post(
            f"{service_url.rstrip('/')}/qr/start",
            json={
                "gateway_id": gateway.id,
                "name": gateway.name,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        return JsonResponse(
            {
                "success": False,
                "message": f"Falha ao gerar QR: {exc}",
            },
            status=400,
        )

    qr_image_url = data.get("qr_image_url")
    if qr_image_url is None:
        qr_image_url = data.get("qr")
    status = data.get("status") or data.get("qr_status") or "pending"
    _update_gateway_qr_state(gateway, status, qr_image_url)

    return JsonResponse(
        {
            "success": True,
            "qr_image_url": qr_image_url,
            "qr_status": status,
            "last_disconnect_reason": data.get("last_disconnect_reason"),
            "last_disconnect_message": data.get("last_disconnect_message", ""),
            "message": data.get("message", "QR gerado."),
        }
    )


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def whatsapp_qr_status(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway WhatsApp não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    if config.get("auth_mode") != "qr":
        return JsonResponse(
            {"success": False, "message": "Gateway não está em modo QR Code."},
            status=400,
        )

    service_url = _get_whatsapp_qr_service_url(gateway)
    if not service_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Serviço de QR Code não configurado.",
            },
            status=400,
        )

    try:
        import requests

        extra_url = request.GET.get("qr_service_url", "").strip()
        if extra_url:
            service_url = extra_url

        response = requests.get(
            f"{service_url.rstrip('/')}/qr/status",
            params={"gateway_id": gateway.id},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        return JsonResponse(
            {
                "success": False,
                "message": f"Falha ao consultar status: {exc}",
            },
            status=400,
        )

    qr_image_url = data.get("qr_image_url")
    if qr_image_url is None:
        qr_image_url = data.get("qr")
    status = data.get("status") or data.get("qr_status") or "pending"
    if status in {"connected", "disconnected"} and not qr_image_url:
        qr_image_url = ""
    _update_gateway_qr_state(gateway, status, qr_image_url)

    return JsonResponse(
        {
            "success": True,
            "qr_image_url": qr_image_url,
            "qr_status": status,
            "last_disconnect_reason": data.get("last_disconnect_reason"),
            "last_disconnect_message": data.get("last_disconnect_message", ""),
            "message": data.get("message", "Status atualizado."),
        }
    )


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def whatsapp_qr_disconnect(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway WhatsApp não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    if config.get("auth_mode") != "qr":
        return JsonResponse(
            {"success": False, "message": "Gateway não está em modo QR Code."},
            status=400,
        )

    service_url = _get_whatsapp_qr_service_url(gateway)
    if not service_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Serviço de QR Code não configurado.",
            },
            status=400,
        )

    try:
        import requests

        extra_url = ""
        try:
            payload = json.loads(request.body or "{}")
            extra_url = payload.get("qr_service_url", "").strip()
        except json.JSONDecodeError:
            extra_url = ""
        if extra_url:
            service_url = extra_url

        response = requests.post(
            f"{service_url.rstrip('/')}/qr/disconnect",
            json={"gateway_id": gateway.id},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Falha ao desconectar: {exc}"},
            status=400,
        )

    status = data.get("status") or data.get("qr_status") or "disconnected"
    _update_gateway_qr_state(gateway, status, "")

    return JsonResponse(
        {
            "success": True,
            "qr_status": status,
            "last_disconnect_reason": data.get("last_disconnect_reason"),
            "last_disconnect_message": data.get("last_disconnect_message", ""),
            "message": data.get("message", "Desconectado."),
        }
    )


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def whatsapp_qr_reset(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway WhatsApp não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    if config.get("auth_mode") != "qr":
        return JsonResponse(
            {"success": False, "message": "Gateway não está em modo QR Code."},
            status=400,
        )

    service_url = _get_whatsapp_qr_service_url(gateway)
    if not service_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Serviço de QR Code não configurado.",
            },
            status=400,
        )

    try:
        import requests

        extra_url = ""
        try:
            payload = json.loads(request.body or "{}")
            extra_url = payload.get("qr_service_url", "").strip()
        except json.JSONDecodeError:
            extra_url = ""
        if extra_url:
            service_url = extra_url

        response = requests.post(
            f"{service_url.rstrip('/')}/qr/reset",
            json={"gateway_id": gateway.id},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Falha ao resetar: {exc}"},
            status=400,
        )

    _update_gateway_qr_state(gateway, "pending", "")

    return JsonResponse(
        {
            "success": True,
            "qr_status": "pending",
            "message": data.get("message", "Sessão resetada."),
        }
    )


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def whatsapp_qr_test_message(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway WhatsApp não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    if config.get("auth_mode") != "qr":
        return JsonResponse(
            {"success": False, "message": "Gateway não está em modo QR Code."},
            status=400,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    recipient = (payload.get("recipient") or config.get("test_recipient") or "").strip()
    message = (payload.get("message") or config.get("test_message") or "").strip()
    if not message:
        message = "Teste WhatsApp ProveMaps."

    if not recipient:
        return JsonResponse(
            {"success": False, "message": "Informe o telefone de teste."},
            status=400,
        )

    service_url = _get_whatsapp_qr_service_url(gateway)
    extra_url = (payload.get("qr_service_url") or "").strip()
    if extra_url:
        service_url = extra_url
    if not service_url:
        return JsonResponse(
            {"success": False, "message": "Serviço de QR Code não configurado."},
            status=400,
        )

    try:
        import requests

        response = requests.post(
            f"{service_url.rstrip('/')}/message/test",
            json={
                "gateway_id": gateway.id,
                "recipient": recipient,
                "message": message,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Falha ao enviar teste: {exc}"},
            status=400,
        )

    return JsonResponse(
        {
            "success": True,
            "message": data.get("message", "Mensagem enviada."),
            "status": data.get("status"),
            "recipient": data.get("recipient", recipient),
        }
    )


@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
@login_required
@user_passes_test(_staff_check)
def messaging_gateway_detail(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id)
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway não encontrado."}, status=404
        )
    
    # Validar permissões RBAC para câmeras de vídeo
    if gateway.gateway_type == "video" and not request.user.is_superuser:
        user_depts = request.user.profile.departments.all()
        
        # Verificar se a câmera pertence aos departamentos do usuário OU é pública
        has_access = (
            gateway.departments.exists() == False or  # Pública (sem departamentos)
            gateway.departments.filter(id__in=[d.id for d in user_depts]).exists()  # Ou pertence aos departamentos do usuário
        )
        
        if not has_access:
            return JsonResponse(
                {"success": False, "message": "Sem permissão para acessar esta câmera."},
                status=403
            )

    original_config = dict(gateway.config or {})
    original_enabled = gateway.enabled

    if request.method == "GET":
        return JsonResponse({"success": True, "gateway": _serialize_gateway(gateway)})

    if request.method == "DELETE":
        gateway_type = gateway.gateway_type
        if gateway_type == "video":
            video_gateway_service.stop_stream_for_gateway(gateway, clear_preview=True)
        gateway.delete()
        _sync_gateway_env(gateway_type)
        return JsonResponse({"success": True, "message": "Gateway removido."})

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )

    if "name" in data:
        gateway.name = data.get("name", "").strip() or gateway.name
    if "provider" in data:
        gateway.provider = data.get("provider", "").strip() or gateway.provider
    if "site_name" in data:
        gateway.site_name = data.get("site_name", "").strip() or None
    if "priority" in data:
        try:
            priority = int(data.get("priority", gateway.priority))
        except (TypeError, ValueError):
            priority = gateway.priority
        if priority < 1:
            priority = 1
        gateway.priority = priority

    stop_before_save = False
    config_updated = False
    updated_config = dict(gateway.config or {})

    if "enabled" in data:
        new_enabled = bool(data.get("enabled"))
        gateway.enabled = new_enabled
        if original_enabled and not new_enabled and gateway.gateway_type == "video":
            stop_before_save = True

    if "config" in data and isinstance(data.get("config"), dict):
        sensitive_keys = {
            "password",
            "api_token",
            "access_token",
            "bot_token",
            "aws_secret_access_key",
            "oauth_client_secret",
            "oauth_refresh_token",
        }
        for key, value in data.get("config", {}).items():
            if key in sensitive_keys and value == "":
                continue
            if (
                gateway.gateway_type == "video"
                and key in {"stream_url", "stream_type", "restream_key"}
                and updated_config.get(key) != value
            ):
                stop_before_save = True
            updated_config[key] = value
            config_updated = True

    if gateway.gateway_type == "video" and stop_before_save:
        updated_config.pop("preview_url", None)
        video_gateway_service.stop_stream_for_gateway(gateway)

    if config_updated:
        gateway.config = updated_config

    gateway.save()
    _sync_gateway_env(gateway.gateway_type)

    return JsonResponse({"success": True, "gateway": _serialize_gateway(gateway)})


def _stream_upstream_response(response: requests.Response, chunk_size: int = 64 * 1024):
    try:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    finally:
        response.close()


@require_GET
@login_required
@user_passes_test(_staff_check)
def proxy_video_gateway_hls(request, gateway_id: int, resource: str = "index.m3u8"):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="video")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway de vídeo não encontrado."},
            status=404,
        )

    if not _user_can_access_video_gateway(request.user, gateway):
        return JsonResponse(
            {"success": False, "message": "Sem permissão para acessar esta câmera."},
            status=403,
        )

    sanitized = (resource or "index.m3u8").strip()
    if not sanitized or sanitized.endswith("/"):
        sanitized = f"{sanitized.rstrip('/')}/index.m3u8"
    sanitized = sanitized.lstrip("/")
    if ".." in sanitized:
        return JsonResponse(
            {"success": False, "message": "Recurso inválido."},
            status=400,
        )

    stream_key = video_gateway_service.get_stream_key(gateway)
    target_url = video_gateway_service.build_internal_hls_url(stream_key, sanitized)

    upstream_params = dict(request.GET.items())
    upstream_params.setdefault("mode", "legacy")

    try:
        upstream = requests.get(
            target_url,
            params=upstream_params,
            timeout=15,
            stream=True,
        )
    except requests.RequestException as exc:
        logger.warning(
            "Falha ao proxy HLS para gateway %s (%s): %s",
            gateway.id,
            sanitized,
            exc,
        )
        return HttpResponse(status=502)

    if upstream.status_code >= 400:
        content_type = upstream.headers.get("Content-Type", "text/plain")
        body = upstream.content[:4096]
        upstream.close()
        return HttpResponse(body, status=upstream.status_code, content_type=content_type)

    content_type = upstream.headers.get(
        "Content-Type",
        "application/vnd.apple.mpegurl" if sanitized.endswith(".m3u8") else "application/octet-stream",
    )

    response = StreamingHttpResponse(
        _stream_upstream_response(upstream),
        status=upstream.status_code,
        content_type=content_type,
    )

    passthrough_headers = [
        "Cache-Control",
        "Last-Modified",
        "ETag",
        "Content-Length",
        "Accept-Ranges",
    ]
    for header in passthrough_headers:
        value = upstream.headers.get(header)
        if value:
            response[header] = value

    response["Cache-Control"] = upstream.headers.get("Cache-Control", "no-cache, private")
    return response


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def start_video_gateway_preview(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="video")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway de vídeo não encontrado."},
            status=404,
        )

    config = gateway.config or {}
    stream_url = (config.get("stream_url") or "").strip()
    if not stream_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Configure a URL do stream antes de iniciar a pré-visualização.",
            },
            status=400,
        )

    try:
        video_gateway_service.ensure_stream_for_gateway(
            gateway,
            wait_ready=True,
            startup_timeout=30.0,
        )
    except video_gateway_service.PreviewStartTimeout as exc:
        logger.warning(
            "Pré-visualização do gateway %s não ficou pronta: %s", gateway.id, exc
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Stream HLS não ficou pronto a tempo. Verifique a origem do vídeo.",
            },
            status=504,
        )
    except video_gateway_service.VideoGatewayError as exc:
        logger.warning(
            "Falha ao acionar transmuxer para gateway %s: %s", gateway.id, exc
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Não foi possível acionar o serviço de vídeo.",
            },
            status=502,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Falha inesperada ao iniciar pré-visualização do gateway %s: %s",
            gateway.id,
            exc,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Não foi possível iniciar a pré-visualização do stream.",
            },
            status=500,
        )

    gateway.refresh_from_db(fields=["config", "updated_at"])
    preview_url = (gateway.config or {}).get("preview_url", "")
    playback_url = video_gateway_service.build_playback_url(gateway)
    proxy_url = request.build_absolute_uri(
        reverse("setup_app:video_hls_proxy", args=[gateway.id, "index.m3u8"])
    )
    return JsonResponse(
        {
            "success": True,
            "preview_url": preview_url,
            "playback_url": playback_url,
            "playback_proxy_url": proxy_url,
        }
    )


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def stop_video_gateway_preview(request, gateway_id: int):
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="video")
    except MessagingGateway.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Gateway de vídeo não encontrado."},
            status=404,
        )

    try:
        video_gateway_service.stop_stream_for_gateway(gateway)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Falha ao encerrar pré-visualização do gateway %s: %s", gateway.id, exc
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Não foi possível encerrar a pré-visualização do stream.",
            },
            status=500,
        )

    return JsonResponse({"success": True})


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def get_env_file(request):
    """Return the raw .env content for editing."""
    try:
        env_path = env_manager.ENV_PATH
        if not env_path.exists():
            return JsonResponse({"success": True, "content": ""})

        content = env_path.read_text(encoding="utf-8")
        if len(content) > 512_000:
            return JsonResponse(
                {"success": False, "message": "Env file is too large to edit."},
                status=400,
            )
        return JsonResponse({"success": True, "content": content})
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Failed to read env file: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def update_env_file(request):
    """Overwrite the .env file with provided content."""
    try:
        data = json.loads(request.body or "{}")
        content = data.get("content", "")
        if not isinstance(content, str):
            return JsonResponse(
                {"success": False, "message": "Invalid content payload."},
                status=400,
            )
        if len(content) > 512_000:
            return JsonResponse(
                {"success": False, "message": "Env content is too large."},
                status=400,
            )

        env_path = env_manager.ENV_PATH
        env_path.parent.mkdir(parents=True, exist_ok=True)
        if content and not content.endswith("\n"):
            content = f"{content}\n"
        env_path.write_text(content, encoding="utf-8")

        clear_runtime_config_cache()
        runtime_settings.reload_config()
        reload_diagnostics_flag_cache()

        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="Env File",
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Env file updated."})
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400,
        )
    except Exception as exc:
        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="Env File",
            request=request,
            success=False,
            error_message=str(exc),
        )
        return JsonResponse(
            {"success": False, "message": f"Failed to update env file: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def import_env_backup(request):
    """Restore .env content from a backup metadata file."""
    try:
        data = json.loads(request.body or "{}")
        env_file = data.get("env_file", "")
        if not isinstance(env_file, str):
            return JsonResponse(
                {"success": False, "message": "Invalid env file payload."},
                status=400,
            )
        if len(env_file) > 512_000:
            return JsonResponse(
                {"success": False, "message": "Env content is too large."},
                status=400,
            )

        env_path = env_manager.ENV_PATH
        env_path.parent.mkdir(parents=True, exist_ok=True)
        if env_file and not env_file.endswith("\n"):
            env_file = f"{env_file}\n"
        env_path.write_text(env_file, encoding="utf-8")

        clear_runtime_config_cache()
        runtime_settings.reload_config()
        reload_diagnostics_flag_cache()

        ConfigurationAudit.log_change(
            user=request.user,
            action="import",
            section="Env File",
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Env file importado."})
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400,
        )
    except Exception as exc:
        ConfigurationAudit.log_change(
            user=request.user,
            action="import",
            section="Env File",
            request=request,
            success=False,
            error_message=str(exc),
        )
        return JsonResponse(
            {"success": False, "message": f"Env import failed: {exc}"},
            status=500,
        )


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(_staff_check)
def backups_manager(request):
    """List backups or trigger a new backup."""
    if request.method == "GET":
        _ensure_backup_dir()
        retention_values = env_manager.read_values(
            ["BACKUP_RETENTION_DAYS", "BACKUP_RETENTION_COUNT"]
        )
        backups = []
        for file_path in BACKUP_DIR.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in _ALLOWED_BACKUP_EXTENSIONS:
                continue
            try:
                stat = file_path.stat()
            except FileNotFoundError:
                continue
            
            # Check if backup was uploaded to cloud (heuristic: check if mentioned in recent env values)
            cloud_uploaded = False
            upload_marker = BACKUP_DIR / f".{file_path.name}.uploaded"
            if upload_marker.exists():
                cloud_uploaded = True
            
            backups.append(
                {
                    "id": file_path.name,
                    "name": file_path.name,
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": _detect_backup_type(file_path.name),
                    "download_url": f"/setup_app/api/backups/download/{file_path.name}/",
                    "cloud_uploaded": cloud_uploaded,
                }
            )
        backups.sort(key=lambda item: item["created_at"], reverse=True)
        return JsonResponse(
            {
                "success": True,
                "backups": backups,
                "settings": {
                    "retention_days": retention_values.get("BACKUP_RETENTION_DAYS", ""),
                    "retention_count": retention_values.get("BACKUP_RETENTION_COUNT", ""),
                },
            }
        )

    try:
        _ensure_backup_dir()
        if request.FILES.get("file"):
            upload = request.FILES["file"]
            safe_name = Path(upload.name).name
            if not safe_name:
                return JsonResponse(
                    {"success": False, "message": "Invalid file name."},
                    status=400,
                )
            suffix = Path(safe_name).suffix.lower()
            if suffix not in _ALLOWED_BACKUP_EXTENSIONS:
                return JsonResponse(
                    {"success": False, "message": "Unsupported backup format."},
                    status=400,
                )

            target = BACKUP_DIR / safe_name
            if target.exists():
                stamped = datetime.now().strftime("%Y%m%d_%H%M%S")
                target = BACKUP_DIR / f"upload_{stamped}_{safe_name}"

            with target.open("wb") as handler:
                for chunk in upload.chunks():
                    handler.write(chunk)

            _apply_backup_retention()

            ConfigurationAudit.log_change(
                user=request.user,
                action="import",
                section="Backups",
                new_value=target.name,
                request=request,
                success=True,
            )

            return JsonResponse(
                {"success": True, "message": "Backup enviado", "filename": target.name},
                status=201,
            )

        if shutil.which("pg_dump") is None:
            return JsonResponse(
                {"success": False, "message": "pg_dump is not available on the server."},
                status=500,
            )

        try:
            _get_backup_password()
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)

        filename = call_command("make_backup")
        if not filename:
            backups = [
                path for path in BACKUP_DIR.iterdir()
                if path.is_file() and path.suffix.lower() == ".zip"
            ]
            if backups:
                latest = max(backups, key=lambda item: item.stat().st_mtime)
                filename = latest.name

        gdrive_upload = _upload_backup_if_enabled(filename)
        ftp_upload = _upload_backup_via_ftp(filename)

        _apply_backup_retention()

        ConfigurationAudit.log_change(
            user=request.user,
            action="create",
            section="Backups",
            new_value=filename or "",
            request=request,
            success=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Backup criado",
                "filename": filename or "",
                "gdrive_upload": gdrive_upload or {},
                "ftp_upload": ftp_upload or {},
            },
            status=202,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Backup failed: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def restore_backup(request):
    """Restore a backup file."""
    try:
        data = json.loads(request.body or "{}")
        filename = data.get("filename", "")
        backup_path = _safe_backup_path(filename)
        if not backup_path.exists():
            return JsonResponse({"success": False, "message": "File not found."}, status=404)

        if shutil.which("pg_restore") is None and shutil.which("psql") is None:
            return JsonResponse(
                {"success": False, "message": "Database restore tools are not available."},
                status=500,
            )

        if backup_path.suffix.lower() == ".zip":
            try:
                import pyzipper
            except ImportError as exc:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "pyzipper is required to restore encrypted backups.",
                    },
                    status=500,
                )

            try:
                password = _get_backup_password()
            except ValueError as exc:
                return JsonResponse({"success": False, "message": str(exc)}, status=400)
            extracted_path = None
            with tempfile.TemporaryDirectory(dir=BACKUP_DIR) as temp_dir:
                temp_dir_path = Path(temp_dir)
                with pyzipper.AESZipFile(backup_path) as zipf:
                    zipf.pwd = password
                    zipf.extractall(temp_dir_path)

                candidates = list(temp_dir_path.glob("*.dump")) + list(temp_dir_path.glob("*.sql"))
                if not candidates:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Backup zip does not contain a .dump or .sql file.",
                        },
                        status=400,
                    )

                extracted_path = candidates[0]
                restore_name = f"restore_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extracted_path.suffix}"
                restore_path = BACKUP_DIR / restore_name
                shutil.copy2(extracted_path, restore_path)

                try:
                    call_command("restore_db", restore_path.name)
                finally:
                    restore_path.unlink(missing_ok=True)
        else:
            call_command("restore_db", backup_path.name)

        ConfigurationAudit.log_change(
            user=request.user,
            action="restore",
            section="Backups",
            new_value=filename,
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Restauração iniciada."})
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Restore failed: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def delete_backup(request):
    """Delete a backup file."""
    try:
        data = json.loads(request.body or "{}")
        filename = data.get("filename", "")
        backup_path = _safe_backup_path(filename)
        if not backup_path.exists():
            return JsonResponse({"success": False, "message": "File not found."}, status=404)

        backup_path.unlink(missing_ok=True)

        ConfigurationAudit.log_change(
            user=request.user,
            action="delete",
            section="Backups",
            new_value=filename,
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Backup removido."})
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Delete failed: {exc}"},
            status=500,
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def upload_backup_to_cloud(request):
    """Upload an existing backup file to configured cloud destinations."""
    try:
        data = json.loads(request.body or "{}")
        filename = data.get("filename", "")
        backup_path = _safe_backup_path(filename)
        if not backup_path.exists():
            return JsonResponse({"success": False, "message": "File not found."}, status=404)

        gdrive_upload = _upload_backup_if_enabled(filename)
        ftp_upload = _upload_backup_via_ftp(filename)

        # Mark as uploaded if at least one provider succeeded
        if (gdrive_upload and gdrive_upload.get("success")) or (ftp_upload and ftp_upload.get("success")):
            upload_marker = BACKUP_DIR / f".{filename}.uploaded"
            upload_marker.touch()

        ConfigurationAudit.log_change(
            user=request.user,
            action="upload",
            section="Backups",
            new_value=filename or "",
            request=request,
            success=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Envio iniciado",
                "gdrive_upload": gdrive_upload or {},
                "ftp_upload": ftp_upload or {},
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Upload failed: {exc}"},
            status=500,
        )


@require_http_methods(["POST"])
@login_required
@user_passes_test(_staff_check)
def update_backup_settings(request):
    """Update retention and automation settings for backups."""
    try:
        data = json.loads(request.body or "{}")
        logger.info(f"[update_backup_settings] Received data: {data}")
        
        retention_days = data.get("retention_days")
        retention_count = data.get("retention_count")
        auto_backup = data.get("auto_backup")
        frequency = data.get("frequency")
        cloud_upload = data.get("cloud_upload")
        cloud_provider = data.get("cloud_provider")
        cloud_path = data.get("cloud_path")

        payload = {
            "BACKUP_RETENTION_DAYS": str(retention_days or ""),
            "BACKUP_RETENTION_COUNT": str(retention_count or ""),
        }
        
        if auto_backup is not None:
            payload["BACKUP_AUTO_ENABLED"] = "true" if auto_backup else "false"
        if frequency:
            payload["BACKUP_FREQUENCY"] = str(frequency)
        if cloud_upload is not None:
            payload["BACKUP_CLOUD_UPLOAD"] = "true" if cloud_upload else "false"
        if cloud_provider:
            payload["BACKUP_CLOUD_PROVIDER"] = str(cloud_provider)
        if cloud_path:
            payload["BACKUP_CLOUD_PATH"] = str(cloud_path)

        logger.info(f"[update_backup_settings] Writing to .env: {payload}")
        env_manager.write_values(payload)
        logger.info("[update_backup_settings] Successfully wrote to .env")

        _apply_backup_retention()

        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="Backups",
            new_value=json.dumps(payload),
            request=request,
            success=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Configurações de backup atualizadas.",
                "settings": payload,
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Update failed: {exc}"},
            status=500,
        )


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def download_backup(request, filename):
    """Download a backup file."""
    backup_path = _safe_backup_path(filename)
    if not backup_path.exists():
        return JsonResponse({"success": False, "message": "File not found."}, status=404)

    return FileResponse(
        backup_path.open("rb"),
        as_attachment=True,
        filename=backup_path.name,
    )


# ============================================================================
# Video Mosaics API
# ============================================================================


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def video_cameras_list(request):
    """Listar câmeras (MessagingGateway) com filtro opcional por site.

    Query params:
      - site: ID do Site (inventory.Site.id). Quando fornecido, filtra por `site_name` do gateway
        igual ao `display_name` do Site.
    """
    import os
    from django.conf import settings
    from django.http import JsonResponse
    from django.db.models import Q
    from setup_app.models import MessagingGateway
    from inventory.models import Site
    from .services import video_gateway as video_gateway_service

    try:
        qs = MessagingGateway.objects.filter(gateway_type="video", enabled=True)

        # RBAC: usuários não superuser só veem câmeras públicas ou dos seus departamentos
        if not request.user.is_superuser:
            user_depts = request.user.profile.departments.all()
            qs = qs.filter(Q(departments__in=user_depts) | Q(departments__isnull=True)).distinct()

        site_param = request.GET.get("site") or request.GET.get("site_id")
        site_name = None
        if site_param:
            try:
                site_obj = Site.objects.get(pk=int(site_param))
                site_name = site_obj.display_name
            except Exception:
                site_name = None
        if site_name:
            qs = qs.filter(site_name=site_name)

        gateways = list(qs.order_by("name"))

        def _whep_url(gw: MessagingGateway) -> str | None:
            cfg = gw.config or {}
            webrtc_base = (cfg.get("webrtc_public_base_url") or "").strip()
            if not webrtc_base:
                webrtc_base = getattr(settings, "VIDEO_WEBRTC_PUBLIC_BASE_URL", None) or os.environ.get("VIDEO_WEBRTC_PUBLIC_BASE_URL")
            if not webrtc_base:
                return None
            restream_key = (cfg.get("restream_key") or f"gateway_{gw.id}")
            base = str(webrtc_base).rstrip('/')
            return f"{base}/{restream_key}/whep"

        results = []
        for gw in gateways:
            playback_url = video_gateway_service.build_playback_url(gw)
            results.append({
                "id": gw.id,
                "name": gw.name,
                "enabled": gw.enabled,
                "site_name": gw.site_name,
                "playback_url": playback_url,
                "whep_url": _whep_url(gw),
            })

        return JsonResponse({
            "success": True,
            "count": len(results),
            "results": results,
        })
    except Exception as exc:
        logger.exception("Error listing video cameras")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)

@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(_staff_check)
def video_mosaics_list(request):
    """List all video mosaics or create a new one."""
    from .models import VideoMosaic
    
    if request.method == "GET":
        try:
            # Filtro opcional por site_id
            site_id_param = request.GET.get('site_id') or request.GET.get('site')

            # Filtrar por departamentos do usuário
            if request.user.is_superuser:
                # Superuser vê todos os mosaicos
                mosaics = VideoMosaic.objects.all().order_by('name')
            else:
                # Usuários normais veem apenas mosaicos de seus departamentos
                user_depts = request.user.profile.departments.all()
                
                # Mosaicos sem departamento (públicos) OU mosaicos dos departamentos do usuário
                mosaics = VideoMosaic.objects.filter(
                    Q(departments__in=user_depts) | 
                    Q(departments__isnull=True)
                ).distinct().order_by('name')
            if site_id_param:
                try:
                    mosaics = mosaics.filter(site_id=int(site_id_param))
                except ValueError:
                    pass
            
            mosaic_list = [
                {
                    "id": m.id,
                    "name": m.name,
                    "layout": m.layout,
                    "cameras": m.cameras or [],
                    "site_id": m.site_id,
                    "departments": [{"id": d.id, "name": d.name} for d in m.departments.all()],
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                }
                for m in mosaics
            ]
            return JsonResponse({"success": True, "mosaics": mosaic_list})
        except Exception as exc:
            logger.exception("Error listing video mosaics")
            return JsonResponse(
                {"success": False, "message": f"Failed to list mosaics: {exc}"},
                status=500,
            )
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name", "").strip()
            layout = data.get("layout", "2x2")
            cameras = data.get("cameras", [])
            department_ids = data.get("department_ids", [])
            site_id = data.get("site_id")
            
            if not name:
                return JsonResponse(
                    {"success": False, "message": "Nome do mosaico é obrigatório"},
                    status=400,
                )
            
            # Validar permissões: usuários normais só podem criar mosaicos em seus departamentos
            if not request.user.is_superuser and department_ids:
                user_dept_ids = set(request.user.profile.departments.values_list('id', flat=True))
                requested_dept_ids = set(department_ids)
                
                if not requested_dept_ids.issubset(user_dept_ids):
                    return JsonResponse(
                        {"success": False, "message": "Você só pode criar mosaicos em departamentos aos quais pertence."},
                        status=403,
                    )
            
            mosaic = VideoMosaic.objects.create(
                name=name,
                layout=layout,
                cameras=cameras,
                site_id=site_id if isinstance(site_id, int) else None,
            )
            
            # Adicionar departamentos se fornecidos
            if department_ids:
                from core.models import Department
                mosaic.departments.set(Department.objects.filter(id__in=department_ids))
            
            return JsonResponse({
                "success": True,
                "message": "Mosaico criado com sucesso",
                "mosaic": {
                    "id": mosaic.id,
                    "name": mosaic.name,
                    "layout": mosaic.layout,
                    "cameras": mosaic.cameras,
                    "site_id": mosaic.site_id,
                    "departments": [{"id": d.id, "name": d.name} for d in mosaic.departments.all()],
                    "created_at": mosaic.created_at.isoformat(),
                    "updated_at": mosaic.updated_at.isoformat(),
                },
            })
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"},
                status=400,
            )
        except Exception as exc:
            logger.exception("Error creating video mosaic")
            return JsonResponse(
                {"success": False, "message": f"Failed to create mosaic: {exc}"},
                status=500,
            )


@require_http_methods(["GET", "PATCH", "DELETE"])
@login_required
@user_passes_test(_staff_check)
def video_mosaic_detail(request, mosaic_id: int):
    """Get, update or delete a specific video mosaic."""
    from .models import VideoMosaic
    
    try:
        mosaic = VideoMosaic.objects.get(pk=mosaic_id)
    except VideoMosaic.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Mosaico não encontrado"},
            status=404,
        )
    
    # Validar permissões RBAC
    if not request.user.is_superuser:
        user_depts = request.user.profile.departments.all()
        
        # Verificar se o mosaico pertence aos departamentos do usuário OU é público
        has_access = (
            mosaic.departments.exists() == False or  # Público (sem departamentos)
            mosaic.departments.filter(id__in=[d.id for d in user_depts]).exists()  # Ou pertence aos departamentos do usuário
        )
        
        if not has_access:
            return JsonResponse(
                {"success": False, "message": "Sem permissão para acessar este mosaico."},
                status=403
            )
    
    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "mosaic": {
                "id": mosaic.id,
                "name": mosaic.name,
                "layout": mosaic.layout,
                "cameras": mosaic.cameras,
                "site_id": mosaic.site_id,
                "departments": [{"id": d.id, "name": d.name} for d in mosaic.departments.all()],
                "created_at": mosaic.created_at.isoformat() if mosaic.created_at else None,
                "updated_at": mosaic.updated_at.isoformat() if mosaic.updated_at else None,
            },
        })
    
    elif request.method == "PATCH":
        try:
            data = json.loads(request.body)
            
            if "name" in data:
                name = data["name"].strip()
                if not name:
                    return JsonResponse(
                        {"success": False, "message": "Nome do mosaico não pode ser vazio"},
                        status=400,
                    )
                mosaic.name = name
            
            if "layout" in data:
                mosaic.layout = data["layout"]
            
            if "cameras" in data:
                mosaic.cameras = data["cameras"]

            if "site_id" in data:
                raw_site_id = data["site_id"]
                mosaic.site_id = raw_site_id if isinstance(raw_site_id, int) else None
            
            # Atualizar departamentos se fornecidos
            if "department_ids" in data:
                department_ids = data["department_ids"]
                
                # Validar permissões: usuários normais só podem atribuir seus próprios departamentos
                if not request.user.is_superuser and department_ids:
                    user_dept_ids = set(request.user.profile.departments.values_list('id', flat=True))
                    requested_dept_ids = set(department_ids)
                    
                    if not requested_dept_ids.issubset(user_dept_ids):
                        return JsonResponse(
                            {"success": False, "message": "Você só pode atribuir departamentos aos quais pertence."},
                            status=403,
                        )
                
                from core.models import Department
                mosaic.departments.set(Department.objects.filter(id__in=department_ids))
            
            mosaic.save()
            
            return JsonResponse({
                "success": True,
                "message": "Mosaico atualizado com sucesso",
                "mosaic": {
                    "id": mosaic.id,
                    "name": mosaic.name,
                    "layout": mosaic.layout,
                    "cameras": mosaic.cameras,
                    "site_id": mosaic.site_id,
                    "departments": [{"id": d.id, "name": d.name} for d in mosaic.departments.all()],
                    "updated_at": mosaic.updated_at.isoformat(),
                },
            })
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"},
                status=400,
            )
        except Exception as exc:
            logger.exception("Error updating video mosaic")
            return JsonResponse(
                {"success": False, "message": f"Failed to update mosaic: {exc}"},
                status=500,
            )
    
    elif request.method == "DELETE":
        try:
            mosaic_name = mosaic.name
            mosaic.delete()
            return JsonResponse({
                "success": True,
                "message": f"Mosaico '{mosaic_name}' removido com sucesso",
            })
        except Exception as exc:
            logger.exception("Error deleting video mosaic")
            return JsonResponse(
                {"success": False, "message": f"Failed to delete mosaic: {exc}"},
                status=500,
            )

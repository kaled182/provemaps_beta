"""API endpoints for setup configuration testing and management."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from integrations.zabbix.zabbix_client import zabbix_request
from integrations.zabbix.guards import reload_diagnostics_flag_cache
from .models import FirstTimeSetup
from .models_audit import ConfigurationAudit
from .services import runtime_settings
from .services.config_loader import clear_runtime_config_cache
from .services.service_reloader import trigger_restart
from .utils import env_manager


def _staff_check(user):
    """Check if user is staff."""
    return user.is_active and user.is_staff


BACKUP_DIR = Path(settings.BASE_DIR) / "database" / "backups"


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
            
            # Try to get Zabbix API version (doesn't require auth)
            payload = {
                "jsonrpc": "2.0",
                "method": "apiinfo.version",
                "params": {},
                "id": 1
            }
            
            response = requests.post(
                zabbix_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(result["error"].get("data", "API error"))
            
            version = result.get("result", "Unknown")

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
                    "message": f"Connection successful! Zabbix version: {version}",
                    "version": version,
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
            "ALLOWED_HOSTS",
            "ENABLE_DIAGNOSTIC_ENDPOINTS",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_URL",
            "SERVICE_RESTART_COMMANDS",
        ]

        config_data = env_manager.read_values(editable_keys)

        # Sanitize sensitive data for export
        sensitive_keys = ["SECRET_KEY", "ZABBIX_API_PASSWORD", "ZABBIX_API_KEY", "DB_PASSWORD"]
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
            "ALLOWED_HOSTS",
            "ENABLE_DIAGNOSTIC_ENDPOINTS",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_URL",
            "SERVICE_RESTART_COMMANDS",
        ]
        
        current_values = env_manager.read_values(editable_keys)
        
        # Convert boolean strings to actual booleans for JSON
        config_data = {}
        for key, value in current_values.items():
            if key in ["DEBUG", "ENABLE_DIAGNOSTIC_ENDPOINTS"]:
                config_data[key] = value.lower() == "true" if value else False
            else:
                config_data[key] = value or ""
        
        return JsonResponse({
            "success": True,
            "configuration": config_data
        })

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, 
            status=500
        )


@require_POST
@login_required
@user_passes_test(_staff_check)
def update_configuration(request):
    """Update system configuration (save to .env and database)."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = [
            "SECRET_KEY", "ZABBIX_API_URL", "DB_HOST", 
            "DB_PORT", "DB_NAME", "DB_USER"
        ]
        
        missing_fields = [
            field for field in required_fields 
            if not data.get(field, "").strip()
        ]
        
        if missing_fields:
            return JsonResponse({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=400)

        # Step 1: Write to .env file
        payload = {
            "SECRET_KEY": data.get("SECRET_KEY", "").strip(),
            "DEBUG": "True" if data.get("DEBUG", False) else "False",
            "ZABBIX_API_URL": data.get("ZABBIX_API_URL", "").strip(),
            "ZABBIX_API_USER": data.get("ZABBIX_API_USER", "").strip(),
            "ZABBIX_API_PASSWORD": data.get("ZABBIX_API_PASSWORD", "").strip(),
            "ZABBIX_API_KEY": data.get("ZABBIX_API_KEY", "").strip(),
            "GOOGLE_MAPS_API_KEY": data.get("GOOGLE_MAPS_API_KEY", "").strip(),
            "ALLOWED_HOSTS": data.get("ALLOWED_HOSTS", "").strip(),
            "ENABLE_DIAGNOSTIC_ENDPOINTS": (
                "True" if data.get("ENABLE_DIAGNOSTIC_ENDPOINTS", False) 
                else "False"
            ),
            "DB_HOST": data.get("DB_HOST", "").strip(),
            "DB_PORT": data.get("DB_PORT", "").strip(),
            "DB_NAME": data.get("DB_NAME", "").strip(),
            "DB_USER": data.get("DB_USER", "").strip(),
            "DB_PASSWORD": data.get("DB_PASSWORD", "").strip(),
            "REDIS_URL": data.get("REDIS_URL", "").strip(),
            "SERVICE_RESTART_COMMANDS": data.get(
                "SERVICE_RESTART_COMMANDS", ""
            ).strip(),
        }
        
        env_manager.write_values(payload)
        os.environ["SERVICE_RESTART_COMMANDS"] = payload["SERVICE_RESTART_COMMANDS"]

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
                "db_host": payload["DB_HOST"],
                "db_port": payload["DB_PORT"],
                "db_name": payload["DB_NAME"],
                "db_user": payload["DB_USER"],
                "db_password": payload["DB_PASSWORD"],
                "redis_url": payload["REDIS_URL"],
            }
        )

        # Step 3: Clear caches
        clear_runtime_config_cache()
        runtime_settings.reload_config()
        
        from integrations.zabbix.zabbix_service import clear_token_cache
        clear_token_cache()
        reload_diagnostics_flag_cache()

        # Step 4: Trigger service restart if configured
        if payload["SERVICE_RESTART_COMMANDS"]:
            trigger_restart()

        # Log success
        ConfigurationAudit.log_change(
            user=request.user,
            action="update",
            section="System Configuration",
            request=request,
            success=True,
        )

        return JsonResponse({
            "success": True,
            "message": "Configuration updated successfully"
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


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(_staff_check)
def backups_manager(request):
    """List backups or trigger a new backup."""
    if request.method == "GET":
        _ensure_backup_dir()
        backups = []
        for file_path in BACKUP_DIR.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in {".dump", ".sql", ".json"}:
                continue
            stat = file_path.stat()
            backups.append(
                {
                    "name": file_path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        backups.sort(key=lambda item: item["created_at"], reverse=True)
        return JsonResponse({"success": True, "backups": backups})

    try:
        _ensure_backup_dir()
        if shutil.which("pg_dump") is None:
            return JsonResponse(
                {"success": False, "message": "pg_dump is not available on the server."},
                status=500,
            )

        db_settings = _get_db_settings()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"manual_backup_{timestamp}.dump"
        backup_path = BACKUP_DIR / filename

        env = os.environ.copy()
        if db_settings.get("DB_PASSWORD"):
            env["PGPASSWORD"] = db_settings["DB_PASSWORD"]

        command = [
            "pg_dump",
            "-Fc",
            "-f",
            str(backup_path),
            "-h",
            db_settings["DB_HOST"],
            "-p",
            db_settings["DB_PORT"],
            "-U",
            db_settings["DB_USER"],
            db_settings["DB_NAME"],
        ]

        subprocess.run(command, check=True, env=env, capture_output=True, text=True)

        ConfigurationAudit.log_change(
            user=request.user,
            action="create",
            section="Backups",
            new_value=filename,
            request=request,
            success=True,
        )

        return JsonResponse(
            {"success": True, "message": "Backup criado", "filename": filename},
            status=202,
        )
    except subprocess.CalledProcessError as exc:
        return JsonResponse(
            {"success": False, "message": exc.stderr or "Backup failed."},
            status=500,
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

        if shutil.which("pg_restore") is None or shutil.which("psql") is None:
            return JsonResponse(
                {"success": False, "message": "Database restore tools are not available."},
                status=500,
            )

        db_settings = _get_db_settings()
        env = os.environ.copy()
        if db_settings.get("DB_PASSWORD"):
            env["PGPASSWORD"] = db_settings["DB_PASSWORD"]

        if backup_path.suffix.lower() == ".dump":
            command = [
                "pg_restore",
                "--clean",
                "--if-exists",
                "-h",
                db_settings["DB_HOST"],
                "-p",
                db_settings["DB_PORT"],
                "-U",
                db_settings["DB_USER"],
                "-d",
                db_settings["DB_NAME"],
                str(backup_path),
            ]
        elif backup_path.suffix.lower() == ".sql":
            command = [
                "psql",
                "-h",
                db_settings["DB_HOST"],
                "-p",
                db_settings["DB_PORT"],
                "-U",
                db_settings["DB_USER"],
                "-d",
                db_settings["DB_NAME"],
                "-f",
                str(backup_path),
            ]
        else:
            return JsonResponse(
                {"success": False, "message": "Unsupported backup format."},
                status=400,
            )

        subprocess.run(command, check=True, env=env, capture_output=True, text=True)

        ConfigurationAudit.log_change(
            user=request.user,
            action="restore",
            section="Backups",
            new_value=filename,
            request=request,
            success=True,
        )

        return JsonResponse({"success": True, "message": "Restauração iniciada."})
    except subprocess.CalledProcessError as exc:
        return JsonResponse(
            {"success": False, "message": exc.stderr or "Restore failed."},
            status=500,
        )
    except Exception as exc:
        return JsonResponse(
            {"success": False, "message": f"Restore failed: {exc}"},
            status=500,
        )

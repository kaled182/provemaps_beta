"""Backups da base de dados e envio para a nuvem (Google Drive / FTP).

Saiu de `setup_app/api_views.py` em EV-0017a. Regras:
- os ficheiros vivem em `BACKUP_DIR` e só `.zip` conta como backup;
- um nome de ficheiro nunca sai da pasta (`safe_backup_path`);
- a senha do zip vem do `.env` e tem pelo menos `MIN_BACKUP_PASSWORD_LEN` caracteres;
- exceções de domínio levam um `status` HTTP sugerido para a view traduzir.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command

from ..models import FirstTimeSetup
from ..services import runtime_settings
from ..services.cloud_backups import test_gdrive_connection, upload_backup_to_gdrive
from ..services.config_loader import clear_runtime_config_cache
from ..utils import env_manager
from .common import to_bool

BACKUP_DIR = Path(settings.BASE_DIR) / "database" / "backups"
ALLOWED_BACKUP_EXTENSIONS = {".zip"}
MIN_BACKUP_PASSWORD_LEN = 8
DOWNLOAD_URL_PREFIX = "/setup_app/api/backups/download/"
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class BackupError(Exception):
    """Erro de domínio dos backups; `status` é o HTTP sugerido."""

    status = 400


class BackupNotFound(BackupError):
    status = 404


class BackupToolMissing(BackupError):
    """pg_dump/pg_restore/pyzipper/SDK Google ausentes no servidor."""

    status = 500


class InvalidBackupFile(BackupError):
    status = 400


# ── Configuração lida do .env ────────────────────────────────────────────────


def get_db_settings() -> dict[str, str]:
    keys = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    values = env_manager.read_values(keys)
    missing = [key for key in keys if key != "DB_PASSWORD" and not values.get(key)]
    if missing:
        raise ValueError(f"Missing database settings: {', '.join(missing)}")
    return values


def get_backup_password() -> bytes:
    values = env_manager.read_values(["BACKUP_ZIP_PASSWORD"])
    password = values.get("BACKUP_ZIP_PASSWORD", "").strip()
    if len(password) < MIN_BACKUP_PASSWORD_LEN:
        raise ValueError("A senha do backup precisa ter pelo menos 8 caracteres para criptografar.")
    return password.encode("utf-8")


def get_gdrive_settings() -> dict[str, Any]:
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
        "enabled": to_bool(values.get("GDRIVE_ENABLED", "")),
        "auth_mode": values.get("GDRIVE_AUTH_MODE", "service_account"),
        "credentials": values.get("GDRIVE_CREDENTIALS_JSON", ""),
        "folder_id": values.get("GDRIVE_FOLDER_ID", ""),
        "shared_drive_id": values.get("GDRIVE_SHARED_DRIVE_ID", ""),
        "oauth_client_id": values.get("GDRIVE_OAUTH_CLIENT_ID", ""),
        "oauth_client_secret": values.get("GDRIVE_OAUTH_CLIENT_SECRET", ""),
        "oauth_refresh_token": values.get("GDRIVE_OAUTH_REFRESH_TOKEN", ""),
        "oauth_user_email": values.get("GDRIVE_OAUTH_USER_EMAIL", ""),
    }


def get_ftp_settings() -> dict[str, Any]:
    values = env_manager.read_values(
        ["FTP_ENABLED", "FTP_HOST", "FTP_PORT", "FTP_USER", "FTP_PASSWORD", "FTP_PATH"]
    )
    return {
        "enabled": to_bool(values.get("FTP_ENABLED", "")),
        "host": values.get("FTP_HOST", ""),
        "port": values.get("FTP_PORT", ""),
        "user": values.get("FTP_USER", ""),
        "password": values.get("FTP_PASSWORD", ""),
        "path": values.get("FTP_PATH", ""),
    }


# ── Ficheiros ────────────────────────────────────────────────────────────────


def safe_backup_path(filename: str) -> Path:
    """Caminho dentro de BACKUP_DIR; recusa vazio, subpastas e `..`."""
    if not filename:
        raise ValueError("Filename required")
    safe_name = Path(filename).name
    if safe_name != filename:
        raise ValueError("Invalid filename")
    return BACKUP_DIR / safe_name


def ensure_backup_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def detect_backup_type(filename: str) -> str:
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


def _backup_files() -> list[Path]:
    files = []
    for path in BACKUP_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in ALLOWED_BACKUP_EXTENSIONS:
            continue
        try:
            path.stat()
        except FileNotFoundError:
            continue
        files.append(path)
    return files


def apply_backup_retention() -> None:
    """Apaga backups mais velhos que BACKUP_RETENTION_DAYS e além de BACKUP_RETENTION_COUNT."""
    values = env_manager.read_values(["BACKUP_RETENTION_DAYS", "BACKUP_RETENTION_COUNT"])

    def _int(raw: str) -> int | None:
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    days = _int(values.get("BACKUP_RETENTION_DAYS", ""))
    count = _int(values.get("BACKUP_RETENTION_COUNT", ""))
    if not days and not count:
        return

    ensure_backup_dir()
    files = _backup_files()

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
        for _, path in sorted(sortable, key=lambda item: item[0], reverse=True)[count:]:
            path.unlink(missing_ok=True)


def list_backups() -> dict[str, Any]:
    """Backups existentes (mais recente primeiro) e as definições de retenção."""
    ensure_backup_dir()
    retention = env_manager.read_values(["BACKUP_RETENTION_DAYS", "BACKUP_RETENTION_COUNT"])
    backups = []
    for path in _backup_files():
        stat = path.stat()
        backups.append(
            {
                "id": path.name,
                "name": path.name,
                "filename": path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "type": detect_backup_type(path.name),
                "download_url": f"{DOWNLOAD_URL_PREFIX}{path.name}/",
                "cloud_uploaded": (BACKUP_DIR / f".{path.name}.uploaded").exists(),
            }
        )
    backups.sort(key=lambda item: item["created_at"], reverse=True)
    return {
        "backups": backups,
        "settings": {
            "retention_days": retention.get("BACKUP_RETENTION_DAYS", ""),
            "retention_count": retention.get("BACKUP_RETENTION_COUNT", ""),
        },
    }


def store_uploaded_backup(upload) -> str:
    """Guarda um ficheiro enviado pelo utilizador; devolve o nome final."""
    ensure_backup_dir()
    safe_name = Path(upload.name).name
    if not safe_name:
        raise InvalidBackupFile("Invalid file name.")
    if Path(safe_name).suffix.lower() not in ALLOWED_BACKUP_EXTENSIONS:
        raise InvalidBackupFile("Unsupported backup format.")

    target = BACKUP_DIR / safe_name
    if target.exists():
        stamped = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = BACKUP_DIR / f"upload_{stamped}_{safe_name}"

    with target.open("wb") as handler:
        for chunk in upload.chunks():
            handler.write(chunk)

    apply_backup_retention()
    return target.name


def create_backup() -> dict[str, Any]:
    """Gera um backup com `make_backup`, envia para a nuvem se ativo e aplica retenção."""
    ensure_backup_dir()
    if shutil.which("pg_dump") is None:
        raise BackupToolMissing("pg_dump is not available on the server.")
    get_backup_password()  # ValueError se a senha for curta

    filename = call_command("make_backup")
    if not filename:
        candidates = _backup_files()
        if candidates:
            filename = max(candidates, key=lambda item: item.stat().st_mtime).name

    gdrive_upload = upload_backup_if_enabled(filename)
    ftp_upload = upload_backup_via_ftp(filename)
    apply_backup_retention()
    return {
        "filename": filename or "",
        "gdrive_upload": gdrive_upload or {},
        "ftp_upload": ftp_upload or {},
    }


def restore_backup(filename: str) -> None:
    """Restaura um backup (zip cifrado ou dump) com o comando `restore_db`."""
    backup_path = safe_backup_path(filename)
    if not backup_path.exists():
        raise BackupNotFound("File not found.")

    if shutil.which("pg_restore") is None and shutil.which("psql") is None:
        raise BackupToolMissing("Database restore tools are not available.")

    if backup_path.suffix.lower() != ".zip":
        call_command("restore_db", backup_path.name)
        return

    try:
        import pyzipper
    except ImportError as exc:
        raise BackupToolMissing("pyzipper is required to restore encrypted backups.") from exc

    password = get_backup_password()
    with tempfile.TemporaryDirectory(dir=BACKUP_DIR) as temp_dir:
        temp_dir_path = Path(temp_dir)
        with pyzipper.AESZipFile(backup_path) as zipf:
            zipf.pwd = password
            zipf.extractall(temp_dir_path)

        candidates = list(temp_dir_path.glob("*.dump")) + list(temp_dir_path.glob("*.sql"))
        if not candidates:
            raise InvalidBackupFile("Backup zip does not contain a .dump or .sql file.")

        extracted = candidates[0]
        restore_name = f"restore_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extracted.suffix}"
        restore_path = BACKUP_DIR / restore_name
        shutil.copy2(extracted, restore_path)
        try:
            call_command("restore_db", restore_path.name)
        finally:
            restore_path.unlink(missing_ok=True)


def delete_backup(filename: str) -> None:
    backup_path = safe_backup_path(filename)
    if not backup_path.exists():
        raise BackupNotFound("File not found.")
    backup_path.unlink(missing_ok=True)


def backup_download_path(filename: str) -> Path:
    backup_path = safe_backup_path(filename)
    if not backup_path.exists():
        raise BackupNotFound("File not found.")
    return backup_path


def update_backup_settings(data: dict[str, Any]) -> dict[str, str]:
    """Escreve retenção/automação no .env e aplica a retenção; devolve o que escreveu."""
    payload = {
        "BACKUP_RETENTION_DAYS": str(data.get("retention_days") or ""),
        "BACKUP_RETENTION_COUNT": str(data.get("retention_count") or ""),
    }
    if data.get("auto_backup") is not None:
        payload["BACKUP_AUTO_ENABLED"] = "true" if data["auto_backup"] else "false"
    if data.get("frequency"):
        payload["BACKUP_FREQUENCY"] = str(data["frequency"])
    if data.get("cloud_upload") is not None:
        payload["BACKUP_CLOUD_UPLOAD"] = "true" if data["cloud_upload"] else "false"
    if data.get("cloud_provider"):
        payload["BACKUP_CLOUD_PROVIDER"] = str(data["cloud_provider"])
    if data.get("cloud_path"):
        payload["BACKUP_CLOUD_PATH"] = str(data["cloud_path"])

    env_manager.write_values(payload)
    apply_backup_retention()
    return payload


# ── Nuvem: FTP e Google Drive ────────────────────────────────────────────────


def ensure_ftp_dir(ftp, remote_path: str) -> None:
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


def upload_backup_via_ftp(
    filename: str, settings_payload: dict[str, Any] | None = None
) -> dict[str, object]:
    if not filename:
        return {"success": False, "message": "Backup filename not available."}
    settings_payload = settings_payload or get_ftp_settings()
    if not settings_payload.get("enabled"):
        return {"success": False, "message": "FTP desabilitado."}

    backup_path = safe_backup_path(filename)
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
            ftp.login(
                user=settings_payload.get("user", ""), passwd=settings_payload.get("password", "")
            )
        else:
            ftp.login()
        ensure_ftp_dir(ftp, settings_payload.get("path", ""))
        with backup_path.open("rb") as handler:
            ftp.storbinary(f"STOR {backup_path.name}", handler)
        ftp.quit()
        return {"success": True, "message": "Backup enviado via FTP."}
    except Exception as exc:
        return {"success": False, "message": f"Falha ao enviar via FTP: {exc}"}


def upload_backup_if_enabled(
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
) -> dict[str, object]:
    """Envia para o Google Drive se ativo (no .env ou nos argumentos explícitos)."""
    if not filename:
        return {"success": False, "message": "Backup filename not available."}

    if enabled is not None:
        settings_payload: dict[str, Any] = {
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
        settings_payload = get_gdrive_settings()
    if not settings_payload["enabled"]:
        return {"success": False, "message": "Google Drive desabilitado."}

    backup_path = safe_backup_path(filename)
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


def upload_existing_backup(filename: str) -> dict[str, Any]:
    """Envia um backup já existente para os destinos ativos; marca se algum aceitou."""
    backup_path = safe_backup_path(filename)
    if not backup_path.exists():
        raise BackupNotFound("File not found.")

    gdrive_upload = upload_backup_if_enabled(filename)
    ftp_upload = upload_backup_via_ftp(filename)
    marked = bool(
        (gdrive_upload and gdrive_upload.get("success"))
        or (ftp_upload and ftp_upload.get("success"))
    )
    if marked:
        (BACKUP_DIR / f".{filename}.uploaded").touch()
    return {"gdrive_upload": gdrive_upload or {}, "ftp_upload": ftp_upload or {}, "marked": marked}


def gdrive_test(data: dict[str, Any]) -> dict[str, Any]:
    """Testa a ligação ao Drive com o que veio no pedido, completando com o .env."""
    auth_mode = (data.get("gdrive_auth_mode") or "").strip()
    credentials_json = (data.get("gdrive_credentials_json") or "").strip()
    folder_id = (data.get("gdrive_folder_id") or "").strip()
    shared_drive_id = (data.get("gdrive_shared_drive_id") or "").strip()
    oauth_client_id = (data.get("gdrive_oauth_client_id") or "").strip()
    oauth_client_secret = (data.get("gdrive_oauth_client_secret") or "").strip()
    oauth_refresh_token = ""

    needs_env = (
        not auth_mode
        or (auth_mode == "service_account" and not credentials_json)
        or auth_mode == "oauth"
    )
    if needs_env:
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

    return test_gdrive_connection(
        auth_mode=auth_mode or "service_account",
        credentials_json=credentials_json,
        folder_id=folder_id or None,
        shared_drive_id=shared_drive_id or None,
        oauth_client_id=oauth_client_id,
        oauth_client_secret=oauth_client_secret,
        oauth_refresh_token=oauth_refresh_token,
    )


def _gdrive_client_config(client_id: str, client_secret: str) -> dict[str, Any]:
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _oauth_flow_class():
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise BackupToolMissing("Google OAuth SDK não instalado.") from exc
    return Flow


def gdrive_oauth_start(data: dict[str, Any], redirect_uri: str) -> dict[str, str]:
    """Grava client id/secret e devolve a URL de autorização e o `state` a guardar na sessão."""
    client_id = (data.get("gdrive_oauth_client_id") or "").strip()
    client_secret = (data.get("gdrive_oauth_client_secret") or "").strip()
    if not client_id or not client_secret:
        values = env_manager.read_values(["GDRIVE_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_SECRET"])
        client_id = client_id or values.get("GDRIVE_OAUTH_CLIENT_ID", "")
        client_secret = client_secret or values.get("GDRIVE_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ValueError("Informe Client ID e Client Secret.")

    flow_class = _oauth_flow_class()

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

    flow = flow_class.from_client_config(
        _gdrive_client_config(client_id, client_secret),
        scopes=GDRIVE_SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return {"auth_url": auth_url, "state": state}


def gdrive_oauth_complete(code: str, state: str, redirect_uri: str) -> dict[str, str]:
    """Troca o código pelo refresh token, guarda-o e devolve o e-mail da conta."""
    values = env_manager.read_values(["GDRIVE_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_SECRET"])
    client_id = values.get("GDRIVE_OAUTH_CLIENT_ID", "")
    client_secret = values.get("GDRIVE_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ValueError("Client ID/Secret não configurados.")

    flow_class = _oauth_flow_class()
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise BackupToolMissing("Google OAuth SDK não instalado.") from exc

    flow = flow_class.from_client_config(
        _gdrive_client_config(client_id, client_secret),
        scopes=GDRIVE_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    refresh_token = creds.refresh_token
    if not refresh_token:
        raise ValueError("Refresh token não foi retornado.")

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
    return {"user_email": user_email}

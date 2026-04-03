from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _build_service_from_service_account(credentials_json: str):
    payload = json.loads(credentials_json)
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(payload, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _build_service_from_oauth(
    client_id: str, client_secret: str, refresh_token: str
):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_backup_to_gdrive(
    file_path: Path,
    *,
    auth_mode: str,
    credentials_json: str = "",
    folder_id: str | None = None,
    shared_drive_id: str | None = None,
    oauth_client_id: str = "",
    oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
) -> Dict[str, Any]:
    """Upload a backup ZIP to Google Drive using a Service Account."""
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        return {
            "success": False,
            "message": "Google Drive SDK is not installed on the server.",
        }

    if auth_mode == "oauth":
        if not (oauth_client_id and oauth_client_secret and oauth_refresh_token):
            return {"success": False, "message": "Conta pessoal nao conectada."}
        try:
            service = _build_service_from_oauth(
                oauth_client_id, oauth_client_secret, oauth_refresh_token
            )
        except Exception as exc:
            return {"success": False, "message": f"Erro OAuth: {exc}"}
    else:
        if not credentials_json:
            return {"success": False, "message": "Service Account JSON not configured."}
        try:
            service = _build_service_from_service_account(credentials_json)
        except json.JSONDecodeError as exc:
            return {"success": False, "message": f"Invalid Service Account JSON: {exc}"}
        except Exception as exc:
            return {"success": False, "message": f"Erro Service Account: {exc}"}

    metadata = {"name": file_path.name}
    if folder_id:
        metadata["parents"] = [folder_id]
    elif shared_drive_id:
        metadata["parents"] = [shared_drive_id]

    media = MediaFileUpload(str(file_path), resumable=True)
    try:
        created = (
            service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name",
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if "storagequotaexceeded" in lowered or "quota" in lowered:
            message = "Cota do Google Drive excedida."
        return {"success": False, "message": f"Falha ao enviar para o Drive: {message}"}

    return {
        "success": True,
        "message": "Backup enviado ao Google Drive.",
        "file_id": created.get("id", ""),
        "file_name": created.get("name", file_path.name),
    }


def test_gdrive_connection(
    *,
    auth_mode: str,
    credentials_json: str = "",
    folder_id: str | None = None,
    shared_drive_id: str | None = None,
    oauth_client_id: str = "",
    oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
) -> Dict[str, Any]:
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return {
            "success": False,
            "message": "Google Drive SDK is not installed on the server.",
        }

    if auth_mode == "oauth":
        if not (oauth_client_id and oauth_client_secret and oauth_refresh_token):
            return {"success": False, "message": "Conta pessoal nao conectada."}
        try:
            service = _build_service_from_oauth(
                oauth_client_id, oauth_client_secret, oauth_refresh_token
            )
        except Exception as exc:
            return {"success": False, "message": f"Erro OAuth: {exc}"}
    else:
        if not credentials_json:
            return {"success": False, "message": "Service Account JSON not configured."}
        try:
            service = _build_service_from_service_account(credentials_json)
        except json.JSONDecodeError as exc:
            return {"success": False, "message": f"Invalid Service Account JSON: {exc}"}
        except Exception as exc:
            return {"success": False, "message": f"Erro Service Account: {exc}"}

    try:
        if folder_id:
            folder = (
                service.files()
                .get(
                    fileId=folder_id,
                    fields="id,name,mimeType",
                    supportsAllDrives=True,
                )
                .execute()
            )
            name = folder.get("name", "pasta")
            mime_type = folder.get("mimeType", "")
            if mime_type != "application/vnd.google-apps.folder":
                return {
                    "success": True,
                    "message": f"Acesso OK, mas o ID nao e de pasta: {name}.",
                }
            return {"success": True, "message": f"Acesso OK a pasta: {name}."}
        if shared_drive_id:
            drive = service.drives().get(driveId=shared_drive_id).execute()
            name = drive.get("name", "Shared Drive")
            return {"success": True, "message": f"Acesso OK ao Shared Drive: {name}."}

        about = service.about().get(fields="user").execute()
        user = (about or {}).get("user", {}).get("emailAddress", "")
        if user:
            return {"success": True, "message": f"Conexao OK ({user})."}
        return {"success": True, "message": "Conexao OK ao Google Drive."}
    except Exception as exc:
        return {"success": False, "message": f"Erro ao conectar no Drive: {exc}"}

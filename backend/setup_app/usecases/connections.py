"""Testes de ligação do ecrã de configuração: Zabbix, PostgreSQL, Redis, FTP, SMTP e SMS.

Saiu de `setup_app/api_views.py` em EV-0017e. Cada função recebe o dict do pedido, completa
o que falta com o `.env` onde a view legada o fazia, tenta a ligação e devolve um dict com
`message` (e campos extra); falha é `ConnectionTestError` (HTTP 400) — com `audit` preenchido
quando a view legada registava a falha em `ConfigurationAudit`.
"""

from __future__ import annotations

import base64
import ftplib
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlparse

import requests

from ..utils import env_manager

ZABBIX_TIMEOUT = 10
DB_CONNECT_TIMEOUT = 5
REDIS_CONNECT_TIMEOUT = 5
FTP_TIMEOUT = 8
SMTP_TIMEOUT = 10
SMS_TIMEOUT = 10
SMSNET_DEFAULT_URL = "https://sistema.smsnet.com.br/sms/global"
GMAIL_BAD_CREDENTIALS_HINT = (
    "Gmail rejeitou as credenciais. Verifique usuário/senha, ou use "
    "App Password/OAuth. Se for Workspace, considere smtp-relay.gmail.com."
)
SMS_PENDING_PROVIDERS = {
    "zenvia": "Integração Zenvia disponível para configuração. Envio será habilitado na próxima etapa.",
    "totalvoice": "Integração TotalVoice disponível para configuração. Envio será habilitado na próxima etapa.",
    "aws_sns": "Integração AWS SNS disponível para configuração. Envio será habilitado na próxima etapa.",
    "infobip": "Integração Infobip disponível para configuração. Envio será habilitado na próxima etapa.",
}


class ConnectionTestError(ValueError):
    """Teste falhou ou pedido inválido. `audit` é a mensagem a registar na auditoria (ou None
    quando a view legada não auditava, p. ex. campos em falta); `extra` vai para a resposta."""

    status = 400

    def __init__(self, message: str, *, audit: str | None = None, **extra: Any):
        super().__init__(message)
        self.audit = audit
        self.extra = extra


def _s(data: dict[str, Any], key: str, default: str = "") -> str:
    return str(data.get(key, default) or "").strip()


# ── Zabbix ───────────────────────────────────────────────────────────────────


def test_zabbix(data: dict[str, Any]) -> dict[str, Any]:
    """`apiinfo.version` sem auth e, conforme `auth_type`, `user.get` com Bearer ou `user.login`."""
    zabbix_url = _s(data, "zabbix_api_url")
    auth_type = data.get("auth_type", "login")
    api_key = _s(data, "zabbix_api_key")
    username = _s(data, "zabbix_api_user")
    password = _s(data, "zabbix_api_password")
    if not zabbix_url:
        raise ConnectionTestError("Zabbix URL is required")

    def _post(payload, headers=None):
        return requests.post(
            zabbix_url,
            json=payload,
            headers=headers or {"Content-Type": "application/json"},
            timeout=ZABBIX_TIMEOUT,
        )

    try:
        response = _post({"jsonrpc": "2.0", "method": "apiinfo.version", "params": {}, "id": 1})
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            error_payload = result.get("error", {})
            details = error_payload.get("data") or error_payload.get("message") or "API error"
            raise ConnectionTestError(
                f"Serviço respondeu com erro: {details}", audit=details, status="api_error"
            )
        version = result.get("result", "Unknown")

        if auth_type == "token" and api_key:
            # Zabbix 7.x+ exige o token no header Authorization: Bearer, não em `auth`
            auth_result = _post(
                {"jsonrpc": "2.0", "method": "user.get", "params": {"output": ["userid"]}, "id": 2},
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            ).json()
            if "error" in auth_result:
                error_message = auth_result.get("error", {}).get("message", "Unknown error")
                raise ConnectionTestError(
                    "Conexão OK, mas o token do Zabbix é inválido.",
                    audit=f"Invalid API token: {error_message}",
                    status="auth_failed",
                    version=version,
                    error_detail=error_message,
                )

        if auth_type == "login":
            if not username or not password:
                raise ConnectionTestError(
                    "Conexão OK, mas usuário/senha não foram informados.",
                    audit="Missing username/password",
                    status="auth_missing",
                    version=version,
                )
            login_result = _post(
                {
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {"username": username, "password": password},
                    "id": 2,
                }
            ).json()
            if "error" in login_result or not login_result.get("result"):
                raise ConnectionTestError(
                    "Conexão OK, mas a autenticação falhou.",
                    audit="Login failed",
                    status="auth_failed",
                    version=version,
                )
    except requests.exceptions.RequestException as exc:
        raise ConnectionTestError(
            f"Serviço offline: {exc}", audit=str(exc), status="offline"
        ) from exc

    return {
        "message": f"Serviço online. Zabbix v{version}.",
        "version": version,
        "status": "online",
    }


# ── PostgreSQL ───────────────────────────────────────────────────────────────


def test_database(data: dict[str, Any]) -> dict[str, Any]:
    db_host, db_port, db_name, db_user = (
        _s(data, "db_host"),
        _s(data, "db_port"),
        _s(data, "db_name"),
        _s(data, "db_user"),
    )
    db_password = _s(data, "db_password")
    if not all([db_host, db_port, db_name, db_user]):
        raise ConnectionTestError("All database fields are required except password")
    try:
        # psycopg (v3) direto: é o driver instalado (requirements) e evita a
        # contabilidade de aliases do Django.
        import psycopg

        conn = psycopg.connect(
            host=db_host,
            port=int(db_port),
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=DB_CONNECT_TIMEOUT,
        )
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version_full = cursor.fetchone()[0]
            version = version_full.split(",")[0] if "," in version_full else version_full
            cursor.close()
        finally:
            conn.close()
    except Exception as exc:
        raise ConnectionTestError(f"Connection failed: {exc}", audit=str(exc)) from exc
    return {"message": f"Connection successful! {version}", "version": version}


# ── Redis ────────────────────────────────────────────────────────────────────


def test_redis(data: dict[str, Any]) -> dict[str, Any]:
    redis_url = _s(data, "redis_url")
    if not redis_url:
        raise ConnectionTestError("Redis URL is required")
    try:
        import redis

        parsed = urlparse(redis_url)
        client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
            password=parsed.password,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
        )
        client.ping()
        redis_version = client.info().get("redis_version", "Unknown")
        client.close()
    except Exception as exc:
        raise ConnectionTestError(f"Connection failed: {exc}", audit=str(exc)) from exc
    return {
        "message": f"Connection successful! Redis version: {redis_version}",
        "version": redis_version,
    }


# ── FTP ──────────────────────────────────────────────────────────────────────


def test_ftp(data: dict[str, Any]) -> dict[str, Any]:
    """Credenciais do pedido; sem `ftp_host` completa tudo com o `.env`."""
    host = _s(data, "ftp_host")
    port_raw = _s(data, "ftp_port")
    username = _s(data, "ftp_user")
    password = _s(data, "ftp_password")
    remote_path = _s(data, "ftp_path")
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
        raise ConnectionTestError("FTP host is required.")
    try:
        port = int(port_raw) if port_raw else 21
    except ValueError:
        port = 21
    try:
        ftp = ftplib.FTP()
        ftp.connect(host=host, port=port, timeout=FTP_TIMEOUT)
        if username or password:
            ftp.login(user=username, passwd=password)
        else:
            ftp.login()
        if remote_path:
            ftp.cwd(remote_path)
        pwd = ftp.pwd()
        ftp.quit()
    except Exception as exc:
        raise ConnectionTestError(f"Connection failed: {exc}", audit=str(exc)) from exc
    return {"message": f"Connection successful! PWD: {pwd}"}


# ── SMTP ─────────────────────────────────────────────────────────────────────

_SMTP_ENV = {
    "host": "SMTP_HOST",
    "port_raw": "SMTP_PORT",
    "security": "SMTP_SECURITY",
    "username": "SMTP_USER",
    "password": "SMTP_PASSWORD",
    "auth_mode": "SMTP_AUTH_MODE",
    "oauth_client_id": "SMTP_OAUTH_CLIENT_ID",
    "oauth_client_secret": "SMTP_OAUTH_CLIENT_SECRET",
    "oauth_refresh_token": "SMTP_OAUTH_REFRESH_TOKEN",
    "from_name": "SMTP_FROM_NAME",
    "from_email": "SMTP_FROM_EMAIL",
    "recipient": "SMTP_TEST_RECIPIENT",
}


def _smtp_params(data: dict[str, Any]) -> dict[str, str]:
    params = {
        "host": _s(data, "smtp_host"),
        "port_raw": _s(data, "smtp_port"),
        "security": _s(data, "smtp_security").lower(),
        "username": _s(data, "smtp_user"),
        "password": str(data.get("smtp_password", "") or ""),
        "auth_mode": _s(data, "smtp_auth_mode").lower(),
        "oauth_client_id": _s(data, "smtp_oauth_client_id"),
        "oauth_client_secret": _s(data, "smtp_oauth_client_secret"),
        "oauth_refresh_token": _s(data, "smtp_oauth_refresh_token"),
        "from_name": _s(data, "smtp_from_name"),
        "from_email": _s(data, "smtp_from_email"),
        "recipient": _s(data, "smtp_test_recipient"),
        "test_message": _s(data, "smtp_test_message"),
    }
    values = env_manager.read_values(list(_SMTP_ENV.values()))
    for key, env_key in _SMTP_ENV.items():
        params[key] = params[key] or values.get(env_key, "")
    if not params["from_email"] and params["username"]:
        params["from_email"] = params["username"]
    params["auth_mode"] = params["auth_mode"] or "password"
    return params


def _xoauth2_token(username: str, client_id: str, client_secret: str, refresh_token: str) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://mail.google.com/"],
    )
    creds.refresh(Request())
    auth_string = f"user={username}\1auth=Bearer {creds.token}\1\1"
    return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")


def test_smtp(data: dict[str, Any]) -> dict[str, Any]:
    """Envia um email de teste. Falhas de rede/autenticação são `ConnectionTestError` auditadas;
    o erro 5.7.8 do Gmail ganha a dica de App Password/OAuth."""
    p = _smtp_params(data)
    missing = [
        label
        for label, value in (
            ("host", p["host"]),
            ("remetente", p["from_email"]),
            ("destinatário", p["recipient"]),
        )
        if not value
    ]
    if missing:
        raise ConnectionTestError(f"Campos obrigatórios ausentes: {', '.join(missing)}.")
    if p["auth_mode"] == "oauth":
        if not p["username"]:
            raise ConnectionTestError("Informe o usuário (email) para autenticação OAuth.")
        if not (p["oauth_client_id"] and p["oauth_client_secret"] and p["oauth_refresh_token"]):
            raise ConnectionTestError("Informe Client ID, Client Secret e Refresh Token do OAuth.")
    try:
        port = int(p["port_raw"]) if p["port_raw"] else (465 if p["security"] == "ssl" else 587)
    except ValueError:
        port = 587

    msg = EmailMessage()
    msg["Subject"] = "Teste SMTP - ProveMaps"
    msg["From"] = f"{p['from_name']} <{p['from_email']}>" if p["from_name"] else p["from_email"]
    msg["To"] = p["recipient"]
    msg.set_content(p["test_message"] or "Este é um email de teste do ProveMaps.")

    try:
        if p["security"] == "ssl":
            server = smtplib.SMTP_SSL(
                host=p["host"],
                port=port,
                context=ssl.create_default_context(),
                timeout=SMTP_TIMEOUT,
            )
            server.ehlo()
        else:
            server = smtplib.SMTP(host=p["host"], port=port, timeout=SMTP_TIMEOUT)
            server.ehlo()
            if p["security"] == "tls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
        if p["auth_mode"] == "oauth":
            token = _xoauth2_token(
                p["username"],
                p["oauth_client_id"],
                p["oauth_client_secret"],
                p["oauth_refresh_token"],
            )
            server.docmd("AUTH", "XOAUTH2 " + token)
        elif p["username"] and p["password"]:
            server.login(p["username"], p["password"])
        server.send_message(msg)
        server.quit()
    except Exception as exc:
        error_msg = str(exc)
        if "5.7.8" in error_msg or "BadCredentials" in error_msg:
            error_msg = GMAIL_BAD_CREDENTIALS_HINT
        raise ConnectionTestError(f"Falha ao enviar email: {error_msg}", audit=str(exc)) from exc
    return {"message": "Email enviado com sucesso."}


# ── SMS ──────────────────────────────────────────────────────────────────────

_SMS_ENV = {
    "provider": "SMS_PROVIDER",
    "username": "SMS_USERNAME",
    "password": "SMS_PASSWORD",
    "api_token": "SMS_API_TOKEN",
    "api_url": "SMS_API_URL",
    "sender_id": "SMS_SENDER_ID",
    "test_recipient": "SMS_TEST_RECIPIENT",
    "test_message": "SMS_TEST_MESSAGE",
    "priority": "SMS_PRIORITY",
    "infobip_base_url": "SMS_INFOBIP_BASE_URL",
    "aws_region": "SMS_AWS_REGION",
    "aws_access_key": "SMS_AWS_ACCESS_KEY_ID",
    "aws_secret": "SMS_AWS_SECRET_ACCESS_KEY",
}


def normalize_br_phone(raw: str) -> str:
    """Só dígitos; aceita DDD+número (10/11) com ou sem 55 à frente; devolve com 55 ou ''."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("55") and len(digits) in (12, 13):
        return digits
    if len(digits) in (10, 11):
        return f"55{digits}"
    return ""


def _sms_params(data: dict[str, Any]) -> dict[str, str]:
    params = {
        "provider": _s(data, "sms_provider").lower() or "smsnet",
        "username": _s(data, "sms_username"),
        "password": str(data.get("sms_password", "") or ""),
        "api_token": _s(data, "sms_api_token"),
        "api_url": _s(data, "sms_api_url"),
        "sender_id": _s(data, "sms_sender_id"),
        "test_recipient": _s(data, "sms_test_recipient"),
        "test_message": _s(data, "sms_test_message") or "Teste SMS ProveMaps.",
        "priority": _s(data, "sms_priority"),
        "infobip_base_url": _s(data, "sms_infobip_base_url"),
        "aws_region": _s(data, "sms_aws_region"),
        "aws_access_key": _s(data, "sms_aws_access_key_id"),
        "aws_secret": _s(data, "sms_aws_secret_access_key"),
    }
    values = env_manager.read_values(list(_SMS_ENV.values()))
    for key, env_key in _SMS_ENV.items():
        params[key] = params[key] or values.get(env_key, "smsnet" if key == "provider" else "")
    return params


def _require(fields: dict[str, str]) -> None:
    missing = [name for name, value in fields.items() if not value]
    if missing:
        raise ConnectionTestError(f"Campos obrigatórios ausentes: {', '.join(missing)}.")


def test_sms(data: dict[str, Any]) -> dict[str, Any]:
    """Devolve `{success, message}`: só o SMSNET envia de facto; os outros provedores respondem
    `success: False` com HTTP 200 («disponível para configuração»), como antes."""
    p = _sms_params(data)
    recipient = normalize_br_phone(p["test_recipient"])
    if not recipient:
        raise ConnectionTestError(
            "Telefone inválido. Use DDD + número (10 ou 11 dígitos), com ou sem 55."
        )
    provider = p["provider"]
    if provider == "smsnet":
        if not p["username"] or not p["password"]:
            raise ConnectionTestError("Usuário e senha são obrigatórios para SMSNET.")
        params = {
            "username": p["username"],
            "password": p["password"],
            "to": recipient,
            "msg": p["test_message"],
        }
        if p["priority"]:
            params["priority"] = p["priority"]
        response = requests.get(
            p["api_url"] or SMSNET_DEFAULT_URL, params=params, timeout=SMS_TIMEOUT
        )
        if response.status_code != 200:
            raise ConnectionTestError(f"Falha no envio SMSNET: HTTP {response.status_code}.")
        return {"success": True, "message": "SMS enviado com sucesso (SMSNET)."}
    if provider == "aws_sns":
        _require(
            {
                "região": p["aws_region"],
                "access key": p["aws_access_key"],
                "secret key": p["aws_secret"],
            }
        )
    if provider == "infobip":
        _require({"base URL": p["infobip_base_url"], "API token": p["api_token"]})
    if provider in SMS_PENDING_PROVIDERS:
        return {"success": False, "message": SMS_PENDING_PROVIDERS[provider]}
    raise ConnectionTestError("Provedor SMS não reconhecido.")

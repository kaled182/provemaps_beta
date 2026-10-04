"""API endpoints for setup configuration testing and management.

EV-0017: este módulo está a ser partido por domínio em `setup_app/api/<dominio>.py` +
`setup_app/usecases/<dominio>.py`. Backups e nuvem (0017a), ficheiro .env/configuração (0017b), gateways de mensagens/WhatsApp QR
(0017c) e vídeo/câmeras (0017d) já saíram.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .api._auth import staff_check as _staff_check  # compat: decoradores e testes importam daqui
from .models import CompanyProfile, MonitoringServer
from .models_audit import ConfigurationAudit
from .usecases.common import to_bool as _to_bool
from .utils import env_manager

logger = logging.getLogger(__name__)


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


def _serialize_company_profile(profile: CompanyProfile, request=None) -> dict[str, Any]:
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
            return JsonResponse({"success": False, "message": "Zabbix URL is required"}, status=400)

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
                    error_payload.get("data") or error_payload.get("message") or "API error"
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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server error: {e!s}"}, status=500)


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
            if "," in version_full:
                version = version_full.split(",")[0]
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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server error: {e!s}"}, status=500)


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
            from urllib.parse import urlparse

            import redis

            # Parse Redis URL
            parsed = urlparse(redis_url)

            # Create Redis client
            r = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                password=parsed.password,
                socket_connect_timeout=5,
            )

            # Test connection with PING
            r.ping()

            # Get Redis info
            info = r.info()
            redis_version = info.get("redis_version", "Unknown")

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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server error: {e!s}"}, status=500)


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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server error: {e!s}"}, status=500)


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
            missing = [
                name
                for name, value in {
                    "região": aws_region,
                    "access key": aws_access_key,
                    "secret key": aws_secret,
                }.items()
                if not value
            ]
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
            missing = [
                name
                for name, value in {
                    "base URL": infobip_base_url,
                    "API token": api_token,
                }.items()
                if not value
            ]
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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server error: {e!s}"}, status=500)


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


def _serialize_monitoring_server(server: MonitoringServer) -> dict[str, Any]:
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
        return JsonResponse(
            {
                "success": True,
                "servers": [_serialize_monitoring_server(server) for server in servers],
            }
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)

    name = data.get("name", "").strip()
    url = data.get("url", "").strip()
    server_type = data.get("server_type", "zabbix").strip() or "zabbix"
    auth_token = data.get("auth_token", "").strip()
    extra_config = (
        data.get("extra_config", {}) if isinstance(data.get("extra_config"), dict) else {}
    )
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

    return JsonResponse(
        {
            "success": True,
            "server": _serialize_monitoring_server(server),
        }
    )


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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)

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

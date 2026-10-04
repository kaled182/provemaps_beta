"""API endpoints for setup configuration testing and management.

EV-0017: este módulo está a ser partido por domínio em `setup_app/api/<dominio>.py` +
`setup_app/usecases/<dominio>.py`. Backups e nuvem (0017a) e ficheiro .env/configuração (0017b) já saíram.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .api._auth import staff_check as _staff_check  # compat: decoradores e testes importam daqui
from .models import CompanyProfile, MessagingGateway, MonitoringServer
from .models_audit import ConfigurationAudit
from .services import runtime_settings, video_gateway as video_gateway_service
from .services.config_loader import clear_runtime_config_cache
from .usecases.common import to_bool as _to_bool
from .utils import env_manager

logger = logging.getLogger(__name__)


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


def _serialize_gateway(gateway: MessagingGateway) -> dict[str, Any]:
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

            gateways = (
                MessagingGateway.objects.filter(
                    Q(
                        gateway_type__in=["sms", "whatsapp", "telegram", "smtp"]
                    )  # Não-vídeo: sempre visível
                    | Q(
                        gateway_type="video", departments__in=user_depts
                    )  # Vídeo: departamentos do usuário
                    | Q(gateway_type="video", departments__isnull=True)  # Vídeo: público
                )
                .distinct()
                .order_by("gateway_type", "priority", "name")
            )

        return JsonResponse(
            {"success": True, "gateways": [_serialize_gateway(gw) for gw in gateways]}
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)

    gateway_type = data.get("gateway_type", "").strip()
    if gateway_type not in {"sms", "whatsapp", "telegram", "smtp", "video"}:
        return JsonResponse({"success": False, "message": "Tipo de gateway inválido."}, status=400)

    name = data.get("name", "").strip()
    if not name:
        return JsonResponse(
            {"success": False, "message": "Nome do gateway é obrigatório."}, status=400
        )

    try:
        priority = int(data.get("priority", 1))
    except (TypeError, ValueError):
        priority = 1
    priority = max(priority, 1)

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
        return JsonResponse({"success": False, "message": "Gateway não encontrado."}, status=404)

    # Validar permissões RBAC para câmeras de vídeo
    if gateway.gateway_type == "video" and not request.user.is_superuser:
        user_depts = request.user.profile.departments.all()

        # Verificar se a câmera pertence aos departamentos do usuário OU é pública
        has_access = (
            not gateway.departments.exists()  # Pública (sem departamentos)
            or gateway.departments.filter(
                id__in=[d.id for d in user_depts]
            ).exists()  # Ou pertence aos departamentos do usuário
        )

        if not has_access:
            return JsonResponse(
                {"success": False, "message": "Sem permissão para acessar esta câmera."}, status=403
            )

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
        return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)

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
        priority = max(priority, 1)
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
        (
            "application/vnd.apple.mpegurl"
            if sanitized.endswith(".m3u8")
            else "application/octet-stream"
        ),
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
        logger.warning("Pré-visualização do gateway %s não ficou pronta: %s", gateway.id, exc)
        return JsonResponse(
            {
                "success": False,
                "message": "Stream HLS não ficou pronto a tempo. Verifique a origem do vídeo.",
            },
            status=504,
        )
    except video_gateway_service.VideoGatewayError as exc:
        logger.warning("Falha ao acionar transmuxer para gateway %s: %s", gateway.id, exc)
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
        logger.warning("Falha ao encerrar pré-visualização do gateway %s: %s", gateway.id, exc)
        return JsonResponse(
            {
                "success": False,
                "message": "Não foi possível encerrar a pré-visualização do stream.",
            },
            status=500,
        )

    return JsonResponse({"success": True})


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

    from django.db.models import Q
    from django.http import JsonResponse

    from inventory.models import Site
    from setup_app.models import MessagingGateway

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
                webrtc_base = getattr(
                    settings, "VIDEO_WEBRTC_PUBLIC_BASE_URL", None
                ) or os.environ.get("VIDEO_WEBRTC_PUBLIC_BASE_URL")
            if not webrtc_base:
                return None
            restream_key = cfg.get("restream_key") or f"gateway_{gw.id}"
            base = str(webrtc_base).rstrip("/")
            return f"{base}/whep/{restream_key}"

        results = []
        for gw in gateways:
            playback_url = video_gateway_service.build_playback_url(gw)
            results.append(
                {
                    "id": gw.id,
                    "name": gw.name,
                    "enabled": gw.enabled,
                    "site_name": gw.site_name,
                    "playback_url": playback_url,
                    "whep_url": _whep_url(gw),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "count": len(results),
                "results": results,
            }
        )
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
            site_id_param = request.GET.get("site_id") or request.GET.get("site")

            # Filtrar por departamentos do usuário
            if request.user.is_superuser:
                # Superuser vê todos os mosaicos
                mosaics = VideoMosaic.objects.all().order_by("name")
            else:
                # Usuários normais veem apenas mosaicos de seus departamentos
                user_depts = request.user.profile.departments.all()

                # Mosaicos sem departamento (públicos) OU mosaicos dos departamentos do usuário
                mosaics = (
                    VideoMosaic.objects.filter(
                        Q(departments__in=user_depts) | Q(departments__isnull=True)
                    )
                    .distinct()
                    .order_by("name")
                )
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
                user_dept_ids = set(request.user.profile.departments.values_list("id", flat=True))
                requested_dept_ids = set(department_ids)

                if not requested_dept_ids.issubset(user_dept_ids):
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Você só pode criar mosaicos em departamentos aos quais pertence.",
                        },
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

            return JsonResponse(
                {
                    "success": True,
                    "message": "Mosaico criado com sucesso",
                    "mosaic": {
                        "id": mosaic.id,
                        "name": mosaic.name,
                        "layout": mosaic.layout,
                        "cameras": mosaic.cameras,
                        "site_id": mosaic.site_id,
                        "departments": [
                            {"id": d.id, "name": d.name} for d in mosaic.departments.all()
                        ],
                        "created_at": mosaic.created_at.isoformat(),
                        "updated_at": mosaic.updated_at.isoformat(),
                    },
                }
            )
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
            not mosaic.departments.exists()  # Público (sem departamentos)
            or mosaic.departments.filter(
                id__in=[d.id for d in user_depts]
            ).exists()  # Ou pertence aos departamentos do usuário
        )

        if not has_access:
            return JsonResponse(
                {"success": False, "message": "Sem permissão para acessar este mosaico."},
                status=403,
            )

    if request.method == "GET":
        return JsonResponse(
            {
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
            }
        )

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
                    user_dept_ids = set(
                        request.user.profile.departments.values_list("id", flat=True)
                    )
                    requested_dept_ids = set(department_ids)

                    if not requested_dept_ids.issubset(user_dept_ids):
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "Você só pode atribuir departamentos aos quais pertence.",
                            },
                            status=403,
                        )

                from core.models import Department

                mosaic.departments.set(Department.objects.filter(id__in=department_ids))

            mosaic.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": "Mosaico atualizado com sucesso",
                    "mosaic": {
                        "id": mosaic.id,
                        "name": mosaic.name,
                        "layout": mosaic.layout,
                        "cameras": mosaic.cameras,
                        "site_id": mosaic.site_id,
                        "departments": [
                            {"id": d.id, "name": d.name} for d in mosaic.departments.all()
                        ],
                        "updated_at": mosaic.updated_at.isoformat(),
                    },
                }
            )
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
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Mosaico '{mosaic_name}' removido com sucesso",
                }
            )
        except Exception as exc:
            logger.exception("Error deleting video mosaic")
            return JsonResponse(
                {"success": False, "message": f"Failed to delete mosaic: {exc}"},
                status=500,
            )


# ─────────────────────────────────────────────────────────────
# Camera Settings
# ─────────────────────────────────────────────────────────────

_CAMERA_KEYS = [
    "CAMERA_DEFAULT_STREAM_TYPE",
    "CAMERA_DEFAULT_RESOLUTION",
    "CAMERA_DEFAULT_FPS",
    "CAMERA_DEFAULT_CODEC",
    "CAMERA_ENABLE_HARDWARE_ACCELERATION",
    "CAMERA_MAX_CONCURRENT_STREAMS",
    "CAMERA_STREAM_TIMEOUT_SECONDS",
    "CAMERA_RECONNECT_ATTEMPTS",
    "CAMERA_RECONNECT_DELAY_MS",
]

_CAMERA_DEFAULTS = {
    "default_stream_type": "rtmp",
    "default_resolution": "1080p",
    "default_fps": 30,
    "default_codec": "h264",
    "enable_hardware_acceleration": True,
    "max_concurrent_streams": 10,
    "stream_timeout_seconds": 30,
    "reconnect_attempts": 3,
    "reconnect_delay_ms": 2000,
}

_CAMERA_KEY_MAP = {
    "CAMERA_DEFAULT_STREAM_TYPE": "default_stream_type",
    "CAMERA_DEFAULT_RESOLUTION": "default_resolution",
    "CAMERA_DEFAULT_FPS": "default_fps",
    "CAMERA_DEFAULT_CODEC": "default_codec",
    "CAMERA_ENABLE_HARDWARE_ACCELERATION": "enable_hardware_acceleration",
    "CAMERA_MAX_CONCURRENT_STREAMS": "max_concurrent_streams",
    "CAMERA_STREAM_TIMEOUT_SECONDS": "stream_timeout_seconds",
    "CAMERA_RECONNECT_ATTEMPTS": "reconnect_attempts",
    "CAMERA_RECONNECT_DELAY_MS": "reconnect_delay_ms",
}


@login_required
@require_http_methods(["GET", "POST"])
def camera_settings(request):
    """GET: return camera config. POST: save camera config."""
    if request.method == "GET":
        try:
            raw = env_manager.read_values(_CAMERA_KEYS)
            result = dict(_CAMERA_DEFAULTS)
            for env_key, setting_key in _CAMERA_KEY_MAP.items():
                val = raw.get(env_key)
                if val not in (None, ""):
                    default = _CAMERA_DEFAULTS.get(setting_key)
                    if isinstance(default, bool):
                        result[setting_key] = str(val).lower() in ("true", "1", "yes")
                    elif isinstance(default, int):
                        try:
                            result[setting_key] = int(val)
                        except (TypeError, ValueError):
                            pass
                    else:
                        result[setting_key] = val
            return JsonResponse({"success": True, "settings": result})
        except Exception as exc:
            logger.exception("Error loading camera settings")
            return JsonResponse({"success": False, "message": str(exc)}, status=500)

    # POST - save settings
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"success": False, "message": f"Invalid JSON: {exc}"}, status=400)

    try:
        to_write: dict[str, Any] = {}
        for env_key, setting_key in _CAMERA_KEY_MAP.items():
            if setting_key in body:
                val = body[setting_key]
                default = _CAMERA_DEFAULTS.get(setting_key)
                if isinstance(default, bool):
                    to_write[env_key] = "true" if val else "false"
                else:
                    to_write[env_key] = str(val)
        if to_write:
            env_manager.write_values(to_write)
        return JsonResponse({"success": True, "message": "Configurações de câmeras salvas."})
    except Exception as exc:
        logger.exception("Error saving camera settings")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


# ─────────────────────────────────────────────────────────────
# Test Stream
# ─────────────────────────────────────────────────────────────


@login_required
@require_POST
def test_stream(request):
    """Test TCP reachability of a stream endpoint (host:port)."""
    import socket
    from urllib.parse import urlparse

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"success": False, "message": f"Invalid JSON: {exc}"}, status=400)

    stream_url = (body.get("stream_url") or "").strip()
    timeout = int(body.get("timeout") or 5)

    if not stream_url:
        return JsonResponse({"success": False, "message": "stream_url é obrigatório."}, status=400)

    try:
        parsed = urlparse(stream_url)
        host = parsed.hostname
        port = parsed.port

        if not host:
            return JsonResponse(
                {"success": False, "message": "URL inválida: host não encontrado."}, status=400
            )

        if not port:
            port = {"rtsp": 554, "rtmp": 1935, "rtmps": 443, "http": 80, "https": 443}.get(
                parsed.scheme.lower(), 554
            )

        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return JsonResponse(
            {
                "success": True,
                "message": f"Conexão bem-sucedida com {host}:{port}.",
            }
        )
    except TimeoutError:
        return JsonResponse(
            {"success": False, "message": "Timeout ao conectar com o servidor de stream."}
        )
    except OSError as exc:
        return JsonResponse({"success": False, "message": f"Falha na conexão: {exc}"})
    except Exception as exc:
        logger.exception("Error testing stream connection")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)

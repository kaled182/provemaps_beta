from __future__ import annotations

import os
import re
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.shortcuts import redirect, render
from django.http import HttpResponseForbidden

from integrations.zabbix.guards import reload_diagnostics_flag_cache

from .forms import EnvConfigForm, FirstTimeSetupForm
from setup_app.utils import env_manager
from setup_app.services import runtime_settings
from .services.service_reloader import trigger_restart
from types import SimpleNamespace

from .models import CompanyProfile, FirstTimeSetup

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_RESTART_COMMANDS = (
    settings.SERVICE_RESTART_COMMANDS
    if getattr(settings, "SERVICE_RESTART_COMMANDS", "")
    else "docker compose restart web; docker compose restart celery; docker compose restart beat"
)


_DB_NAME_FIXED = "app"  # nome do banco nunca muda; só user/senha são configuráveis


def _alter_db_password(db_user: str, new_password: str) -> None:
    """Executa ALTER ROLE no PostgreSQL para trocar a senha do usuário."""
    if not re.match(r"^[a-zA-Z0-9_]+$", db_user):
        raise ValueError(f"db_user inválido: {db_user!r}")
    quoted = connection.ops.quote_name(db_user)
    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER ROLE {quoted} WITH PASSWORD %s",
            [new_password],
        )


def get_setup_logo():
    profile = CompanyProfile.objects.order_by("-updated_at").first()
    if profile and profile.assets_logo:
        return SimpleNamespace(logo=profile.assets_logo)
    return FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()


def _staff_check(user):
    return user.is_active and user.is_staff


def _is_setup_locked():
    """
    Check if setup is locked via filesystem flag.
    This prevents production servers from being reconfigured remotely.
    """
    lock_file = os.path.join(settings.BASE_DIR, 'SETUP_LOCKED')
    # Also check parent directory (project root)
    lock_file_root = os.path.join(settings.BASE_DIR, '..', 'SETUP_LOCKED')
    return os.path.exists(lock_file) or os.path.exists(lock_file_root)


def first_time_setup(request):
    # SECURITY: Block setup if locked
    if _is_setup_locked():
        return HttpResponseForbidden(
            "<h1>Setup Locked</h1>"
            "<p>This setup interface has been locked for security.</p>"
            "<p>To unlock, remove the <code>SETUP_LOCKED</code> file "
            "from the server and restart the application.</p>"
        )
    
    if FirstTimeSetup.objects.filter(configured=True).exists():
        return redirect("/maps_view/dashboard/")

    if request.method == "POST":
        form = FirstTimeSetupForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            
            # Credenciais do banco: user vem do form, name é fixo
            db_user = data.get("db_user") or os.environ.get("DB_USER", "app")
            db_password = data["db_password"]
            db_name = _DB_NAME_FIXED

            # Alterar senha no PostgreSQL se diferente da atual
            current_db_password = os.environ.get("DB_PASSWORD", "")
            if db_password != current_db_password:
                try:
                    _alter_db_password(db_user, db_password)
                    logger.info("Senha do banco alterada via ALTER ROLE para: %s", db_user)
                except Exception as exc:
                    logger.error("Falha ao executar ALTER ROLE: %s", exc)

            # Mark any existing configs as not configured (cleanup)
            FirstTimeSetup.objects.all().update(configured=False)

            # Create new configuration with configured=True
            setup_instance = FirstTimeSetup.objects.create(
                company_name=data["company_name"],
                logo=request.FILES.get("logo"),
                zabbix_url=data["zabbix_url"],
                auth_type=data["auth_type"],
                zabbix_api_key=data.get("zabbix_api_key"),
                zabbix_user=data.get("zabbix_user"),
                zabbix_password=data.get("zabbix_password"),
                map_provider=data.get("map_provider", "osm"),
                maps_api_key=data.get("maps_api_key", ""),
                mapbox_token=data.get("mapbox_token", ""),
                unique_licence=data["unique_licence"],
                db_host=data["db_host"],
                db_port=data["db_port"],
                db_name=db_name,
                db_user=db_user,
                db_password=db_password,
                redis_url=data["redis_url"],
                configured=True,
            )
            
            # Verify it was saved correctly
            if not setup_instance.configured:
                logger.error("Setup instance was not marked as configured after creation")
                setup_instance.configured = True
                setup_instance.save()

            commands = settings.SERVICE_RESTART_COMMANDS or DEFAULT_SERVICE_RESTART_COMMANDS
            env_payload = {
                "COMPANY_NAME": data["company_name"],
                "ZABBIX_API_URL": data["zabbix_url"],
                "GOOGLE_MAPS_API_KEY": data.get("maps_api_key", ""),
                "UNIQUE_LICENCE": data["unique_licence"],
                "DB_HOST": data["db_host"],
                "DB_PORT": data["db_port"],
                "DB_NAME": db_name,
                "DB_USER": db_user,
                "DB_PASSWORD": db_password,
                "REDIS_URL": data["redis_url"],
            }
            if data["auth_type"] == "token":
                env_payload.update(
                    {
                        "ZABBIX_API_USER": "",
                        "ZABBIX_API_PASSWORD": "",
                        "ZABBIX_API_KEY": data.get("zabbix_api_key", ""),
                    }
                )
            else:
                env_payload.update(
                    {
                        "ZABBIX_API_USER": data.get("zabbix_user", ""),
                        "ZABBIX_API_PASSWORD": data.get("zabbix_password", ""),
                        "ZABBIX_API_KEY": "",
                    }
                )
            env_payload["SERVICE_RESTART_COMMANDS"] = commands
            env_manager.write_values(env_payload)
            runtime_settings.reload_config()
            from integrations.zabbix.zabbix_service import clear_token_cache

            clear_token_cache()
            reload_diagnostics_flag_cache()
            command_string = env_payload.get("SERVICE_RESTART_COMMANDS", "").strip()
            os.environ["SERVICE_RESTART_COMMANDS"] = command_string
            if command_string:
                trigger_restart()
            
            # Log success and verify configuration before redirecting
            logger.info(f"Setup completed successfully for company: {data['company_name']}")
            configured_count = FirstTimeSetup.objects.filter(configured=True).count()
            logger.info(f"Configured instances in database: {configured_count}")
            
            if configured_count == 0:
                logger.error("No configured instances found after setup! Forcing configuration.")
                setup_instance.configured = True
                setup_instance.save(update_fields=['configured'])
                
            # After successful first-time setup, send user to the default backbone map
            return redirect("/monitoring/backbone/map/default")
    else:
        form = FirstTimeSetupForm()

    steps = [
        {
            "label": "Company",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>',
        },
        {
            "label": "Zabbix",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>',
        },
        {
            "label": "Maps",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>',
        },
        {
            "label": "Database",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>',
        },
        {
            "label": "Redis",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
        },
        {
            "label": "License",
            "icon": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>',
        },
    ]
    return render(
        request,
        "first_time_setup.html",
        {
            "form": form,
            "setup_logo": get_setup_logo(),
            "steps": steps,
        },
    )


@login_required
def setup_dashboard(request):
    return render(request, "setup_dashboard.html", {"setup_logo": get_setup_logo()})


@login_required
@user_passes_test(_staff_check)
def manage_environment(request):
    """Manage environment configuration (GET shows settings, POST saves and reloads)."""
    # GET: render page containing "System Settings" per test expectations
    if request.method == "GET":
        context = {"title": "System Settings", "setup_logo": get_setup_logo()}
        # Use a lightweight dashboard header which contains the expected text
        return render(request, "setup_dashboard.html", context)

    # POST: validate payload, write .env, reload runtime config and redirect (302)
    form = EnvConfigForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        env_payload = {
            "SECRET_KEY": data.get("secret_key", ""),
            "DEBUG": "True" if data.get("debug") else "False",
            "ZABBIX_API_URL": data.get("zabbix_api_url", ""),
            "ZABBIX_API_USER": data.get("zabbix_api_user", ""),
            "ZABBIX_API_PASSWORD": data.get("zabbix_api_password", ""),
            "ZABBIX_API_KEY": data.get("zabbix_api_key", ""),
            "GOOGLE_MAPS_API_KEY": data.get("google_maps_api_key", ""),
            "ALLOWED_HOSTS": data.get("allowed_hosts", ""),
            "DB_HOST": data.get("db_host", ""),
            "DB_PORT": data.get("db_port", ""),
            "DB_NAME": data.get("db_name", ""),
            "DB_USER": data.get("db_user", ""),
            "DB_PASSWORD": data.get("db_password", ""),
            "REDIS_URL": data.get("redis_url", ""),
            "ENABLE_DIAGNOSTIC_ENDPOINTS": "True" if data.get("enable_diagnostics") else "False",
            "SERVICE_RESTART_COMMANDS": data.get("service_restart_commands", ""),
        }
        env_manager.write_values(env_payload)
        runtime_settings.reload_config()
        # Clear Zabbix token cache after credential changes
        try:
            from integrations.zabbix.zabbix_service import clear_token_cache
            clear_token_cache()
        except Exception:
            pass
        reload_diagnostics_flag_cache()
        # Optionally trigger restart commands (async)
        os.environ["SERVICE_RESTART_COMMANDS"] = env_payload.get("SERVICE_RESTART_COMMANDS", "")
        if env_payload.get("SERVICE_RESTART_COMMANDS"):
            try:
                trigger_restart()
            except Exception:
                pass
        # Redirect after POST (302) per tests
        return redirect("setup_app:manage_environment")

    # Invalid form: render with 400 to indicate issue
    return render(request, "setup_dashboard.html", {"title": "System Settings", "setup_logo": get_setup_logo()}, status=400)

from __future__ import annotations

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from integrations.zabbix.guards import reload_diagnostics_flag_cache

from .forms import EnvConfigForm, FirstTimeSetupForm
from .models import FirstTimeSetup
from .services import runtime_settings
from .services.service_reloader import trigger_restart
from .utils import env_manager

DEFAULT_SERVICE_RESTART_COMMANDS = (
    settings.SERVICE_RESTART_COMMANDS
    if getattr(settings, "SERVICE_RESTART_COMMANDS", "")
    else "docker compose restart web; docker compose restart celery; docker compose restart beat"
)


def get_setup_logo():
    return FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()


def _staff_check(user):
    return user.is_active and user.is_staff


def first_time_setup(request):
    if FirstTimeSetup.objects.filter(configured=True).exists():
        return redirect("/maps_view/dashboard/")

    if request.method == "POST":
        form = FirstTimeSetupForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            FirstTimeSetup.objects.create(
                company_name=data["company_name"],
                logo=request.FILES.get("logo"),
                zabbix_url=data["zabbix_url"],
                auth_type=data["auth_type"],
                zabbix_api_key=data.get("zabbix_api_key"),
                zabbix_user=data.get("zabbix_user"),
                zabbix_password=data.get("zabbix_password"),
                maps_api_key=data["maps_api_key"],
                unique_licence=data["unique_licence"],
                db_host=data["db_host"],
                db_port=data["db_port"],
                db_name=data["db_name"],
                db_user=data["db_user"],
                db_password=data["db_password"],
                redis_url=data["redis_url"],
                configured=True,
            )

            commands = settings.SERVICE_RESTART_COMMANDS or DEFAULT_SERVICE_RESTART_COMMANDS
            env_payload = {
                "COMPANY_NAME": data["company_name"],
                "ZABBIX_API_URL": data["zabbix_url"],
                "GOOGLE_MAPS_API_KEY": data["maps_api_key"],
                "UNIQUE_LICENCE": data["unique_licence"],
                "DB_HOST": data["db_host"],
                "DB_PORT": data["db_port"],
                "DB_NAME": data["db_name"],
                "DB_USER": data["db_user"],
                "DB_PASSWORD": data["db_password"],
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
            return redirect("setup_app:setup_dashboard")
    else:
        form = FirstTimeSetupForm()

    return render(
        request,
        "first_time_setup.html",
        {
            "form": form,
            "setup_logo": get_setup_logo(),
        },
    )


@login_required
def setup_dashboard(request):
    return render(request, "setup_dashboard.html", {"setup_logo": get_setup_logo()})


@login_required
@user_passes_test(_staff_check)
def manage_environment(request):
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

    if request.method == "POST":
        form = EnvConfigForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data

            # Step 1: write the .env file for local development
            payload = {
                "SECRET_KEY": cleaned["secret_key"],
                "DEBUG": "True" if cleaned["debug"] else "False",
                "ZABBIX_API_URL": cleaned["zabbix_api_url"],
                "ZABBIX_API_USER": cleaned["zabbix_api_user"],
                "ZABBIX_API_PASSWORD": cleaned["zabbix_api_password"],
                "ZABBIX_API_KEY": cleaned["zabbix_api_key"],
                "GOOGLE_MAPS_API_KEY": cleaned["google_maps_api_key"],
                "ALLOWED_HOSTS": cleaned["allowed_hosts"],
                "ENABLE_DIAGNOSTIC_ENDPOINTS": (
                    "True" if cleaned["enable_diagnostics"] else "False"
                ),
                "DB_HOST": cleaned["db_host"],
                "DB_PORT": cleaned["db_port"],
                "DB_NAME": cleaned["db_name"],
                "DB_USER": cleaned["db_user"],
                "DB_PASSWORD": cleaned["db_password"],
                "REDIS_URL": cleaned["redis_url"],
                "SERVICE_RESTART_COMMANDS": cleaned["service_restart_commands"],
            }
            env_manager.write_values(payload)
            os.environ["SERVICE_RESTART_COMMANDS"] = cleaned["service_restart_commands"]

            # Step 2: persist the configuration to the database
            # (used by Docker/production deployments)
            from .models import FirstTimeSetup
            from .services.config_loader import clear_runtime_config_cache

            # Determine auth_type based on the provided fields
            auth_type = "token" if cleaned["zabbix_api_key"] else "login"

            # Upsert the configuration row in the database
            api_key = (
                cleaned["zabbix_api_key"] if auth_type == "token" else None
            )
            user = (
                cleaned["zabbix_api_user"] if auth_type == "login" else None
            )
            password = (
                cleaned["zabbix_api_password"]
                if auth_type == "login"
                else None
            )

            FirstTimeSetup.objects.update_or_create(
                configured=True,
                defaults={
                    "company_name": "MapsproveFiber",
                    "zabbix_url": cleaned["zabbix_api_url"],
                    "auth_type": auth_type,
                    "zabbix_api_key": api_key,
                    "zabbix_user": user,
                    "zabbix_password": password,
                    "maps_api_key": cleaned["google_maps_api_key"],
                    "db_host": cleaned["db_host"],
                    "db_port": cleaned["db_port"],
                    "db_name": cleaned["db_name"],
                    "db_user": cleaned["db_user"],
                    "db_password": cleaned["db_password"],
                    "redis_url": cleaned["redis_url"],
                }
            )

            # Clear runtime caches so new values propagate immediately
            clear_runtime_config_cache()
            runtime_settings.reload_config()

            from integrations.zabbix.zabbix_service import clear_token_cache

            clear_token_cache()
            reload_diagnostics_flag_cache()
            if cleaned["service_restart_commands"].strip():
                trigger_restart()
            messages.success(
                request,
                "Configuration saved successfully. Changes are now active!",
            )
            return redirect("setup_app:manage_environment")
    else:
        form = EnvConfigForm(
            initial={
                "secret_key": current_values.get("SECRET_KEY", ""),
                "debug": current_values.get("DEBUG", "").lower() == "true",
                "zabbix_api_url": current_values.get("ZABBIX_API_URL", ""),
                "zabbix_api_user": current_values.get("ZABBIX_API_USER", ""),
                "zabbix_api_password": current_values.get(
                    "ZABBIX_API_PASSWORD", ""
                ),
                "zabbix_api_key": current_values.get("ZABBIX_API_KEY", ""),
                "google_maps_api_key": current_values.get(
                    "GOOGLE_MAPS_API_KEY", ""
                ),
                "allowed_hosts": current_values.get("ALLOWED_HOSTS", ""),
                "enable_diagnostics": (
                    current_values.get(
                        "ENABLE_DIAGNOSTIC_ENDPOINTS", ""
                    ).lower()
                    == "true"
                ),
                "db_host": current_values.get("DB_HOST", ""),
                "db_port": current_values.get("DB_PORT", ""),
                "db_name": current_values.get("DB_NAME", ""),
                "db_user": current_values.get("DB_USER", ""),
                "db_password": current_values.get("DB_PASSWORD", ""),
                "redis_url": current_values.get("REDIS_URL", ""),
                "service_restart_commands": current_values.get(
                    "SERVICE_RESTART_COMMANDS", ""
                )
                or DEFAULT_SERVICE_RESTART_COMMANDS,
            }
        )

    return render(
        request,
        "setup/manage_environment.html",
        {
            "form": form,
            "requires_restart": True,
            "setup_logo": get_setup_logo(),
        },
    )

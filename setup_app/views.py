from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from zabbix_api.guards import reload_diagnostics_flag_cache

from .forms import EnvConfigForm, FirstTimeSetupForm
from .models import FirstTimeSetup
from .services import runtime_settings
from .utils import env_manager


def get_setup_logo():
    return FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()


def _staff_check(user):
    return user.is_active and user.is_staff


@login_required
def first_time_setup(request):
    if FirstTimeSetup.objects.filter(configured=True).exists():
        return redirect("setup_app:setup_dashboard")

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
                configured=True,
            )

            env_payload = {
                "COMPANY_NAME": data["company_name"],
                "ZABBIX_API_URL": data["zabbix_url"],
                "GOOGLE_MAPS_API_KEY": data["maps_api_key"],
                "UNIQUE_LICENCE": data["unique_licence"],
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
            env_manager.write_values(env_payload)
            runtime_settings.reload_config()
            from zabbix_api.services.zabbix_service import clear_token_cache

            clear_token_cache()
            reload_diagnostics_flag_cache()
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
    ]
    current_values = env_manager.read_values(editable_keys)

    if request.method == "POST":
        form = EnvConfigForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data

            # 1. Salva no arquivo .env (para desenvolvimento local)
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
            }
            env_manager.write_values(payload)

            # 2. Salva no banco de dados (para Docker/produção)
            from .models import FirstTimeSetup
            from .services.config_loader import clear_runtime_config_cache

            # Determina auth_type baseado nos campos preenchidos
            auth_type = "token" if cleaned["zabbix_api_key"] else "login"

            # Atualiza ou cria configuração
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
                }
            )

            # Limpa cache de configuração
            clear_runtime_config_cache()
            runtime_settings.reload_config()

            from zabbix_api.services.zabbix_service import clear_token_cache

            clear_token_cache()
            reload_diagnostics_flag_cache()
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
                    current_values.get("ENABLE_DIAGNOSTIC_ENDPOINTS", "").lower()
                    == "true"
                ),
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

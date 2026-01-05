from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.http import HttpResponseForbidden

from integrations.zabbix.guards import reload_diagnostics_flag_cache

from .forms import EnvConfigForm, FirstTimeSetupForm
from .models import FirstTimeSetup

DEFAULT_SERVICE_RESTART_COMMANDS = (
    settings.SERVICE_RESTART_COMMANDS
    if getattr(settings, "SERVICE_RESTART_COMMANDS", "")
    else "docker compose restart web; docker compose restart celery; docker compose restart beat"
)


def get_setup_logo():
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
    """Serve the Vue-based configuration page."""
    context = {"title": "System Settings", "setup_logo": get_setup_logo()}
    return render(request, "spa.html", context)

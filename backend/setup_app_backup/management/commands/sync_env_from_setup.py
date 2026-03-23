from __future__ import annotations

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from setup_app.models import FirstTimeSetup
from setup_app.utils import env_manager
from setup_app.services.service_reloader import trigger_restart


class Command(BaseCommand):
    help = "Regenerate the .env file based on the latest FirstTimeSetup record."

    def handle(self, *args, **options):
        record = (
            FirstTimeSetup.objects.filter(configured=True)
            .order_by("-configured_at")
            .first()
        )
        if not record:
            raise CommandError(
                "No configured FirstTimeSetup entry found. "
                "Complete the initial setup before running this command."
            )

        payload = {
            "COMPANY_NAME": record.company_name or "",
            "ZABBIX_API_URL": record.zabbix_url or "",
            "GOOGLE_MAPS_API_KEY": record.maps_api_key or "",
            "UNIQUE_LICENCE": record.unique_licence or "",
            "DB_HOST": record.db_host or "",
            "DB_PORT": record.db_port or "",
            "DB_NAME": record.db_name or "",
            "DB_USER": record.db_user or "",
            "DB_PASSWORD": record.db_password or "",
            "REDIS_URL": record.redis_url or "",
            "SERVICE_RESTART_COMMANDS": os.getenv(
                "SERVICE_RESTART_COMMANDS",
                getattr(settings, "SERVICE_RESTART_COMMANDS", ""),
            ),
        }

        if record.auth_type == "token":
            payload.update(
                {
                    "ZABBIX_API_USER": "",
                    "ZABBIX_API_PASSWORD": "",
                    "ZABBIX_API_KEY": record.zabbix_api_key or "",
                }
            )
        else:
            payload.update(
                {
                    "ZABBIX_API_USER": record.zabbix_user or "",
                    "ZABBIX_API_PASSWORD": record.zabbix_password or "",
                    "ZABBIX_API_KEY": "",
                }
            )

        env_manager.write_values(payload)
        os.environ["SERVICE_RESTART_COMMANDS"] = payload["SERVICE_RESTART_COMMANDS"]
        self.stdout.write(
            self.style.SUCCESS(f".env synchronised at {env_manager.ENV_PATH}")
        )
        if trigger_restart(async_mode=False):
            self.stdout.write(self.style.SUCCESS("Service restart commands executed."))
        else:
            self.stdout.write("No service restart commands configured; skipped restart.")

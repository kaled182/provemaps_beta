import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from setup_app.services import runtime_settings
from setup_app.utils import env_manager


class Command(BaseCommand):
    help = "Cria um backup completo do banco de dados PostGIS"

    def handle(self, *args, **options):
        backup_dir = Path(settings.BASE_DIR) / "database" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"postgis_backup_{timestamp}.zip"
        filepath = backup_dir / filename

        runtime_config = runtime_settings.get_runtime_config()
        db_name = runtime_config.db_name
        db_user = runtime_config.db_user
        db_host = runtime_config.db_host
        db_port = runtime_config.db_port
        db_pass = runtime_config.db_password

        if not all([db_name, db_user, db_host, db_port]):
            raise RuntimeError("Database configuration is incomplete.")

        self.stdout.write(f"Iniciando backup de {db_name} em {db_host}...")

        env = os.environ.copy()
        if db_pass:
            env["PGPASSWORD"] = str(db_pass)

        with tempfile.TemporaryDirectory(dir=backup_dir) as temp_dir:
            temp_dir_path = Path(temp_dir)
            dump_path = temp_dir_path / f"postgis_backup_{timestamp}.dump"
            metadata_path = temp_dir_path / f"postgis_backup_{timestamp}.config.json"

            cmd = [
                "pg_dump",
                "-h",
                str(db_host),
                "-p",
                str(db_port),
                "-U",
                str(db_user),
                "-F",
                "c",
                "-b",
                "-v",
                "-f",
                str(dump_path),
                str(db_name),
            ]

            try:
                subprocess.run(
                    cmd,
                    env=env,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "O comando 'pg_dump' nao foi encontrado. Instale 'postgresql-client' no container do backend."
                ) from exc
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.strip() if exc.stderr else ""
                raise RuntimeError(f"Erro no pg_dump: {stderr}") from exc

            config_keys = [
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
                "BACKUP_RETENTION_DAYS",
                "BACKUP_RETENTION_COUNT",
            ]
            config_snapshot = env_manager.read_values(config_keys)
            env_payload = ""
            if env_manager.ENV_PATH.exists():
                env_payload = env_manager.ENV_PATH.read_text(encoding="utf-8")

            metadata = {
                "backup_file": filename,
                "created_at": datetime.now().isoformat(),
                "app_version": os.getenv("APP_VERSION", "dev"),
                "static_asset_version": getattr(settings, "STATIC_ASSET_VERSION", ""),
                "env_file": env_payload,
                "configuration": config_snapshot,
            }
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            values = env_manager.read_values(["BACKUP_ZIP_PASSWORD", "SECRET_KEY"])
            password = values.get("BACKUP_ZIP_PASSWORD", "").strip()
            if len(password) < 8:
                raise RuntimeError(
                    "A senha do backup precisa ter pelo menos 8 caracteres."
                )

            try:
                import pyzipper
            except ImportError as exc:
                raise RuntimeError(
                    "pyzipper is required for encrypted backups. Install it in the backend environment."
                ) from exc

            with pyzipper.AESZipFile(
                filepath,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zipf:
                zipf.setpassword(password.encode("utf-8"))
                zipf.write(dump_path, dump_path.name)
                zipf.write(metadata_path, metadata_path.name)

        size_mb = filepath.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"Backup criado com sucesso: {filename}"))
        self.stdout.write(f"Tamanho: {size_mb:.2f} MB")
        return filename

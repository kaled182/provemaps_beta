import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Restaura um backup. CUIDADO: Apaga dados atuais."

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str, help="Nome do arquivo .dump/.sql na pasta de backups")

    def handle(self, *args, **options):
        filename = options["filename"]
        backup_path = Path(settings.BASE_DIR) / "database" / "backups" / filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {backup_path}")

        db_conf = settings.DATABASES["default"]
        db_name = db_conf.get("NAME", "")
        db_user = db_conf.get("USER", "")
        db_host = db_conf.get("HOST", "")
        db_port = db_conf.get("PORT", "")
        db_pass = db_conf.get("PASSWORD", "")

        if not all([db_name, db_user, db_host, db_port]):
            raise RuntimeError("Database configuration is incomplete.")

        env = os.environ.copy()
        if db_pass:
            env["PGPASSWORD"] = str(db_pass)

        if backup_path.suffix.lower() == ".dump":
            cmd = [
                "pg_restore",
                "-h",
                str(db_host),
                "-p",
                str(db_port),
                "-U",
                str(db_user),
                "-d",
                str(db_name),
                "-c",
                "-v",
                str(backup_path),
            ]
        elif backup_path.suffix.lower() == ".sql":
            cmd = [
                "psql",
                "-h",
                str(db_host),
                "-p",
                str(db_port),
                "-U",
                str(db_user),
                "-d",
                str(db_name),
                "-f",
                str(backup_path),
            ]
        else:
            raise RuntimeError("Formato de backup nao suportado.")

        try:
            self.stdout.write(f"Restaurando {filename}...")
            subprocess.run(cmd, env=env, check=True, text=True)
            self.stdout.write(self.style.SUCCESS("Restauracao concluida!"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Os comandos 'pg_restore/psql' nao foram encontrados. Instale 'postgresql-client' no container do backend."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Erro no restore: {exc}") from exc

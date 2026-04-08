import json
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Restaura um backup. CUIDADO: Apaga dados atuais."

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str, help="Nome do arquivo .dump/.sql na pasta de backups")
        parser.add_argument(
            "--config-json",
            type=str,
            default="",
            help="Caminho opcional para o .config.json extraído do backup (para restaurar fernet_key)",
        )

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
                "-h", str(db_host),
                "-p", str(db_port),
                "-U", str(db_user),
                "-d", str(db_name),
                "-c",            # drop before recreate
                "--if-exists",   # skip errors for missing objects
                "--no-owner",    # ignore ownership differences
                "--no-privileges",
                "-v",
                str(backup_path),
            ]
        elif backup_path.suffix.lower() == ".sql":
            cmd = [
                "psql",
                "-h", str(db_host),
                "-p", str(db_port),
                "-U", str(db_user),
                "-d", str(db_name),
                "-f", str(backup_path),
            ]
        else:
            raise RuntimeError("Formato de backup nao suportado.")

        try:
            self.stdout.write(f"Restaurando {filename}...")
            result = subprocess.run(
                cmd,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if result.returncode != 0:
                stderr_lines = result.stderr or ""
                real_errors = [
                    line for line in stderr_lines.splitlines()
                    if "ERROR:" in line and "does not exist" not in line
                ]
                if real_errors:
                    raise RuntimeError("Erro no restore:\n" + "\n".join(real_errors[:10]))
                self.stderr.write(f"[restore_db] Avisos nao fatais:\n{stderr_lines[:500]}")

            self.stdout.write(self.style.SUCCESS("Restauracao do banco concluida!"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Os comandos 'pg_restore/psql' nao foram encontrados."
            ) from exc

        # Restore the Fernet key from the backup config.json so that
        # EncryptedCharFields in the restored database can be decrypted.
        config_json_path = options.get("config_json", "")
        if not config_json_path:
            # Auto-detect: same name as dump but with .config.json extension
            stem = backup_path.stem  # e.g. postgis_backup_20260408_122501
            candidate = backup_path.parent / f"{stem}.config.json"
            if candidate.exists():
                config_json_path = str(candidate)

        if config_json_path and Path(config_json_path).exists():
            try:
                metadata = json.loads(Path(config_json_path).read_text(encoding="utf-8"))
                fernet_key = metadata.get("fernet_key", "").strip()
                if fernet_key:
                    fernet_key_file = Path(settings.BASE_DIR) / "database" / "fernet.key"
                    fernet_key_file.write_text(fernet_key, encoding="utf-8")
                    self.stdout.write(self.style.SUCCESS(
                        f"fernet.key atualizado com a chave do backup."
                    ))
                else:
                    self.stderr.write("[restore_db] config.json nao contem fernet_key — chave nao atualizada.")
            except Exception as exc:
                self.stderr.write(f"[restore_db] Nao foi possivel restaurar fernet_key: {exc}")
        else:
            self.stderr.write("[restore_db] config.json nao encontrado — fernet_key nao atualizada.")

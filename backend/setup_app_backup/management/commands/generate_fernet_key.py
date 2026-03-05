from __future__ import annotations

from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand, CommandError

from setup_app.utils import env_manager


class Command(BaseCommand):
    help = "Generate a Fernet key compatible with the encrypted fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write",
            action="store_true",
            help="Persist the generated key to the .env file using env_manager.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite an existing key when used together with --write.",
        )

    def handle(self, *args, **options):
        key = Fernet.generate_key().decode()

        if options.get("write"):
            env_values = env_manager.read_env()
            if env_values.get("FERNET_KEY") and not options.get("force"):
                raise CommandError("FERNET_KEY already exists. Use --force to overwrite it.")
            env_manager.write_values({"FERNET_KEY": key})
            self.stdout.write(self.style.SUCCESS("FERNET_KEY stored in .env. Restart the server to apply."))
        else:
            self.stdout.write(key)

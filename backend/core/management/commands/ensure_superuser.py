"""Management command to create a default superuser if it does not exist.
Useful for development and Docker environments.
"""
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from typing import Any


class Command(BaseCommand):
    help = "Create a default superuser if it does not already exist"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--username",
            default=os.getenv("DJANGO_SUPERUSER_USERNAME", "admin"),
            help="Superuser username (default: admin)",
        )
        parser.add_argument(
            "--email",
            default=os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@localhost"),
            help="Superuser email (default: admin@localhost)",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123"),
            help="Superuser password (default: admin123)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        User = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'Superuser "{username}" already exists; '
                    "skipping creation."
                )
            )
            return

        try:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{username}" created successfully.'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(f'   Login: {username} / {password}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )
            raise

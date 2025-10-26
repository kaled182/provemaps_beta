"""
Management command para criar superuser padrão se não existir.
Útil para ambientes de desenvolvimento e Docker.
"""
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria superuser padrão se não existir (admin/admin123)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'),
            help='Username do superuser (default: admin)',
        )
        parser.add_argument(
            '--email',
            default=os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@localhost'),
            help='Email do superuser (default: admin@localhost)',
        )
        parser.add_argument(
            '--password',
            default=os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123'),
            help='Senha do superuser (default: admin123)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'⚠️  Superuser "{username}" já existe. Pulando criação.')
            )
            return

        try:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Superuser "{username}" criado com sucesso!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   Login: {username} / {password}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao criar superuser: {e}')
            )
            raise

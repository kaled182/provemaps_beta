from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(blank=True, max_length=20, null=True, verbose_name="Celular/WhatsApp")),
                ("telegram_chat_id", models.CharField(blank=True, max_length=50, null=True, verbose_name="Telegram ID")),
                ("notify_via_email", models.BooleanField(default=True, verbose_name="Receber via Email")),
                ("notify_via_whatsapp", models.BooleanField(default=False, verbose_name="Receber via WhatsApp")),
                ("notify_via_telegram", models.BooleanField(default=False, verbose_name="Receber via Telegram")),
                ("receive_critical_alerts", models.BooleanField(default=True, verbose_name="Alertas Criticos")),
                ("receive_warning_alerts", models.BooleanField(default=False, verbose_name="Alertas de Aviso")),
                ("department", models.CharField(blank=True, max_length=100, verbose_name="Departamento")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

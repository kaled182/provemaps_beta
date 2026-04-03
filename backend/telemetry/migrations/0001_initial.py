from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Installation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("installation_id", models.UUIDField(db_index=True, unique=True)),
                ("version", models.CharField(max_length=32)),
                ("os_platform", models.CharField(blank=True, default="", max_length=64)),
                ("ping_count", models.PositiveIntegerField(default=1)),
                ("first_seen", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Instalação",
                "verbose_name_plural": "Instalações",
                "ordering": ["-last_seen"],
                "app_label": "telemetry",
            },
        ),
    ]

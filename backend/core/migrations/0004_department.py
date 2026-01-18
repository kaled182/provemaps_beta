from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_userprofile_totp"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="Nome")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="Descricao")),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Criado em")),
            ],
        ),
    ]

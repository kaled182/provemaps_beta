from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="totp_secret",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                verbose_name="TOTP Secret",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="totp_enabled",
            field=models.BooleanField(default=False, verbose_name="TOTP Ativo"),
        ),
    ]

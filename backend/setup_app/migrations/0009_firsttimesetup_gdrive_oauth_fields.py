from django.db import migrations, models
from setup_app.fields import EncryptedCharField


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0008_firsttimesetup_gdrive_shared_drive_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_auth_mode",
            field=models.CharField(
                choices=[
                    ("service_account", "Service Account"),
                    ("oauth", "OAuth (Conta pessoal)"),
                ],
                default="service_account",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_oauth_client_id",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_oauth_client_secret",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_oauth_refresh_token",
            field=EncryptedCharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_oauth_user_email",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
    ]

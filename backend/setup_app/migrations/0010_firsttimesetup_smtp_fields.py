from django.db import migrations, models
from setup_app.fields import EncryptedCharField


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0009_firsttimesetup_gdrive_oauth_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_host",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_port",
            field=EncryptedCharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_security",
            field=EncryptedCharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_user",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_password",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_from_name",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_from_email",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_test_recipient",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
    ]

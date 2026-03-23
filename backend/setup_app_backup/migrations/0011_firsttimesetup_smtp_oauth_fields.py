from django.db import migrations
import setup_app.fields


class Migration(migrations.Migration):

    dependencies = [
        ("setup_app", "0010_firsttimesetup_smtp_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_auth_mode",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_oauth_client_id",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_oauth_client_secret",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="smtp_oauth_refresh_token",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
    ]

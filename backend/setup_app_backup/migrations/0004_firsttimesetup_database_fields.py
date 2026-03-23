from django.db import migrations

import setup_app.fields


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0003_alter_firsttimesetup_auth_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="db_host",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="db_port",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="db_name",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="db_user",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="db_password",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="redis_url",
            field=setup_app.fields.EncryptedCharField(blank=True, max_length=512, null=True),
        ),
    ]

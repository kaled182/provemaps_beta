from django.db import migrations
from setup_app.fields import EncryptedCharField


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0007_firsttimesetup_ftp_enabled_firsttimesetup_ftp_host_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="gdrive_shared_drive_id",
            field=EncryptedCharField(blank=True, max_length=255, null=True),
        ),
    ]
